"""操作记录 API — CRUD + 统计。"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sentiment import OperationRecord
from app.schemas.sentiment import (
    OperationRecordCreate,
    OperationRecordUpdate,
    OperationRecordItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list", response_model=list[OperationRecordItem])
async def list_operations(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """操作记录列表。"""
    stmt = select(OperationRecord).order_by(desc(OperationRecord.date)).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_to_item(r) for r in rows]


@router.post("/create", response_model=OperationRecordItem)
async def create_operation(req: OperationRecordCreate, db: AsyncSession = Depends(get_db)):
    """新增操作记录。"""
    obj = OperationRecord(
        date=date.fromisoformat(req.date),
        strategy_used=req.strategy_used,
        target_stock=req.target_stock,
        action=req.action,
        entry_price=req.entry_price,
        exit_price=req.exit_price,
        pnl_pct=req.pnl_pct,
        note=req.note,
        is_correct=req.is_correct,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return _to_item(obj)


@router.put("/{record_id}", response_model=OperationRecordItem)
async def update_operation(
    record_id: int,
    req: OperationRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新操作记录。"""
    stmt = select(OperationRecord).where(OperationRecord.id == record_id)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="操作记录不存在")

    for field, value in req.model_dump(exclude_none=True).items():
        if field == "date":
            value = date.fromisoformat(value)
        setattr(r, field, value)

    await db.commit()
    await db.refresh(r)
    return _to_item(r)


@router.delete("/{record_id}")
async def delete_operation(record_id: int, db: AsyncSession = Depends(get_db)):
    """删除操作记录。"""
    stmt = select(OperationRecord).where(OperationRecord.id == record_id)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="操作记录不存在")

    await db.delete(r)
    await db.commit()
    return {"message": "操作记录已删除"}


@router.get("/stats")
async def operation_stats(db: AsyncSession = Depends(get_db)):
    """操作统计: 胜率、总盈亏等。"""
    stmt = select(OperationRecord).where(OperationRecord.pnl_pct.isnot(None))
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return {"total": 0, "win_rate": 0, "avg_pnl": 0, "total_pnl": 0, "correct_rate": 0, "by_strategy": [], "by_cycle": []}

    total = len(rows)
    wins = sum(1 for r in rows if r.pnl_pct and r.pnl_pct > 0)
    total_pnl = sum(r.pnl_pct or 0 for r in rows)
    avg_pnl = total_pnl / total if total else 0

    correct_count = sum(1 for r in rows if r.is_correct)
    correct_rate = correct_count / total * 100 if total else 0

    by_strategy: dict[str, list[float]] = {}
    for r in rows:
        key = (r.strategy_used or "未填写").strip() or "未填写"
        by_strategy.setdefault(key, []).append(r.pnl_pct or 0)

    strategy_stats = []
    for k, vals in by_strategy.items():
        t = len(vals)
        w = sum(1 for v in vals if v > 0)
        strategy_stats.append({
            "strategy": k,
            "total": t,
            "win_rate": round(w / t * 100, 1) if t else 0,
            "avg_pnl": round(sum(vals) / t, 2) if t else 0,
        })
    strategy_stats.sort(key=lambda x: (x["total"], x["win_rate"]), reverse=True)

    cycle_map: dict[str, str] = {}
    try:
        from app.models.sentiment import SentimentCycleLog
        stmt2 = select(SentimentCycleLog)
        r2 = await db.execute(stmt2)
        logs = r2.scalars().all()
        for l in logs:
            cycle_map[str(l.date)] = l.cycle_phase or ""
    except Exception:
        cycle_map = {}

    by_cycle: dict[str, list[float]] = {}
    for r in rows:
        phase = cycle_map.get(str(r.date), "") or "未知"
        by_cycle.setdefault(phase, []).append(r.pnl_pct or 0)

    cycle_stats = []
    for k, vals in by_cycle.items():
        t = len(vals)
        w = sum(1 for v in vals if v > 0)
        cycle_stats.append({
            "cycle": k,
            "total": t,
            "win_rate": round(w / t * 100, 1) if t else 0,
            "avg_pnl": round(sum(vals) / t, 2) if t else 0,
        })
    cycle_stats.sort(key=lambda x: x["total"], reverse=True)

    return {
        "total": total,
        "win_rate": round(wins / total * 100, 1) if total else 0,
        "avg_pnl": round(avg_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "correct_rate": round(correct_rate, 1),
        "by_strategy": strategy_stats,
        "by_cycle": cycle_stats,
    }


def _to_item(r: OperationRecord) -> OperationRecordItem:
    return OperationRecordItem(
        id=r.id,
        date=str(r.date),
        strategy_used=r.strategy_used or "",
        target_stock=r.target_stock or "",
        action=r.action or "",
        entry_price=r.entry_price,
        exit_price=r.exit_price,
        pnl_pct=r.pnl_pct,
        note=r.note or "",
        is_correct=r.is_correct,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )
