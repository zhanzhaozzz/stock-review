"""新闻采集器基类和数据模型。"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    summary: str = ""
    publish_time: Optional[datetime] = None
    related_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "related_codes": self.related_codes,
        }


class BaseCollector(ABC):
    """新闻采集器抽象基类。"""
    name: str = "base"

    @abstractmethod
    async def fetch_latest(self, limit: int = 30) -> list[NewsItem]:
        """获取最新新闻列表。"""
        ...

    async def fetch_by_stock(self, code: str, name: str, limit: int = 10) -> list[NewsItem]:
        """获取个股相关新闻（默认不支持，子类按需重写）。"""
        return []
