"""操作记录 Pydantic 模型。"""
from pydantic import BaseModel
from typing import Optional


class OperationRecordCreate(BaseModel):
    date: str
    strategy_used: str = ""
    target_stock: str = ""
    action: str = ""
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    note: str = ""
    is_correct: Optional[bool] = None


class OperationRecordUpdate(BaseModel):
    strategy_used: Optional[str] = None
    target_stock: Optional[str] = None
    action: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    note: Optional[str] = None
    is_correct: Optional[bool] = None


class OperationRecordItem(BaseModel):
    id: int
    date: str
    strategy_used: str = ""
    target_stock: str = ""
    action: str = ""
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    note: str = ""
    is_correct: Optional[bool] = None
    created_at: str = ""
