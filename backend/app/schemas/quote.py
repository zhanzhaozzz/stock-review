"""交易语录相关 Pydantic 模型。"""
from pydantic import BaseModel
from typing import Optional


class QuoteItem(BaseModel):
    id: int
    date: str
    content: str
    created_at: str = ""


class QuoteCreateRequest(BaseModel):
    date: str
    content: str


class QuoteUpdateRequest(BaseModel):
    date: Optional[str] = None
    content: Optional[str] = None
