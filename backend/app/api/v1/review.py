"""每日复盘 API。

数据流:
  POST /run              — 触发复盘 → 采集涨停/情绪 → AI 总结 → 写入 daily_reviews + sentiment_cycle_log
  GET  /list             — 历史复盘列表
  GET  /date/{date}      — 按日期获取复盘（历史联动用）
  GET  /{review_id}      — 单次复盘详情
  PUT  /{review_id}      — 用户编辑/确认复盘
  GET  /sentiment        — 情绪周期日志
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.review_engine import generate_daily_review
from app.core.limit_up_tracker import get_limit_up_data
from app.core.strategy_matcher import get_recommend_for_review
from app.models.review import DailyReview, LimitUpBoard
from app.models.sentiment import SentimentCycleLog
from app.schemas.review import (
    DailyReviewItem,
    ReviewUpdateRequest,
    SentimentLogItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run")
async def run_review(
    target_date: str = Query(None, description="目标日期 YYYY-MM-DD，为空则取今日"),
    db: AsyncSession = Depends(get_db),
):
    """触发复盘（支持补充历史复盘）。若已存在则覆盖更新。"""
    if target_date:
        try:
            today = date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    else:
        today = date.today()

    date_str = str(today) if today != date.today() else "today"

    existing_result = await db.execute(
        select(DailyReview).where(DailyReview.date == today)
    )
    existing_review = existing_result.scalar_one_or_none()

    try:
        limit_up_data = await get_limit_up_data(date_str)
    except Exception as e:
        logger.error("Failed to get limit-up data: %s", e)
        limit_up_data = {"market_height": 0, "ladder": [], "broken_boards": []}

    market_overview = None
    if today == date.today():
        try:
            from app.cache import cache_get
            cached = await cache_get("sr:market:overview")
            if cached and isinstance(cached, dict):
                market_overview = cached
        except Exception:
            pass

    if not market_overview:
        try:
            from app.api.v1.market import _read_snapshot, _read_snapshot_by_date
            if today != date.today():
                market_overview = await _read_snapshot_by_date(db, "overview", today)
            if not market_overview:
                market_overview = await _read_snapshot(db, "overview")
        except Exception:
            pass

    prev_phases = await _get_prev_phases(db)

    result = await generate_daily_review(limit_up_data, market_overview, prev_phases)

    leader = limit_up_data.get("market_leader") or {}
    leader_name = ""
    if isinstance(leader, dict):
        leader_name = str(leader.get("name", "") or "")

    cycle = result.get("cycle_result", {})
    ai_reason = cycle.get("ai_reason", "") if isinstance(cycle, dict) else ""

    cycle_phase = cycle.get("phase", "") if isinstance(cycle, dict) else ""
    try:
        strategy_text, position_text = await get_recommend_for_review(cycle_phase, db)
        result["applicable_strategy"] = strategy_text
        result["suggested_position"] = position_text
    except Exception as e:
        logger.warning("strategy_matcher failed, using engine defaults: %s", e)

    raw_height = result.get("market_height", 0) or limit_up_data.get("market_height", 0)
    raw_ladder = limit_up_data.get("ladder", [])
    raw_total_limit_up = result.get("total_limit_up", 0) or sum(
        len(lv.get("stocks", [])) for lv in raw_ladder
    )
    raw_first_board = result.get("first_board_count", 0) or int(limit_up_data.get("first_board_count", 0) or 0)
    raw_broken = limit_up_data.get("broken_boards", [])
    raw_broken_count = result.get("broken_board_count", 0) or len(raw_broken)
    raw_broken_names = result.get("broken_boards", "")
    if not raw_broken_names and raw_broken:
        raw_broken_names = ",".join(
            b.get("name", "") for b in raw_broken[:10] if isinstance(b, dict)
        )

    auto_volume = result.get("total_volume", "")
    if not auto_volume and market_overview:
        breadth = market_overview.get("breadth", {})
        total_amount = breadth.get("total_amount")
        if isinstance(total_amount, (int, float)) and total_amount > 0:
            auto_volume = f"约{round(total_amount / 1e8)}亿"

    review_fields = dict(
        status=result.get("status", "draft"),
        market_sentiment=result.get("market_sentiment", ""),
        sentiment_cycle_main=result.get("sentiment_cycle_main", ""),
        market_height=raw_height,
        market_leader=leader_name,
        dragon_stock=result.get("dragon_stock", leader_name),
        core_middle_stock=result.get("core_middle_stock", ""),
        market_ladder=result.get("market_ladder", ""),
        total_volume=auto_volume,
        total_limit_up=raw_total_limit_up,
        first_board_count=raw_first_board,
        broken_board_count=raw_broken_count,
        sentiment_cycle_sub=result.get("sentiment_cycle_sub", ""),
        index_sentiment_sh=result.get("index_sentiment_sh", ""),
        index_sentiment_csm=result.get("index_sentiment_csm", ""),
        sentiment_detail=ai_reason,
        main_sector=result.get("main_sector", ""),
        sub_sector=result.get("sub_sector", ""),
        main_sectors=result.get("main_sectors", ""),
        sub_sectors=result.get("sub_sectors", ""),
        market_style=result.get("market_style", ""),
        broken_boards=raw_broken_names or result.get("broken_boards", ""),
        broken_high_stock=result.get("broken_high_stock", ""),
        conclusion_quadrant=result.get("conclusion_quadrant", ""),
        review_summary=result.get("review_summary", ""),
        next_day_plan=result.get("next_day_plan", ""),
        next_day_prediction=result.get("next_day_prediction", ""),
        next_day_mode=result.get("next_day_mode", ""),
        applicable_strategy=result.get("applicable_strategy", ""),
        suggested_position=result.get("suggested_position", ""),
        ai_review_draft=result.get("review_summary", ""),
        ai_next_day_suggestion=result.get("next_day_plan", ""),
        is_confirmed=(result.get("status", "draft") == "published"),
    )

    if existing_review:
        for field, value in review_fields.items():
            setattr(existing_review, field, value)
        msg = "复盘已重新生成（覆盖旧草稿）"
    else:
        review_obj = DailyReview(date=today, **review_fields)
        db.add(review_obj)
        msg = "复盘已生成"

    sentiment_log = SentimentCycleLog(
        date=today,
        cycle_phase=cycle.get("phase", ""),
        market_height=cycle.get("height", 0),
        main_sector=result.get("main_sector", ""),
        transition_note=cycle.get("ai_reason", ""),
    )
    db.add(sentiment_log)

    await _save_limit_up_boards(db, today, limit_up_data)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.warning("IntegrityError on review commit, retrying as update")
        async with db.begin():
            re_result = await db.execute(
                select(DailyReview).where(DailyReview.date == today)
            )
            row = re_result.scalar_one_or_none()
            if row:
                for field, value in review_fields.items():
                    setattr(row, field, value)
        msg = "复盘已重新生成（覆盖旧草稿）"

    return {"message": msg, "date": str(today), "sentiment": cycle.get("phase", "")}


@router.post("/generate")
async def generate_review(
    target_date: str = Query(None, description="目标日期 YYYY-MM-DD，为空则取今日"),
    db: AsyncSession = Depends(get_db),
):
    """兼容计划文档：/generate 等价于 /run。"""
    return await run_review(target_date=target_date, db=db)


@router.get("/today", response_model=DailyReviewItem)
async def today_review(db: AsyncSession = Depends(get_db)):
    """获取今日复盘（不存在则 404）。"""
    today = date.today()
    draft_stmt = (
        select(DailyReview)
        .where(DailyReview.date == today, DailyReview.status == "draft")
        .limit(1)
    )
    draft_result = await db.execute(draft_stmt)
    r = draft_result.scalar_one_or_none()
    if not r:
        stmt = select(DailyReview).where(DailyReview.date == today).limit(1)
        result = await db.execute(stmt)
        r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="今日复盘不存在")
    return _to_review_item(r)


@router.get("/list", response_model=list[DailyReviewItem])
async def list_reviews(
    limit: int = Query(30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """历史复盘列表。"""
    stmt = select(DailyReview).order_by(desc(DailyReview.date)).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_to_review_item(r) for r in rows]


@router.get("/sentiment", response_model=list[SentimentLogItem])
async def sentiment_log(
    limit: int = Query(30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """情绪周期日志。"""
    stmt = select(SentimentCycleLog).order_by(desc(SentimentCycleLog.date)).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        SentimentLogItem(
            id=r.id,
            date=str(r.date),
            cycle_phase=r.cycle_phase or "",
            market_height=r.market_height or 0,
            main_sector=r.main_sector or "",
            transition_note=r.transition_note or "",
        )
        for r in rows
    ]


@router.get("/sentiment/current")
async def sentiment_current(db: AsyncSession = Depends(get_db)):
    """当前（最新）情绪周期判断。"""
    stmt = select(SentimentCycleLog).order_by(desc(SentimentCycleLog.date)).limit(1)
    result = await db.execute(stmt)
    latest = result.scalar_one_or_none()
    if not latest:
        return {"phase": "未知", "market_height": 0, "main_sector": "", "date": ""}
    return {
        "phase": latest.cycle_phase or "未知",
        "market_height": latest.market_height or 0,
        "main_sector": latest.main_sector or "",
        "transition_note": latest.transition_note or "",
        "date": str(latest.date),
    }


@router.get("/sentiment/transitions")
async def sentiment_transitions(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """情绪周期转换记录（标注相邻两天的周期变化）。"""
    stmt = select(SentimentCycleLog).order_by(desc(SentimentCycleLog.date)).limit(limit)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    transitions = []
    for i, row in enumerate(rows):
        prev_phase = rows[i + 1].cycle_phase if i + 1 < len(rows) else ""
        current_phase = row.cycle_phase or ""
        changed = prev_phase != current_phase and prev_phase != ""
        transitions.append({
            "date": str(row.date),
            "phase": current_phase,
            "prev_phase": prev_phase,
            "changed": changed,
            "transition": f"{prev_phase} → {current_phase}" if changed else "",
            "market_height": row.market_height or 0,
            "main_sector": row.main_sector or "",
            "note": row.transition_note or "",
        })
    return transitions


@router.get("/date/{target_date}", response_model=DailyReviewItem)
async def get_review_by_date(target_date: str, db: AsyncSession = Depends(get_db)):
    """按日期获取复盘（历史联动用）。"""
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    stmt = select(DailyReview).where(DailyReview.date == d).limit(1)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail=f"{target_date} 无复盘记录")
    return _to_review_item(r)


@router.get("/{review_id}", response_model=DailyReviewItem)
async def get_review(review_id: int, db: AsyncSession = Depends(get_db)):
    """单次复盘详情。"""
    stmt = select(DailyReview).where(DailyReview.id == review_id)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="复盘不存在")
    return _to_review_item(r)


@router.put("/{review_id}")
async def update_review(
    review_id: int,
    req: ReviewUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """编辑/确认复盘。"""
    stmt = select(DailyReview).where(DailyReview.id == review_id)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="复盘不存在")

    payload = req.model_dump(exclude_none=True)
    if "is_confirmed" in payload and "status" not in payload:
        payload["status"] = "published" if payload["is_confirmed"] else "draft"
    if "status" in payload and "is_confirmed" not in payload:
        payload["is_confirmed"] = payload["status"] == "published"
    for field, value in payload.items():
        setattr(r, field, value)

    await db.commit()
    return {"message": "复盘已更新"}


def _to_review_item(r: DailyReview) -> DailyReviewItem:
    return DailyReviewItem(
        id=r.id,
        date=str(r.date),
        status=r.status or ("published" if r.is_confirmed else "draft"),
        market_sentiment=r.market_sentiment or "",
        sentiment_cycle_main=r.sentiment_cycle_main or r.market_sentiment or "",
        market_height=r.market_height or 0,
        market_leader=r.market_leader or "",
        dragon_stock=r.dragon_stock or r.market_leader or "",
        core_middle_stock=r.core_middle_stock or "",
        market_ladder=r.market_ladder or "",
        total_volume=r.total_volume or "",
        total_limit_up=r.total_limit_up or 0,
        first_board_count=r.first_board_count or 0,
        broken_board_count=r.broken_board_count or 0,
        sentiment_detail=r.sentiment_detail or "",
        main_sector=r.main_sector or "",
        sub_sector=r.sub_sector or "",
        main_sectors=r.main_sectors or r.main_sector or "",
        sub_sectors=r.sub_sectors or r.sub_sector or "",
        market_style=r.market_style or "",
        broken_boards=r.broken_boards or "",
        broken_high_stock=r.broken_high_stock or "",
        sentiment_cycle_sub=r.sentiment_cycle_sub or "",
        index_sentiment_sh=r.index_sentiment_sh or "",
        index_sentiment_csm=r.index_sentiment_csm or "",
        conclusion_quadrant=r.conclusion_quadrant or "",
        review_summary=r.review_summary or "",
        next_day_plan=r.next_day_plan or "",
        next_day_prediction=r.next_day_prediction or r.next_day_plan or "",
        next_day_mode=r.next_day_mode or "",
        applicable_strategy=r.applicable_strategy or "",
        suggested_position=r.suggested_position or "",
        ai_review_draft=r.ai_review_draft or "",
        ai_next_day_suggestion=r.ai_next_day_suggestion or "",
        market_action=r.market_action or "",
        market_result=r.market_result or "",
        is_confirmed=r.is_confirmed or False,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


async def _get_prev_phases(db: AsyncSession, n: int = 7) -> list[str]:
    """获取最近 N 天的情绪周期。"""
    stmt = select(SentimentCycleLog).order_by(desc(SentimentCycleLog.date)).limit(n)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [r.cycle_phase for r in reversed(rows) if r.cycle_phase]


async def _save_limit_up_boards(db: AsyncSession, today: date, data: dict):
    """将涨停梯队数据写入 limit_up_boards 表。"""
    for item in data.get("ladder", []):
        level = item.get("level", 1)
        for stock in item.get("stocks", []):
            board = LimitUpBoard(
                date=today,
                board_count=level,
                code=stock.get("code", ""),
                name=stock.get("name", ""),
                sector=stock.get("sector", ""),
                change_pct=stock.get("change_pct"),
                turnover=stock.get("turnover"),
                is_first_board=(level == 1),
                is_broken=stock.get("is_broken", False),
            )
            db.add(board)
