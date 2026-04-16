"""V1 MarketStateDaily Pydantic schemas。"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

MarketPhase = Literal["冰点", "启动", "发酵", "高潮", "高位混沌", "退潮"]
StyleTag = Literal["接力优先", "趋势优先", "轮动试错", "防守观察"]


class MarketStateDailyCreate(BaseModel):
    date: date
    temperature_score: Optional[int] = None
    market_phase: Optional[MarketPhase] = None
    style_tag: Optional[StyleTag] = None
    limit_up_count: Optional[int] = None
    limit_down_count: Optional[int] = None
    boom_rate: Optional[float] = None
    highest_ladder: Optional[int] = None
    promotion_rate: Optional[float] = None
    total_volume: Optional[int] = None
    volume_delta: Optional[int] = None
    focus_sectors: Optional[list] = None
    conclusion: Optional[str] = None


class MarketStateDailyUpdate(BaseModel):
    temperature_score: Optional[int] = None
    market_phase: Optional[MarketPhase] = None
    style_tag: Optional[StyleTag] = None
    limit_up_count: Optional[int] = None
    limit_down_count: Optional[int] = None
    boom_rate: Optional[float] = None
    highest_ladder: Optional[int] = None
    promotion_rate: Optional[float] = None
    total_volume: Optional[int] = None
    volume_delta: Optional[int] = None
    focus_sectors: Optional[list] = None
    conclusion: Optional[str] = None


class MarketStateDailyRead(BaseModel):
    date: date
    temperature_score: Optional[int] = None
    market_phase: Optional[str] = None
    style_tag: Optional[str] = None
    limit_up_count: Optional[int] = None
    limit_down_count: Optional[int] = None
    boom_rate: Optional[float] = None
    highest_ladder: Optional[int] = None
    promotion_rate: Optional[float] = None
    total_volume: Optional[int] = None
    volume_delta: Optional[int] = None
    focus_sectors: Optional[list] = None
    conclusion: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
