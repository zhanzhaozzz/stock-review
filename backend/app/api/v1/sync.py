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
    results["fundamentals"] = await _sync_fundamentals()
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


@router.post("/watchlist-klines")
async def sync_watchlist_klines_api():
    """批量预加载自选股日线历史 → stock_prices 表。"""
    return await _preload_watchlist_klines()


async def _preload_watchlist_klines() -> dict:
    """遍历自选股，对本地 K 线不足 30 条的补充拉取 60 日历史并落库。"""
    from app.models.watchlist import Watchlist
    from app.models.stock import StockPrice
    from app.data_provider.manager import get_data_manager
    from sqlalchemy import func

    synced = 0
    skipped = 0
    failed = 0
    sem = asyncio.Semaphore(3)

    async with async_session() as session:
        wl_result = await session.execute(select(Watchlist))
        codes = list({row.code for row in wl_result.scalars().all()})

    if not codes:
        return {"status": "ok", "synced": 0, "message": "no watchlist stocks"}

    mgr = get_data_manager()

    async def _fetch_one(code: str):
        nonlocal synced, skipped, failed
        async with sem:
            try:
                async with async_session() as db:
                    count_result = await db.execute(
                        select(func.count()).select_from(StockPrice).where(StockPrice.code == code)
                    )
                    count = count_result.scalar() or 0
                    if count >= 30:
                        skipped += 1
                        return

                    df = await asyncio.wait_for(mgr.get_daily(code, 60), timeout=15)
                    if df is None or df.empty:
                        skipped += 1
                        return

                    existing_result = await db.execute(
                        select(StockPrice).where(StockPrice.code == code)
                    )
                    existing_map = {str(r.date): r for r in existing_result.scalars().all()}

                    records = df.to_dict(orient="records")
                    for rec in records:
                        d = str(rec.get("date", ""))
                        if not d:
                            continue
                        if d in existing_map:
                            row = existing_map[d]
                            row.open = rec.get("open")
                            row.high = rec.get("high")
                            row.low = rec.get("low")
                            row.close = rec.get("close")
                            row.volume = rec.get("volume")
                            row.turnover = rec.get("turnover")
                            row.change_pct = rec.get("change_pct")
                        else:
                            try:
                                db.add(StockPrice(
                                    code=code,
                                    date=date.fromisoformat(d),
                                    open=rec.get("open"),
                                    high=rec.get("high"),
                                    low=rec.get("low"),
                                    close=rec.get("close"),
                                    volume=rec.get("volume"),
                                    turnover=rec.get("turnover"),
                                    change_pct=rec.get("change_pct"),
                                ))
                            except (ValueError, TypeError):
                                continue
                    await db.commit()
                    synced += 1
            except Exception as e:
                logger.warning("Kline preload failed for %s: %s", code, e)
                failed += 1

    await asyncio.gather(*[_fetch_one(c) for c in codes])
    logger.info("Watchlist klines preload done: synced=%d, skipped=%d, failed=%d", synced, skipped, failed)
    return {"status": "ok", "synced": synced, "skipped": skipped, "failed": failed}


@router.post("/fundamentals")
async def sync_fundamentals_api():
    """采集自选股基本面数据 → stock_fundamentals 表。"""
    return await _sync_fundamentals()


async def _sync_fundamentals() -> dict:
    """遍历自选股列表，采集基本面 + 计算多周期涨跌幅，upsert 到 stock_fundamentals。"""
    from app.data_provider.fundamental import get_fundamental, compute_price_derived
    from app.models.fundamental import StockFundamental
    from app.models.watchlist import Watchlist

    today = date.today()
    synced = 0
    failed = 0

    async with async_session() as session:
        wl_result = await session.execute(select(Watchlist))
        watchlist_rows = wl_result.scalars().all()
        codes = list({row.code for row in watchlist_rows})

        if not codes:
            return {"status": "ok", "synced": 0, "message": "no watchlist stocks"}

        for code in codes:
            try:
                fund_data = await get_fundamental(code)
                if not fund_data:
                    failed += 1
                    continue

                derived = await compute_price_derived(code, session)

                existing = await session.execute(
                    select(StockFundamental)
                    .where(
                        StockFundamental.code == code,
                        StockFundamental.date == today,
                    )
                    .limit(1)
                )
                row = existing.scalar_one_or_none()

                fields = {
                    "pe_ttm": fund_data.get("pe_ttm"),
                    "pb_mrq": fund_data.get("pb_mrq"),
                    "roe": fund_data.get("roe"),
                    "eps": fund_data.get("eps"),
                    "market_cap": fund_data.get("market_cap"),
                    "circulating_cap": fund_data.get("circulating_cap"),
                    "debt_ratio": fund_data.get("debt_ratio"),
                    "main_net_inflow": fund_data.get("main_net_inflow"),
                    "retail_net_inflow": fund_data.get("retail_net_inflow"),
                    "large_net_inflow": fund_data.get("large_net_inflow"),
                    "vol_ratio": fund_data.get("vol_ratio"),
                    "turnover_ratio": fund_data.get("turnover_ratio"),
                    "committee": fund_data.get("committee"),
                    "swing": fund_data.get("swing"),
                    "rise_day_count": derived.get("rise_day_count"),
                    "chg_5d": derived.get("chg_5d"),
                    "chg_10d": derived.get("chg_10d"),
                    "chg_20d": derived.get("chg_20d"),
                    "chg_60d": derived.get("chg_60d"),
                    "chg_year": derived.get("chg_year"),
                }

                if row:
                    for k, v in fields.items():
                        setattr(row, k, v)
                else:
                    session.add(StockFundamental(code=code, date=today, **fields))

                synced += 1
                await asyncio.sleep(0.3)

            except Exception as e:
                logger.warning("Fundamental sync failed for %s: %s", code, e)
                failed += 1

        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Fundamental sync commit failed: %s", e)
            return {"status": "error", "error": str(e)}

    logger.info("Fundamental sync done: synced=%d, failed=%d", synced, failed)
    return {"status": "ok", "synced": synced, "failed": failed}
