"""新闻聚合 API。

数据流：
  1. POST /news/sync  — 手动触发采集（或定时任务调用），外部接口 → SQLite
  2. GET  /news/latest — 前端查询，从 SQLite 读取
  3. GET  /news/stock/{code} — 个股新闻，从 SQLite 按 related_codes 过滤
  4. GET  /news/flash  — 快讯，从 SQLite 按 source=cls 过滤
"""
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.models.news import NewsCache
from app.schemas.news import NewsItemResponse

logger = logging.getLogger(__name__)
router = APIRouter()


async def _save_news_to_db(items, session: AsyncSession):
    """将采集到的新闻去重后写入 SQLite。"""
    saved = 0
    for n in items:
        existing = await session.execute(
            select(NewsCache.id).where(NewsCache.url == n.url).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue
        obj = NewsCache(
            title=n.title,
            url=n.url,
            source=n.source,
            summary=n.summary or "",
            publish_time=n.publish_time,
            related_codes=n.related_codes if n.related_codes else None,
        )
        session.add(obj)
        saved += 1

    if saved > 0:
        await session.commit()
    return saved


@router.post("/sync")
async def sync_news():
    """手动触发新闻采集：调外部接口 → 写入 SQLite。"""
    from app.news.aggregator import get_aggregator

    agg = get_aggregator()
    try:
        items = await asyncio.wait_for(agg.fetch_latest(limit=80), timeout=30)
    except asyncio.TimeoutError:
        logger.warning("News sync timed out after 30s")
        items = []
    except Exception as e:
        logger.error("News sync failed: %s", e)
        items = []

    saved = 0
    if items:
        async with async_session() as session:
            saved = await _save_news_to_db(items, session)

    logger.info("News sync done: fetched=%d, saved=%d", len(items), saved)
    return {"fetched": len(items), "saved": saved}


@router.get("/latest", response_model=list[NewsItemResponse])
async def latest_news(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """最新新闻 — 从 SQLite 读取。"""
    stmt = (
        select(NewsCache)
        .order_by(desc(NewsCache.publish_time), desc(NewsCache.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        NewsItemResponse(
            title=r.title,
            url=r.url,
            source=r.source,
            summary=r.summary or "",
            publish_time=r.publish_time.isoformat() if r.publish_time else None,
            related_codes=r.related_codes or [],
        )
        for r in rows
    ]


@router.get("/stock/{code}", response_model=list[NewsItemResponse])
async def stock_news(
    code: str,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """个股相关新闻 — 从 SQLite 按标题/related_codes 模糊查找。"""
    name = code
    try:
        from app.data_provider.manager import get_data_manager
        mgr = get_data_manager()
        quote = await mgr.get_realtime_quote(code)
        if quote and quote.get("name"):
            name = quote["name"]
    except Exception:
        pass

    clean_code = code.split(".")[0]
    stmt = (
        select(NewsCache)
        .where(
            or_(
                NewsCache.title.contains(name),
                NewsCache.title.contains(clean_code),
            )
        )
        .order_by(desc(NewsCache.publish_time))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        NewsItemResponse(
            title=r.title,
            url=r.url,
            source=r.source,
            summary=r.summary or "",
            publish_time=r.publish_time.isoformat() if r.publish_time else None,
        )
        for r in rows
    ]


@router.get("/flash", response_model=list[NewsItemResponse])
async def flash_news(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """财联社快讯 — 从 SQLite 按 source 过滤。"""
    stmt = (
        select(NewsCache)
        .where(NewsCache.source.in_(["财联社", "财联社(东财)"]))
        .order_by(desc(NewsCache.publish_time), desc(NewsCache.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        NewsItemResponse(
            title=r.title,
            url=r.url,
            source=r.source,
            summary=r.summary or "",
            publish_time=r.publish_time.isoformat() if r.publish_time else None,
        )
        for r in rows
    ]
