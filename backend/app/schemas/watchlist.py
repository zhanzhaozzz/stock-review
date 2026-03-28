"""自选股相关的 Pydantic 模型。"""
from pydantic import BaseModel, Field


class WatchlistAddRequest(BaseModel):
    codes: list[str] = Field(..., min_length=1, max_length=100, description="股票代码列表")
    group_name: str = "默认"


class WatchlistItem(BaseModel):
    id: int
    code: str
    name: str
    market: str = "A"
    group_name: str = "默认"
    note: str | None = None
    sort_order: int = 0
    latest_rating: float | None = None
    latest_label: str | None = None
    price: float | None = None
    change_pct: float | None = None


class WatchlistUpdateRequest(BaseModel):
    note: str | None = None
    group_name: str | None = None
    sort_order: int | None = None


class StockSearchItem(BaseModel):
    code: str
    name: str
    market: str = "A"
