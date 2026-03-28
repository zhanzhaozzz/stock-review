"""市场总览 API。

数据流：
  1. POST /sync/market (sync.py)  — 采集外部数据 → 写入 market_snapshots 表 + Redis 热缓存
  2. GET  /market/overview          — 优先读 Redis 缓存 → 降级从 SQLite 读最新快照
  3. GET  /market/sectors            — 同上
  4. GET  /market/quote/{code}       — 实时行情，Redis 缓存（30s）
"""
import asyncio
import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache_get, cache_set
from app.database import get_db
from app.models.market import MarketSnapshot
from app.data_provider.manager import get_data_manager

logger = logging.getLogger(__name__)
router = APIRouter()

EXTERNAL_TIMEOUT = 15


async def _with_timeout(coro, fallback=None):
    """包装外部调用，统一超时保护。"""
    try:
        return await asyncio.wait_for(coro, timeout=EXTERNAL_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("External call timed out after %ds", EXTERNAL_TIMEOUT)
        return fallback
    except Exception as e:
        logger.warning("External call failed: %s", e)
        return fallback


async def _read_snapshot(db: AsyncSession, snapshot_type: str) -> dict | list | None:
    """从 SQLite 读取最新快照。"""
    stmt = (
        select(MarketSnapshot)
        .where(MarketSnapshot.snapshot_type == snapshot_type)
        .order_by(desc(MarketSnapshot.updated_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row:
        return row.data
    return None


@router.get("/overview")
async def market_overview(db: AsyncSession = Depends(get_db)):
    """大盘指数 + 涨跌面 + 涨停跌停数。

    优先 Redis 缓存 → 降级 SQLite 快照 → 兜底空数据。
    """
    cached = await cache_get("sr:market:overview")
    if cached:
        return cached

    data = await _read_snapshot(db, "overview")
    if data:
        await cache_set("sr:market:overview", data, ttl=60)
        return data

    return {"indices": [], "breadth": {}, "timestamp": None, "_hint": "请先同步市场数据"}


@router.get("/breadth")
async def market_breadth(db: AsyncSession = Depends(get_db)):
    """涨跌面统计。"""
    cached = await cache_get("sr:market:breadth")
    if cached:
        return cached

    snapshot = await _read_snapshot(db, "overview")
    if snapshot and "breadth" in snapshot:
        return snapshot["breadth"]

    return {"up": 0, "down": 0, "flat": 0, "limit_up": 0, "limit_down": 0, "total": 0}


@router.get("/sectors")
async def market_sectors(
    sector_type: str = Query("concept", description="concept 或 industry"),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """板块排行(概念/行业) + 涨跌幅。"""
    cache_key = f"sr:market:sectors:{sector_type}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    data = await _read_snapshot(db, f"sectors_{sector_type}")
    if data:
        result = data[:limit] if isinstance(data, list) else data
        await cache_set(cache_key, result, ttl=120)
        return result

    return []


@router.get("/money-flow")
async def money_flow(db: AsyncSession = Depends(get_db)):
    """行业资金流向。"""
    cached = await cache_get("sr:market:money_flow")
    if cached:
        return cached

    data = await _read_snapshot(db, "money_flow")
    if data:
        await cache_set("sr:market:money_flow", data, ttl=120)
        return data

    return []


@router.get("/index/{code}/history")
async def index_history(code: str, days: int = Query(60, ge=1, le=365)):
    """指数历史 K 线。"""
    mgr = get_data_manager()
    df = await _with_timeout(mgr.get_index_daily(code, days))
    if df is None:
        return {"error": "No data", "code": code}
    records = df.to_dict(orient="records")
    for r in records:
        if "date" in r:
            r["date"] = str(r["date"])
    return {"code": code, "days": len(records), "data": records}


@router.get("/limit-up")
async def limit_up_board(
    date_str: str = Query("today", alias="date"),
    db: AsyncSession = Depends(get_db),
):
    """涨停板/连板梯队结构化数据。"""
    cached = await cache_get("sr:market:limit_up")
    if cached:
        return cached

    data = await _read_snapshot(db, "limit_up")
    if data:
        await cache_set("sr:market:limit_up", data, ttl=300)
        return data

    return {}


@router.get("/quote/{code}")
async def stock_quote(code: str):
    """单只股票实时行情 — 仅用 Redis 短缓存（30s），不落库。"""
    cache_key = f"sr:quote:{code}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    mgr = get_data_manager()
    quote = await _with_timeout(mgr.get_realtime_quote(code))
    if quote:
        await cache_set(cache_key, quote, ttl=30)
        return quote
    return {"error": "Quote not available", "code": code}
