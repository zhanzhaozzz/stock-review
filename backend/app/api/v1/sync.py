"""数据同步 API — 统一入口，从外部采集 → 写入 SQLite + Redis 热缓存。

所有模块的"采集"逻辑集中在这里，前端查询接口只读 SQLite/Redis。
"""
import asyncio
import logging
from datetime import date, datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.cache import cache_set
from app.database import async_session
from app.models.market import MarketSnapshot

logger = logging.getLogger(__name__)
router = APIRouter()


async def _upsert_snapshot(session, snapshot_type: str, data):
    """写入或更新 market_snapshots 表。"""
    today = date.today()
    existing = await session.execute(
        select(MarketSnapshot)
        .where(
            MarketSnapshot.snapshot_type == snapshot_type,
            MarketSnapshot.date == today,
        )
        .limit(1)
    )
    row = existing.scalar_one_or_none()
    if row:
        row.data = data
        row.updated_at = datetime.now()
    else:
        session.add(MarketSnapshot(
            date=today,
            snapshot_type=snapshot_type,
            data=data,
        ))


@router.post("/all")
async def sync_all():
    """一键同步：串行采集市场+新闻+自选股行情 → 全部落库。

    SQLite 不支持并发写入，并行 session 会导致 database is locked，
    因此改为串行执行；数据采集（网络 IO）仍在各函数内部并行。
    """
    results = {}
    results["market"] = await _sync_market()
    results["news"] = await _sync_news()
    results["watchlist_quotes"] = await _sync_watchlist_quotes()
    return results


@router.post("/market")
async def sync_market_api():
    """同步市场数据 → SQLite + Redis。"""
    return await _sync_market()


@router.post("/news")
async def sync_news_api():
    """采集新闻 → SQLite。"""
    return await _sync_news()


@router.post("/watchlist-quotes")
async def sync_watchlist_quotes_api():
    """同步自选股行情 → stock_prices 表。"""
    return await _sync_watchlist_quotes()


async def _sync_market() -> dict:
    """采集大盘指数/涨跌面/板块排行/资金流向/涨停板 → 写入 SQLite + Redis。"""
    refreshed = []

    async with async_session() as session:
        try:
            from app.core.market_review import get_market_overview
            data = await asyncio.wait_for(get_market_overview(), timeout=25)
            if data:
                await _upsert_snapshot(session, "overview", data)
                await cache_set("sr:market:overview", data, ttl=120)
                if "breadth" in data:
                    await cache_set("sr:market:breadth", data["breadth"], ttl=120)
                refreshed.append("overview")
        except Exception as e:
            logger.warning("Market overview sync failed: %s", e)
            await session.rollback()

        try:
            from app.core.market_review import get_sector_ranking
            data = await asyncio.wait_for(get_sector_ranking("concept", 30), timeout=20)
            if data:
                await _upsert_snapshot(session, "sectors_concept", data)
                await cache_set("sr:market:sectors:concept", data, ttl=120)
                refreshed.append("sectors_concept")
        except Exception as e:
            logger.warning("Sector concept sync failed: %s", e)
            await session.rollback()

        try:
            from app.core.market_review import get_sector_ranking
            data = await asyncio.wait_for(get_sector_ranking("industry", 30), timeout=20)
            if data:
                await _upsert_snapshot(session, "sectors_industry", data)
                await cache_set("sr:market:sectors:industry", data, ttl=120)
                refreshed.append("sectors_industry")
        except Exception as e:
            logger.warning("Sector industry sync failed: %s", e)
            await session.rollback()

        try:
            from app.core.market_review import get_money_flow
            data = await asyncio.wait_for(get_money_flow(), timeout=20)
            if data:
                await _upsert_snapshot(session, "money_flow", data)
                await cache_set("sr:market:money_flow", data, ttl=120)
                refreshed.append("money_flow")
        except Exception as e:
            logger.warning("Money flow sync failed: %s", e)
            await session.rollback()

        try:
            from app.core.limit_up_tracker import get_limit_up_data
            data = await asyncio.wait_for(get_limit_up_data("today"), timeout=20)
            if data:
                await _upsert_snapshot(session, "limit_up", data)
                await cache_set("sr:market:limit_up", data, ttl=300)
                refreshed.append("limit_up")
        except Exception as e:
            logger.warning("Limit up sync failed: %s", e)
            await session.rollback()

        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.warning("Market sync commit failed: %s", e)

    logger.info("Market sync done: %s", refreshed)
    return {"status": "ok", "refreshed": refreshed}


async def _sync_news() -> dict:
    """采集新闻 → 写入 news_cache 表。"""
    from app.news.aggregator import get_aggregator
    from app.api.v1.news import _save_news_to_db

    agg = get_aggregator()
    try:
        items = await asyncio.wait_for(agg.fetch_latest(limit=80), timeout=30)
    except asyncio.TimeoutError:
        logger.warning("News sync timed out")
        items = []
    except Exception as e:
        logger.error("News sync failed: %s", e)
        items = []

    saved = 0
    if items:
        async with async_session() as session:
            saved = await _save_news_to_db(items, session)

    logger.info("News sync done: fetched=%d, saved=%d", len(items), saved)
    return {"status": "ok", "fetched": len(items), "saved": saved}


async def _sync_watchlist_quotes() -> dict:
    """批量采集自选股行情 → 写入 stock_prices 表。"""
    from app.api.v1.watchlist import sync_watchlist_quotes
    return await sync_watchlist_quotes()
