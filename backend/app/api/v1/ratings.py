"""量化评级 API。"""
import asyncio
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.cache import cache_get, cache_set
from app.core.rating_engine import rate_stock
from app.models.rating import Rating
from app.schemas.rating import (
    RatingRunRequest,
    RatingRunResponse,
    RatingItem,
    RatingHistoryItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_STOCK_NAMES: dict[str, tuple[str, str]] = {}


def _detect_market(code: str) -> str:
    c = code.split(".")[0]
    if code.upper().endswith(".HK") or code.startswith("hk"):
        return "HK"
    if c.startswith("6"):
        return "A"
    return "A"


async def _resolve_name(code: str) -> tuple[str, str]:
    """返回 (name, market)。简单缓存 + 数据管理器查询。"""
    if code in _STOCK_NAMES:
        return _STOCK_NAMES[code]
    market = _detect_market(code)
    name = code
    try:
        from app.data_provider.manager import get_data_manager
        mgr = get_data_manager()
        quote = await mgr.get_realtime_quote(code)
        if quote and quote.get("name"):
            name = quote["name"]
    except Exception:
        pass
    _STOCK_NAMES[code] = (name, market)
    return name, market


@router.post("/run", response_model=RatingRunResponse)
async def run_rating(req: RatingRunRequest, db: AsyncSession = Depends(get_db)):
    """对指定股票列表执行评级。"""
    results: list[RatingItem] = []
    failed = 0
    today = date.today()

    sem = asyncio.Semaphore(5)

    async def _rate_one(code: str):
        nonlocal failed
        async with sem:
            try:
                name, market = await _resolve_name(code)
                r = await rate_stock(code, name=name, market=market)
                if r is None:
                    failed += 1
                    return

                rating_obj = Rating(
                    code=code,
                    name=r.get("name", code),
                    market=r.get("market", "A"),
                    date=today,
                    model_type="quant_ai",
                    trend_score=r.get("trend_score"),
                    momentum_score=r.get("momentum_score"),
                    volatility_score=r.get("volatility_score"),
                    volume_score=r.get("volume_score"),
                    value_score=r.get("value_score"),
                    sentiment_score=r.get("sentiment_score"),
                    fundamental_score=r.get("fundamental_score"),
                    ai_score=r.get("ai_score"),
                    total_score=r.get("total_score"),
                    rating=r.get("rating", ""),
                    reason={"text": r.get("reason", "")},
                    pe=r.get("pe"),
                    pb=r.get("pb"),
                    roe=r.get("roe"),
                    market_cap=r.get("market_cap"),
                    net_flow=r.get("net_flow"),
                )
                db.add(rating_obj)

                results.append(RatingItem(
                    code=code,
                    name=r.get("name", code),
                    market=r.get("market", "A"),
                    date=str(today),
                    **{k: r[k] for k in [
                        "trend_score", "momentum_score", "volatility_score",
                        "volume_score", "value_score", "sentiment_score",
                        "fundamental_score", "ai_score", "total_score",
                        "rating", "reason", "pe", "pb", "roe", "market_cap", "net_flow",
                    ] if k in r},
                ))
            except Exception as e:
                logger.error("Rating failed for %s: %s", code, e)
                failed += 1

    tasks = [_rate_one(c) for c in req.codes]
    await asyncio.gather(*tasks)

    try:
        await db.commit()
    except Exception as e:
        logger.error("Rating DB commit failed: %s", e)
        await db.rollback()

    results.sort(key=lambda x: x.total_score, reverse=True)

    return RatingRunResponse(
        total=len(req.codes),
        success=len(results),
        failed=failed,
        results=results,
    )


@router.get("/latest", response_model=list[RatingItem])
async def latest_ratings(
    limit: int = Query(50, ge=1, le=200),
    min_score: float = Query(0, ge=0, le=100),
    sort_by: str = Query("total_score"),
    db: AsyncSession = Depends(get_db),
):
    """最新评级结果(支持排序/筛选)。"""
    cache_key = f"sr:ratings:latest:{limit}:{min_score}:{sort_by}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    sort_col = getattr(Rating, sort_by, Rating.total_score)
    stmt = (
        select(Rating)
        .where(Rating.total_score >= min_score)
        .order_by(desc(sort_col))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = []
    for r in rows:
        items.append(RatingItem(
            code=r.code,
            name=r.name,
            market=r.market,
            date=str(r.date),
            trend_score=r.trend_score or 0,
            momentum_score=r.momentum_score or 0,
            volatility_score=r.volatility_score or 0,
            volume_score=r.volume_score or 0,
            value_score=r.value_score or 0,
            sentiment_score=r.sentiment_score or 0,
            fundamental_score=r.fundamental_score,
            ai_score=r.ai_score or 0,
            total_score=r.total_score or 0,
            rating=r.rating or "",
            reason=r.reason.get("text", "") if isinstance(r.reason, dict) else str(r.reason or ""),
            pe=r.pe,
            pb=r.pb,
            roe=r.roe,
            market_cap=r.market_cap,
            net_flow=r.net_flow,
        ))

    await cache_set(cache_key, [i.model_dump() for i in items], ttl=300)
    return items


@router.get("/history/{code}", response_model=list[RatingHistoryItem])
async def rating_history(
    code: str,
    limit: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """某只股票的历史评级趋势。"""
    stmt = (
        select(Rating)
        .where(Rating.code == code)
        .order_by(desc(Rating.date))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        RatingHistoryItem(
            date=str(r.date),
            total_score=r.total_score or 0,
            rating=r.rating or "",
            trend_score=r.trend_score or 0,
            momentum_score=r.momentum_score or 0,
            volatility_score=r.volatility_score or 0,
            volume_score=r.volume_score or 0,
            value_score=r.value_score or 0,
            sentiment_score=r.sentiment_score or 0,
            ai_score=r.ai_score or 0,
        )
        for r in rows
    ]
