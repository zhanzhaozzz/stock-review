"""V1 AI 作战台 API。"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core import market_state_service, battle_brief_service, candidate_pool_service
from app.schemas.market_state import MarketStateDailyRead
from app.schemas.battle_brief import BattleBriefRead
from app.schemas.candidate_pool import CandidatePoolEntryRead

router = APIRouter()


@router.get("/today")
async def get_combat_desk_today(db: AsyncSession = Depends(get_db)):
    today = date.today()

    market_state = await market_state_service.get_by_date(db, today)
    battle_brief = await battle_brief_service.get_by_date(db, today)
    candidates = await candidate_pool_service.list_by_date(db, today)

    return {
        "date": today.isoformat(),
        "market_state": MarketStateDailyRead.model_validate(
            market_state, from_attributes=True
        ) if market_state else None,
        "battle_brief": BattleBriefRead.model_validate(
            battle_brief, from_attributes=True
        ) if battle_brief else None,
        "candidate_preview": [
            CandidatePoolEntryRead.model_validate(c, from_attributes=True)
            for c in candidates[:5]
        ],
    }
