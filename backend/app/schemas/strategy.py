"""战法库 Pydantic 模型。"""
from pydantic import BaseModel
from typing import Optional


class StrategyCreate(BaseModel):
    name: str
    applicable_cycles: list[str] = []
    conditions: str = ""
    entry_rules: str = ""
    exit_rules: str = ""
    position_rules: str = ""
    buy_point_rules: str = ""
    sort_order: int = 0


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    applicable_cycles: Optional[list[str]] = None
    conditions: Optional[str] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    position_rules: Optional[str] = None
    buy_point_rules: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class StrategyItem(BaseModel):
    id: int
    name: str
    applicable_cycles: list[str] = []
    conditions: str = ""
    entry_rules: str = ""
    exit_rules: str = ""
    position_rules: str = ""
    buy_point_rules: str = ""
    is_active: bool = True
    sort_order: int = 0
    created_at: str = ""
