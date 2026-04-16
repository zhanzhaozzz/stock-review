"""V1 CandidatePoolEntry Pydantic schemas。"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

SourceType = Literal["梯队", "事件", "观察池"]
GateStatus = Literal["通过", "观察", "拦截"]
ActionHint = Literal["重点跟踪", "轻仓试错", "观察等待", "放弃"]
ReviewOutcome = Literal["待复盘", "逻辑兑现", "时机未到", "逻辑证伪", "纪律拦截正确"]


class CandidatePoolEntryCreate(BaseModel):
    date: date
    code: str
    name: str
    source_type: SourceType
    source_reason: Optional[str] = None
    theme: Optional[str] = None
    thesis: Optional[str] = None
    gate_status: Optional[GateStatus] = None
    gate_reason: Optional[str] = None
    action_hint: Optional[ActionHint] = None
    risk_flags: Optional[list] = None
    review_outcome: Optional[ReviewOutcome] = "待复盘"
    review_note: Optional[str] = None


class CandidatePoolEntryUpdate(BaseModel):
    gate_status: Optional[GateStatus] = None
    gate_reason: Optional[str] = None
    action_hint: Optional[ActionHint] = None
    review_outcome: Optional[ReviewOutcome] = None
    review_note: Optional[str] = None


class CandidatePoolEntryRead(BaseModel):
    id: int
    date: date
    code: str
    name: str
    source_type: Optional[str] = None
    source_reason: Optional[str] = None
    theme: Optional[str] = None
    thesis: Optional[str] = None
    gate_status: Optional[str] = None
    gate_reason: Optional[str] = None
    action_hint: Optional[str] = None
    risk_flags: Optional[list] = None
    review_outcome: Optional[str] = "待复盘"
    review_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
