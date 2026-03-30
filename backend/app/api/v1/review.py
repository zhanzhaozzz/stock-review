"""每日复盘 API。

数据流:
  POST /run        — 触发复盘 → 采集涨停/情绪 → AI 总结 → 写入 daily_reviews + sentiment_cycle_log
  GET  /list       — 历史复盘列表
  GET  /{review_id}— 单次复盘详情
  PUT  /{review_id}— 用户编辑/确认复盘
  GET  /sentiment   — 情绪周期日志
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.review_engine import generate_daily_review
from app.core.limit_up_tracker import get_limit_up_data
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
async def run_review(db: AsyncSession = Depends(get_db)):
    """触发当日复盘。"""
    today = date.today()

    existing = await db.execute(
        select(DailyReview).where(DailyReview.date == today)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="今日复盘已存在，请通过编辑更新")

    try:
        limit_up_data = await get_limit_up_data()
    except Exception as e:
        logger.error("Failed to get limit-up data: %s", e)
        limit_up_data = {"market_height": 0, "ladder": [], "broken_boards": []}

    market_overview = None
    try:
        from app.cache import cache_get
        cached = await cache_get("sr:market:overview")
        if cached and isinstance(cached, dict):
            market_overview = cached
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

    review_obj = DailyReview(
        date=today,
        market_sentiment=result.get("market_sentiment", ""),
        market_height=result.get("market_height", 0),
        market_leader=leader_name,
        total_limit_up=result.get("total_limit_up", 0),
        first_board_count=result.get("first_board_count", 0),
        broken_board_count=result.get("broken_board_count", 0),
        sentiment_detail=ai_reason,
        main_sector=result.get("main_sector", ""),
        sub_sector=result.get("sub_sector", ""),
        broken_boards=result.get("broken_boards", ""),
        review_summary=result.get("review_summary", ""),
        next_day_plan=result.get("next_day_plan", ""),
        applicable_strategy=result.get("applicable_strategy", ""),
        suggested_position=result.get("suggested_position", ""),
        ai_review_draft=result.get("review_summary", ""),
        ai_next_day_suggestion=result.get("next_day_plan", ""),
    )
    db.add(review_obj)

    sentiment_log = SentimentCycleLog(
        date=today,
        cycle_phase=cycle.get("phase", ""),
        market_height=cycle.get("height", 0),
        main_sector=result.get("main_sector", ""),
        transition_note=cycle.get("ai_reason", ""),
    )
    db.add(sentiment_log)

    await _save_limit_up_boards(db, today, limit_up_data)

    await db.commit()

    return {"message": "复盘已生成", "date": str(today), "sentiment": cycle.get("phase", "")}


@router.post("/generate")
async def generate_review(db: AsyncSession = Depends(get_db)):
    """兼容计划文档：/generate 等价于 /run。"""
    return await run_review(db)


@router.get("/today", response_model=DailyReviewItem)
async def today_review(db: AsyncSession = Depends(get_db)):
    """获取今日复盘（不存在则 404）。"""
    today = date.today()
    stmt = select(DailyReview).where(DailyReview.date == today).limit(1)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="今日复盘不存在")
    return _to_review_item(r)


@router.get("/list", response_model=list[DailyReviewItem])
async def list_reviews(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """历史复盘列表。"""
    stmt = select(DailyReview).order_by(desc(DailyReview.date)).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_to_review_item(r) for r in rows]


@router.get("/sentiment", response_model=list[SentimentLogItem])
async def sentiment_log(
    limit: int = Query(30, ge=1, le=100),
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

    for field, value in req.model_dump(exclude_none=True).items():
        setattr(r, field, value)

    await db.commit()
    return {"message": "复盘已更新"}


def _to_review_item(r: DailyReview) -> DailyReviewItem:
    return DailyReviewItem(
        id=r.id,
        date=str(r.date),
        market_sentiment=r.market_sentiment or "",
        market_height=r.market_height or 0,
        market_leader=r.market_leader or "",
        total_limit_up=r.total_limit_up or 0,
        first_board_count=r.first_board_count or 0,
        broken_board_count=r.broken_board_count or 0,
        sentiment_detail=r.sentiment_detail or "",
        main_sector=r.main_sector or "",
        sub_sector=r.sub_sector or "",
        review_summary=r.review_summary or "",
        next_day_plan=r.next_day_plan or "",
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
