"""V1 盘后复盘 API。"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core import post_market_review_service
from app.schemas.review_outcome import PostMarketReviewRead

router = APIRouter()


@router.get("/today")
async def get_post_market_review_today(db: AsyncSession = Depends(get_db)):
    today = date.today()
    review = await post_market_review_service.get_by_date(db, today)
    if not review:
        return None
    return PostMarketReviewRead.model_validate(review, from_attributes=True)


@router.post("/run")
async def run_post_market_review(db: AsyncSession = Depends(get_db)):
    """触发盘后复盘生成（Phase 1 骨架，Phase 2 实现完整逻辑）。"""
    today = date.today()
    try:
        result = await post_market_review_service.run_review(db, today)
        return PostMarketReviewRead.model_validate(result, from_attributes=True)
    except NotImplementedError:
        raise HTTPException(
            status_code=501,
            detail="盘后复盘自动生成将在 Phase 2 实现",
        )
