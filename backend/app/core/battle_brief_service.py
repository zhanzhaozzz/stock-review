"""V1 BattleBrief 服务层。"""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.battle_brief import BattleBrief
from app.schemas.battle_brief import BattleBriefCreate, BattleBriefUpdate

logger = logging.getLogger(__name__)


async def get_by_date(db: AsyncSession, target_date: date) -> BattleBrief | None:
    result = await db.execute(
        select(BattleBrief).where(BattleBrief.date == target_date)
    )
    return result.scalar_one_or_none()


async def create_or_update(
    db: AsyncSession, data: BattleBriefCreate
) -> BattleBrief:
    existing = await get_by_date(db, data.date)
    if existing:
        for field, value in data.model_dump(exclude_unset=True, exclude={"date"}).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = BattleBrief(**data.model_dump(exclude_unset=True))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
