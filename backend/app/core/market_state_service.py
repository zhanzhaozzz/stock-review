"""V1 MarketStateDaily 服务层。"""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_state import MarketStateDaily
from app.schemas.market_state import MarketStateDailyCreate, MarketStateDailyUpdate

logger = logging.getLogger(__name__)


async def get_by_date(db: AsyncSession, target_date: date) -> MarketStateDaily | None:
    result = await db.execute(
        select(MarketStateDaily).where(MarketStateDaily.date == target_date)
    )
    return result.scalar_one_or_none()


async def create_or_update(
    db: AsyncSession, data: MarketStateDailyCreate
) -> MarketStateDaily:
    existing = await get_by_date(db, data.date)
    if existing:
        for field, value in data.model_dump(exclude_unset=True, exclude={"date"}).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = MarketStateDaily(**data.model_dump(exclude_unset=True))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def generate_from_snapshot(db: AsyncSession, target_date: date) -> MarketStateDaily:
    """从 market_snapshots / limit_up_boards 等原始数据组装 MarketStateDaily。

    Phase 2 实现完整逻辑，本阶段仅占位。
    """
    raise NotImplementedError("generate_from_snapshot 将在 Phase 2 实现")
