"""市场总览 API。"""
from fastapi import APIRouter, Query

from app.cache import cache_get, cache_set
from app.core.market_review import get_market_overview, get_sector_ranking, get_money_flow
from app.core.limit_up_tracker import get_limit_up_data
from app.data_provider.manager import get_data_manager

router = APIRouter()


@router.get("/overview")
async def market_overview():
    """大盘指数 + 涨跌面 + 涨停跌停数。"""
    cached = await cache_get("sr:market:overview")
    if cached:
        return cached
    data = await get_market_overview()
    await cache_set("sr:market:overview", data, ttl=60)
    return data


@router.get("/breadth")
async def market_breadth():
    """涨跌面统计(独立端点，较慢但单独缓存)。"""
    from app.core.market_review import get_market_breadth
    return await get_market_breadth()


@router.get("/sectors")
async def market_sectors(
    sector_type: str = Query("concept", description="concept 或 industry"),
    limit: int = Query(30, ge=1, le=100),
):
    """板块排行(概念/行业) + 涨跌幅。"""
    cache_key = f"sr:market:sectors:{sector_type}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    data = await get_sector_ranking(sector_type, limit)
    await cache_set(cache_key, data, ttl=120)
    return data


@router.get("/money-flow")
async def money_flow():
    """行业资金流向。"""
    cached = await cache_get("sr:market:money_flow")
    if cached:
        return cached
    data = await get_money_flow()
    await cache_set("sr:market:money_flow", data, ttl=120)
    return data


@router.get("/index/{code}/history")
async def index_history(code: str, days: int = Query(60, ge=1, le=365)):
    """指数历史 K 线。"""
    mgr = get_data_manager()
    df = await mgr.get_index_daily(code, days)
    if df is None:
        return {"error": "No data", "code": code}
    records = df.to_dict(orient="records")
    for r in records:
        if "date" in r:
            r["date"] = str(r["date"])
    return {"code": code, "days": len(records), "data": records}


@router.get("/limit-up")
async def limit_up_board(date: str = Query("today")):
    """涨停板/连板梯队结构化数据。"""
    cached = await cache_get("sr:market:limit_up")
    if cached:
        return cached
    data = await get_limit_up_data(date)
    await cache_set("sr:market:limit_up", data, ttl=300)
    return data


@router.get("/quote/{code}")
async def stock_quote(code: str):
    """单只股票实时行情。"""
    cache_key = f"sr:quote:{code}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    mgr = get_data_manager()
    quote = await mgr.get_realtime_quote(code)
    if quote:
        await cache_set(cache_key, quote)
        return quote
    return {"error": "Quote not available", "code": code}
