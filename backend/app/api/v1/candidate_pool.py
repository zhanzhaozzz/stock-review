"""V1 候选池 API。"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core import candidate_pool_service
from app.schemas.candidate_pool import (
    CandidatePoolEntryRead,
    CandidatePoolEntryUpdate,
)

router = APIRouter()


@router.get("/today", response_model=list[CandidatePoolEntryRead])
async def get_candidates_today(db: AsyncSession = Depends(get_db)):
    today = date.today()
    entries = await candidate_pool_service.list_by_date(db, today)
    return [
        CandidatePoolEntryRead.model_validate(e, from_attributes=True)
        for e in entries
    ]


@router.get("", response_model=list[CandidatePoolEntryRead])
async def get_candidates_by_date(
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    if date:
        try:
            from datetime import date as date_cls
            target_date = date_cls.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，需 YYYY-MM-DD")
    else:
        from datetime import date as date_cls
        target_date = date_cls.today()

    entries = await candidate_pool_service.list_by_date(db, target_date)
    return [
        CandidatePoolEntryRead.model_validate(e, from_attributes=True)
        for e in entries
    ]


@router.put("/{entry_id}", response_model=CandidatePoolEntryRead)
async def update_candidate(
    entry_id: int,
    data: CandidatePoolEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    entry = await candidate_pool_service.update_entry(db, entry_id, data)
    if not entry:
        raise HTTPException(status_code=404, detail="候选池条目不存在")
    return CandidatePoolEntryRead.model_validate(entry, from_attributes=True)
