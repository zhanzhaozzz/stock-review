"""V1 生成链手动触发 API — 为每个核心对象提供手动补跑入口。

路由前缀: /api/v1/generate
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.market_state import MarketStateDailyRead
from app.schemas.battle_brief import BattleBriefRead
from app.schemas.candidate_pool import CandidatePoolEntryRead
from app.schemas.review_outcome import PostMarketReviewRead

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_date(raw: Optional[str]) -> date:
    if not raw:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，需 YYYY-MM-DD")


@router.post("/market-state", response_model=MarketStateDailyRead)
async def generate_market_state(
    target_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
):
    """手动触发 MarketStateDaily 生成。幂等：同日已有则覆盖。"""
    d = _parse_date(target_date)
    logger.info("[GenerateAPI] 手动触发 MarketStateDaily date=%s", d)
    try:
        from app.core import market_state_service
        result = await market_state_service.generate_from_snapshot(db, d)
        return MarketStateDailyRead.model_validate(result, from_attributes=True)
    except Exception as e:
        logger.error("[GenerateAPI] MarketStateDaily 生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"MarketStateDaily 生成失败: {e}")


@router.post("/battle-brief", response_model=BattleBriefRead)
async def generate_battle_brief(
    target_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
):
    """手动触发 BattleBrief 生成。幂等：同日已有则覆盖。"""
    d = _parse_date(target_date)
    logger.info("[GenerateAPI] 手动触发 BattleBrief date=%s", d)
    try:
        from app.core import battle_brief_service
        result = await battle_brief_service.generate(db, d)
        return BattleBriefRead.model_validate(result, from_attributes=True)
    except Exception as e:
        logger.error("[GenerateAPI] BattleBrief 生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"BattleBrief 生成失败: {e}")


@router.post("/candidates", response_model=list[CandidatePoolEntryRead])
async def generate_candidates(
    target_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
):
    """手动触发 CandidatePoolEntry 生成。幂等：同日同票跳过。"""
    d = _parse_date(target_date)
    logger.info("[GenerateAPI] 手动触发 CandidatePoolEntry date=%s", d)
    try:
        from app.core import candidate_pool_service
        result = await candidate_pool_service.generate_candidates(db, d)
        return [CandidatePoolEntryRead.model_validate(e, from_attributes=True) for e in result]
    except Exception as e:
        logger.error("[GenerateAPI] CandidatePoolEntry 生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"CandidatePoolEntry 生成失败: {e}")


@router.post("/candidate-review", response_model=list[CandidatePoolEntryRead])
async def generate_candidate_review(
    target_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
):
    """手动触发候选池盘后回填。幂等：已回填的（非"待复盘"）跳过。"""
    d = _parse_date(target_date)
    logger.info("[GenerateAPI] 手动触发候选池回填 date=%s", d)
    try:
        from app.core import candidate_pool_service
        result = await candidate_pool_service.backfill_review_outcomes(db, d)
        return [CandidatePoolEntryRead.model_validate(e, from_attributes=True) for e in result]
    except Exception as e:
        logger.error("[GenerateAPI] 候选池回填失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"候选池回填失败: {e}")


@router.post("/post-market-review", response_model=PostMarketReviewRead)
async def generate_post_market_review(
    target_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
):
    """手动触发 PostMarketReview 生成。幂等：同日已有则覆盖。"""
    d = _parse_date(target_date)
    logger.info("[GenerateAPI] 手动触发 PostMarketReview date=%s", d)
    try:
        from app.core import post_market_review_service
        result = await post_market_review_service.run_review(db, d)
        return PostMarketReviewRead.model_validate(result, from_attributes=True)
    except Exception as e:
        logger.error("[GenerateAPI] PostMarketReview 生成失败: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"PostMarketReview 生成失败: {e}")
