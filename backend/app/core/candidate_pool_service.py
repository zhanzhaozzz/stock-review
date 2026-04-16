"""V1 CandidatePoolEntry 服务层。"""
import logging
from datetime import date

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
