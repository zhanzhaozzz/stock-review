"""自选股管理 API。

数据流：
  1. POST /sync/watchlist_quotes — 批量采集自选股行情 → 写入 stock_prices 表 + Redis
  2. GET  /watchlist               — 从 SQLite(watchlist + stock_prices + ratings) 查询
"""
import asyncio
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.cache import cache_get, cache_set
from app.models.watchlist import Watchlist
from app.models.stock import StockPrice
from app.models.rating import Rating
from app.schemas.watchlist import (
    WatchlistAddRequest,
    WatchlistItem,
    WatchlistUpdateRequest,
    StockSearchItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_USER_ID = 1


def _detect_market(code: str) -> str:
    if code.upper().endswith(".HK") or code.lower().startswith("hk"):
        return "HK"
    return "A"


async def _resolve_name(code: str) -> str:
    try:
        from app.data_provider.manager import get_data_manager
        mgr = get_data_manager()
        quote = await mgr.get_realtime_quote(code)
        if quote and quote.get("name"):
            return quote["name"]
    except Exception:
        pass
    return code


async def sync_watchlist_quotes():
    """批量采集自选股行情 → 写入 stock_prices 表。

    被 sync API 调用。
    """
    async with async_session() as db:
        stmt = select(Watchlist.code).where(Watchlist.user_id == DEFAULT_USER_ID)
        result = await db.execute(stmt)
        codes = [r[0] for r in result.all()]

    if not codes:
        return {"synced": 0}

    from app.data_provider.manager import get_data_manager
    mgr = get_data_manager()
    today = date.today()
    synced = 0

    async def _fetch_and_save(code: str):
        nonlocal synced
        try:
            quote = await asyncio.wait_for(mgr.get_realtime_quote(code), timeout=10)
            if not quote:
                return
            await cache_set(f"sr:quote:{code}", quote, ttl=60)

            async with async_session() as session:
                existing = await session.execute(
                    select(StockPrice.id)
                    .where(StockPrice.code == code, StockPrice.date == today)
                    .limit(1)
                )
                row = existing.scalar_one_or_none()
                if row:
                    await session.execute(
                        select(StockPrice)
                        .where(StockPrice.id == row)
                    )
                    sp = (await session.execute(
                        select(StockPrice).where(StockPrice.id == row)
                    )).scalar_one()
                    sp.close = quote.get("price")
                    sp.open = quote.get("open", sp.open)
                    sp.high = quote.get("high", sp.high)
                    sp.low = quote.get("low", sp.low)
                    sp.volume = quote.get("volume")
                    sp.turnover = quote.get("turnover")
                    sp.change_pct = quote.get("change_pct")
                else:
                    sp = StockPrice(
                        code=code,
                        date=today,
                        open=quote.get("open"),
                        high=quote.get("high"),
                        low=quote.get("low"),
                        close=quote.get("price"),
                        volume=quote.get("volume"),
                        turnover=quote.get("turnover"),
                        change_pct=quote.get("change_pct"),
                    )
                    session.add(sp)
                await session.commit()
                synced += 1
        except Exception as e:
            logger.debug("Quote sync failed for %s: %s", code, e)

    sem = asyncio.Semaphore(5)

    async def _bounded(code):
        async with sem:
            await _fetch_and_save(code)

    await asyncio.gather(*[_bounded(c) for c in codes])
    logger.info("Watchlist quotes synced: %d/%d", synced, len(codes))
    return {"synced": synced, "total": len(codes)}


@router.get("", response_model=list[WatchlistItem])
async def list_watchlist(
    group: str = Query(None, description="按分组筛选"),
    db: AsyncSession = Depends(get_db),
):
    """自选股列表(从 SQLite 读取行情 + 评级)。"""
    stmt = select(Watchlist).where(Watchlist.user_id == DEFAULT_USER_ID)
    if group:
        stmt = stmt.where(Watchlist.group_name == group)
    stmt = stmt.order_by(Watchlist.sort_order, Watchlist.created_at.desc())
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return []

    items = []
    for w in rows:
        latest_score = None
        latest_label = None
        r_stmt = (
            select(Rating)
            .where(Rating.code == w.code)
            .order_by(desc(Rating.date))
            .limit(1)
        )
        r_result = await db.execute(r_stmt)
        rating = r_result.scalar_one_or_none()
        if rating:
            latest_score = rating.total_score
            latest_label = rating.rating

        price = None
        change_pct = None
        p_stmt = (
            select(StockPrice)
            .where(StockPrice.code == w.code)
            .order_by(desc(StockPrice.date))
            .limit(1)
        )
        p_result = await db.execute(p_stmt)
        sp = p_result.scalar_one_or_none()
        if sp:
            price = sp.close
            change_pct = sp.change_pct

        items.append(WatchlistItem(
            id=w.id,
            code=w.code,
            name=w.name,
            market=w.market,
            group_name=w.group_name or "默认",
            note=w.note,
            sort_order=w.sort_order,
            latest_rating=latest_score,
            latest_label=latest_label,
            price=price,
            change_pct=change_pct,
        ))

    return items


@router.post("", response_model=list[WatchlistItem])
async def add_to_watchlist(
    req: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
):
    """添加自选(单只/批量)。"""
    added = []
    for code in req.codes:
        existing = await db.execute(
            select(Watchlist).where(
                Watchlist.user_id == DEFAULT_USER_ID,
                Watchlist.code == code,
            )
        )
        if existing.scalar_one_or_none():
            continue

        name = await _resolve_name(code)
        market = _detect_market(code)
        w = Watchlist(
            user_id=DEFAULT_USER_ID,
            code=code,
            name=name,
            market=market,
            group_name=req.group_name,
        )
        db.add(w)
        await db.flush()
        added.append(WatchlistItem(
            id=w.id,
            code=w.code,
            name=w.name,
            market=w.market,
            group_name=w.group_name or "默认",
        ))

    await db.commit()
    return added


@router.delete("/{code}")
async def remove_from_watchlist(code: str, db: AsyncSession = Depends(get_db)):
    """删除自选股。"""
    stmt = delete(Watchlist).where(
        Watchlist.user_id == DEFAULT_USER_ID,
        Watchlist.code == code,
    )
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found in watchlist")
    return {"ok": True, "code": code}


@router.put("/{code}")
async def update_watchlist_item(
    code: str,
    req: WatchlistUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """修改自选股备注/分组/排序。"""
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == DEFAULT_USER_ID,
            Watchlist.code == code,
        )
    )
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=404, detail="Not found in watchlist")

    if req.note is not None:
        w.note = req.note
    if req.group_name is not None:
        w.group_name = req.group_name
    if req.sort_order is not None:
        w.sort_order = req.sort_order

    await db.commit()
    return {"ok": True, "code": code}


@router.get("/groups", response_model=list[str])
async def watchlist_groups(db: AsyncSession = Depends(get_db)):
    """获取自选股分组列表。"""
    stmt = (
        select(Watchlist.group_name)
        .where(Watchlist.user_id == DEFAULT_USER_ID)
        .distinct()
    )
    result = await db.execute(stmt)
    return [r[0] or "默认" for r in result.all()]


@router.get("/search", response_model=list[StockSearchItem])
async def search_stock(q: str = Query(..., min_length=1, description="搜索关键词")):
    """搜索股票(支持代码/名称模糊搜索)。"""
    try:
        import akshare as ak
        import asyncio
        df = await asyncio.to_thread(ak.stock_info_a_code_name)
        if df is not None and not df.empty:
            mask = df["code"].str.contains(q) | df["name"].str.contains(q, na=False)
            matched = df[mask].head(20)
            return [
                StockSearchItem(code=row["code"], name=row["name"])
                for _, row in matched.iterrows()
            ]
    except Exception as e:
        logger.warning("Stock search failed: %s", e)
    return []
