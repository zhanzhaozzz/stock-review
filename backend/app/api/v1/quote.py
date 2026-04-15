"""交易语录 API — CRUD。"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.quote import TradingQuote
from app.schemas.quote import QuoteItem, QuoteCreateRequest, QuoteUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list", response_model=list[QuoteItem])
async def list_quotes(
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """语录列表（按日期降序）。"""
    stmt = select(TradingQuote).order_by(desc(TradingQuote.date)).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        QuoteItem(
            id=r.id,
            date=str(r.date),
            content=r.content or "",
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


@router.post("/create", response_model=QuoteItem)
async def create_quote(
    req: QuoteCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """新增语录。"""
    try:
        d = date.fromisoformat(req.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    quote = TradingQuote(date=d, content=req.content)
    db.add(quote)
    await db.commit()
    await db.refresh(quote)
    return QuoteItem(
        id=quote.id,
        date=str(quote.date),
        content=quote.content,
        created_at=quote.created_at.isoformat() if quote.created_at else "",
    )


@router.put("/{quote_id}", response_model=QuoteItem)
async def update_quote(
    quote_id: int,
    req: QuoteUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """编辑语录。"""
    stmt = select(TradingQuote).where(TradingQuote.id == quote_id)
    result = await db.execute(stmt)
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="语录不存在")

    payload = req.model_dump(exclude_none=True)
    if "date" in payload:
        try:
            payload["date"] = date.fromisoformat(payload["date"])
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误")
    for field, value in payload.items():
        setattr(quote, field, value)

    await db.commit()
    await db.refresh(quote)
    return QuoteItem(
        id=quote.id,
        date=str(quote.date),
        content=quote.content,
        created_at=quote.created_at.isoformat() if quote.created_at else "",
    )


@router.delete("/{quote_id}")
async def delete_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除语录。"""
    stmt = select(TradingQuote).where(TradingQuote.id == quote_id)
    result = await db.execute(stmt)
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="语录不存在")

    await db.delete(quote)
    await db.commit()
    return {"message": "语录已删除"}
