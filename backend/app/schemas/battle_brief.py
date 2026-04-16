"""V1 BattleBrief Pydantic schemas。"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

StatusTone = Literal["可做", "轻仓试错", "防守观察", "不做"]


class BattleBriefCreate(BaseModel):
    date: date
    status_tone: Optional[StatusTone] = None
    suggested_position: Optional[str] = None
    overall_conclusion: Optional[str] = None
    macro_context: Optional[list] = None
    main_narrative: Optional[list] = None
    bullish_sectors: Optional[list] = None
    bearish_sectors: Optional[list] = None
    risk_tips: Optional[list] = None
    allowed_actions: Optional[list] = None
    forbidden_actions: Optional[list] = None


class BattleBriefUpdate(BaseModel):
    status_tone: Optional[StatusTone] = None
    suggested_position: Optional[str] = None
    overall_conclusion: Optional[str] = None
    macro_context: Optional[list] = None
    main_narrative: Optional[list] = None
    bullish_sectors: Optional[list] = None
    bearish_sectors: Optional[list] = None
    risk_tips: Optional[list] = None
    allowed_actions: Optional[list] = None
    forbidden_actions: Optional[list] = None


class BattleBriefRead(BaseModel):
    date: date
    status_tone: Optional[str] = None
    suggested_position: Optional[str] = None
    overall_conclusion: Optional[str] = None
    macro_context: Optional[list] = None
    main_narrative: Optional[list] = None
    bullish_sectors: Optional[list] = None
    bearish_sectors: Optional[list] = None
    risk_tips: Optional[list] = None
    allowed_actions: Optional[list] = None
    forbidden_actions: Optional[list] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
