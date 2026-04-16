"""V1 CandidatePoolEntry 服务层。"""
import logging
from datetime import date, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_pool import CandidatePoolEntry
from app.schemas.candidate_pool import CandidatePoolEntryCreate, CandidatePoolEntryUpdate

logger = logging.getLogger(__name__)


async def list_by_date(db: AsyncSession, target_date: date) -> list[CandidatePoolEntry]:
    result = await db.execute(
        select(CandidatePoolEntry)
        .where(CandidatePoolEntry.date == target_date)
        .order_by(CandidatePoolEntry.id)
    )
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, entry_id: int) -> CandidatePoolEntry | None:
    result = await db.execute(
        select(CandidatePoolEntry).where(CandidatePoolEntry.id == entry_id)
    )
    return result.scalar_one_or_none()


async def create_entry(
    db: AsyncSession, data: CandidatePoolEntryCreate
) -> CandidatePoolEntry:
    """创建候选池条目，同日同票已存在时返回已有记录。"""
    existing = await db.execute(
        select(CandidatePoolEntry).where(
            and_(
                CandidatePoolEntry.date == data.date,
                CandidatePoolEntry.code == data.code,
            )
        )
    )
    found = existing.scalar_one_or_none()
    if found:
        logger.info("候选池已存在 date=%s code=%s，跳过创建", data.date, data.code)
        return found

    record = CandidatePoolEntry(**data.model_dump(exclude_unset=True))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_entry(
    db: AsyncSession, entry_id: int, data: CandidatePoolEntryUpdate
) -> CandidatePoolEntry | None:
    entry = await get_by_id(db, entry_id)
    if not entry:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    await db.commit()
    await db.refresh(entry)
    return entry


async def generate_candidates(db: AsyncSession, target_date: date) -> list[CandidatePoolEntry]:
    """融合梯队来源 + 观察池来源 + 前日种子，生成候选池。

    幂等：同日同票跳过已有条目。
    """
    logger.info("[CandidatePool] 开始生成 date=%s", target_date)

    from app.core.limit_up_tracker import get_limit_up_data
    from app.core import market_state_service, battle_brief_service, discipline_engine
    from app.models.watchlist import Watchlist
    from app.models.review_outcome import PostMarketReview

    market_state = await market_state_service.get_by_date(db, target_date)
    if not market_state:
        yesterday = target_date - timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= timedelta(days=1)
        market_state = await market_state_service.get_by_date(db, yesterday)

    battle_brief = await battle_brief_service.get_by_date(db, target_date)

    raw_candidates: list[dict] = []

    try:
        limit_up = await get_limit_up_data(str(target_date))
        ladder = limit_up.get("ladder", [])
        for tier in ladder:
            level = tier.get("level", 1)
            if level < 2:
                continue
            for stock in tier.get("stocks", []):
                raw_candidates.append({
                    "code": stock.get("code", ""),
                    "name": stock.get("name", ""),
                    "source_type": "梯队",
                    "source_reason": f"{level}板连板，所属行业: {stock.get('sector', '')}",
                    "theme": stock.get("sector", ""),
                })
        logger.info("[CandidatePool] 梯队来源: %d 只", len(raw_candidates))
    except Exception as e:
        logger.warning("[CandidatePool] 梯队数据获取失败: %s", e)

    watchlist_count = 0
    try:
        wl_result = await db.execute(select(Watchlist))
        watchlist_items = wl_result.scalars().all()
        for item in watchlist_items:
            raw_candidates.append({
                "code": item.code,
                "name": item.name,
                "source_type": "观察池",
                "source_reason": f"自选股观察池, 市场={item.market or ''}",
                "theme": "",
            })
            watchlist_count += 1
        logger.info("[CandidatePool] 观察池来源: %d 只", watchlist_count)
    except Exception as e:
        logger.warning("[CandidatePool] 观察池数据获取失败: %s", e)

    try:
        yesterday = target_date - timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= timedelta(days=1)
        prev_review = await db.execute(
            select(PostMarketReview).where(PostMarketReview.date == yesterday)
        )
        prev = prev_review.scalar_one_or_none()
        if prev and prev.next_day_seeds:
            seeds = prev.next_day_seeds if isinstance(prev.next_day_seeds, list) else []
            for seed in seeds:
                if isinstance(seed, dict) and seed.get("code"):
                    raw_candidates.append({
                        "code": seed["code"],
                        "name": seed.get("name", ""),
                        "source_type": "事件",
                        "source_reason": f"前日复盘种子: {seed.get('reason', '')}",
                        "theme": seed.get("theme", ""),
                    })
            logger.info("[CandidatePool] 前日种子来源: %d 只", len(seeds))
    except Exception as e:
        logger.warning("[CandidatePool] 前日种子获取失败: %s", e)

    merged = _deduplicate_candidates(raw_candidates)
    logger.info("[CandidatePool] 去重后候选: %d 只", len(merged))

    created: list[CandidatePoolEntry] = []
    for cand in merged:
        gate_result = discipline_engine.evaluate(
            CandidatePoolEntryCreate(
                date=target_date,
                code=cand["code"],
                name=cand["name"],
                source_type=cand["source_type"],
                source_reason=cand.get("source_reason"),
                theme=cand.get("theme"),
            ),
            market_state,
        )

        data = CandidatePoolEntryCreate(
            date=target_date,
            code=cand["code"],
            name=cand["name"],
            source_type=cand["source_type"],
            source_reason=cand.get("source_reason"),
            theme=cand.get("theme"),
            thesis=cand.get("thesis"),
            gate_status=gate_result["gate_status"],
            gate_reason=gate_result["gate_reason"],
            action_hint=gate_result["action_hint"],
        )

        entry = await create_entry(db, data)
        created.append(entry)

    logger.info("[CandidatePool] 生成完成 date=%s count=%d", target_date, len(created))
    return created


def _deduplicate_candidates(raw: list[dict]) -> list[dict]:
    """同 code 去重，梯队优先级最高。"""
    _PRIORITY = {"梯队": 0, "事件": 1, "观察池": 2}
    seen: dict[str, dict] = {}
    for cand in raw:
        code = cand.get("code", "")
        if not code:
            continue
        if code in seen:
            existing_priority = _PRIORITY.get(seen[code].get("source_type", ""), 9)
            new_priority = _PRIORITY.get(cand.get("source_type", ""), 9)
            if new_priority < existing_priority:
                seen[code] = cand
        else:
            seen[code] = cand
    return list(seen.values())


async def backfill_review_outcomes(db: AsyncSession, target_date: date) -> list[CandidatePoolEntry]:
    """回填候选池当日条目的 review_outcome。

    基于盘后行情数据判断逻辑兑现情况。
    幂等：已回填的不再覆盖（除非仍为"待复盘"）。
    """
    logger.info("[CandidatePool] 开始回填 review_outcome date=%s", target_date)

    entries = await list_by_date(db, target_date)
    if not entries:
        logger.info("[CandidatePool] 当日无候选池条目，跳过回填")
        return []

    from app.data_provider.manager import get_data_manager
    manager = get_data_manager()

    updated: list[CandidatePoolEntry] = []
    for entry in entries:
        if entry.review_outcome and entry.review_outcome != "待复盘":
            continue

        if entry.gate_status == "拦截":
            entry.review_outcome = "纪律拦截正确"
            entry.review_note = f"门控拦截: {entry.gate_reason or ''}"
            updated.append(entry)
            continue

        try:
            df = await manager.get_daily(entry.code, days=1)
            if df is not None and not df.empty:
                row = df.iloc[-1]
                change_pct = float(row.get("change_pct", 0) or 0)
                if change_pct >= 5:
                    entry.review_outcome = "逻辑兑现"
                    entry.review_note = f"涨幅 {change_pct:.2f}%"
                elif change_pct >= 0:
                    entry.review_outcome = "时机未到"
                    entry.review_note = f"涨幅 {change_pct:.2f}%，逻辑未完全兑现"
                else:
                    entry.review_outcome = "逻辑证伪"
                    entry.review_note = f"跌幅 {change_pct:.2f}%"
                updated.append(entry)
            else:
                logger.warning("[CandidatePool] 无法获取行情 code=%s", entry.code)
        except Exception as e:
            logger.warning("[CandidatePool] 回填失败 code=%s: %s", entry.code, e)

    if updated:
        await db.commit()

    logger.info("[CandidatePool] 回填完成 date=%s updated=%d/%d", target_date, len(updated), len(entries))
    return updated
