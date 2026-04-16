"""V1 PostMarketReview 服务层。"""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_outcome import PostMarketReview
from app.schemas.review_outcome import PostMarketReviewCreate, PostMarketReviewUpdate

logger = logging.getLogger(__name__)


async def get_by_date(db: AsyncSession, target_date: date) -> PostMarketReview | None:
    result = await db.execute(
        select(PostMarketReview).where(PostMarketReview.date == target_date)
    )
    return result.scalar_one_or_none()


async def create_or_update(
    db: AsyncSession, data: PostMarketReviewCreate
) -> PostMarketReview:
    existing = await get_by_date(db, data.date)
    if existing:
        for field, value in data.model_dump(exclude_unset=True, exclude={"date"}).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = PostMarketReview(**data.model_dump(exclude_unset=True))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def run_review(db: AsyncSession, target_date: date) -> PostMarketReview:
    """消费当天 BattleBrief + MarketStateDaily + CandidatePoolEntry 生成盘后复盘。

    Phase 2 实现完整逻辑，本阶段仅占位。
    """
    raise NotImplementedError("run_review 将在 Phase 2 实现")
