"""战法库 API — CRUD。"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate, StrategyItem

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list", response_model=list[StrategyItem])
async def list_strategies(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """获取战法列表。"""
    stmt = select(Strategy).order_by(Strategy.sort_order, desc(Strategy.created_at))
    if active_only:
        stmt = stmt.where(Strategy.is_active == True)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_to_item(r) for r in rows]


@router.post("/create", response_model=StrategyItem)
async def create_strategy(req: StrategyCreate, db: AsyncSession = Depends(get_db)):
    """新增战法。"""
    obj = Strategy(
        name=req.name,
        applicable_cycles=req.applicable_cycles,
        conditions=req.conditions,
        entry_rules=req.entry_rules,
        exit_rules=req.exit_rules,
        position_rules=req.position_rules,
        buy_point_rules=req.buy_point_rules,
        sort_order=req.sort_order,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return _to_item(obj)


@router.put("/{strategy_id}", response_model=StrategyItem)
async def update_strategy(
    strategy_id: int,
    req: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新战法。"""
    stmt = select(Strategy).where(Strategy.id == strategy_id)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="战法不存在")

    for field, value in req.model_dump(exclude_none=True).items():
        setattr(r, field, value)

    await db.commit()
    await db.refresh(r)
    return _to_item(r)


@router.get("/recommend")
async def recommend_strategies(db: AsyncSession = Depends(get_db)):
    """基于当前情绪周期推荐适用战法。"""
    from app.core.strategy_matcher import match_strategies
    from app.models.sentiment import SentimentCycleLog

    stmt = select(SentimentCycleLog).order_by(desc(SentimentCycleLog.date)).limit(1)
    result = await db.execute(stmt)
    latest = result.scalar_one_or_none()
    phase = latest.cycle_phase if latest else "震荡"

    return await match_strategies(phase, db)


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, db: AsyncSession = Depends(get_db)):
    """删除战法。"""
    stmt = select(Strategy).where(Strategy.id == strategy_id)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="战法不存在")

    await db.delete(r)
    await db.commit()
    return {"message": "战法已删除"}


def _to_item(r: Strategy) -> StrategyItem:
    return StrategyItem(
        id=r.id,
        name=r.name,
        applicable_cycles=r.applicable_cycles if isinstance(r.applicable_cycles, list) else [],
        conditions=r.conditions or "",
        entry_rules=r.entry_rules or "",
        exit_rules=r.exit_rules or "",
        position_rules=r.position_rules or "",
        buy_point_rules=r.buy_point_rules or "",
        is_active=r.is_active if r.is_active is not None else True,
        sort_order=r.sort_order or 0,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )
