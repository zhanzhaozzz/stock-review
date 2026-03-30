"""新闻相关的 Pydantic 模型。"""
from pydantic import BaseModel


class NewsItemResponse(BaseModel):
    title: str
    url: str
    source: str
    summary: str = ""
    publish_time: str | None = None
    related_codes: list[str] = []
