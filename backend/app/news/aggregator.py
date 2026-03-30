"""新闻聚合器 — 并行采集 + 标题去重 + 时间排序。"""
import asyncio
import logging
from difflib import SequenceMatcher

from app.news.base import NewsItem
from app.news.cls_collector import CLSCollector
from app.news.eastmoney_collector import EastMoneyCollector
from app.news.sina_collector import SinaCollector

logger = logging.getLogger(__name__)


class NewsAggregator:
    """并行调用多个新闻采集器，合并去重后返回。"""

    def __init__(self):
        self.collectors = [
            CLSCollector(),
            EastMoneyCollector(),
            SinaCollector(),
        ]

    async def fetch_latest(self, limit: int = 50) -> list[NewsItem]:
        """并行采集最新新闻，去重后按时间倒序。"""
        tasks = [c.fetch_latest(limit=limit) for c in self.collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: list[NewsItem] = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Collector error: %s", r)
                continue
            all_items.extend(r)

        deduped = self._deduplicate(all_items)
        deduped.sort(key=lambda x: x.publish_time or _MIN_DT, reverse=True)

        logger.info("Aggregated: %d raw -> %d deduped", len(all_items), len(deduped))
        return deduped[:limit]

    async def fetch_by_stock(self, code: str, name: str, limit: int = 20) -> list[NewsItem]:
        """获取个股相关新闻（目前仅东方财富支持搜索）。"""
        tasks = [c.fetch_by_stock(code, name, limit) for c in self.collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: list[NewsItem] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            all_items.extend(r)

        deduped = self._deduplicate(all_items)
        deduped.sort(key=lambda x: x.publish_time or _MIN_DT, reverse=True)
        return deduped[:limit]

    @staticmethod
    def _deduplicate(items: list[NewsItem], threshold: float = 0.8) -> list[NewsItem]:
        """标题去重：完全相同或相似度 > threshold 视为重复。"""
        seen_titles: list[str] = []
        result: list[NewsItem] = []
        for item in items:
            title = item.title.strip()
            if not title:
                continue
            is_dup = False
            for seen in seen_titles:
                if title == seen:
                    is_dup = True
                    break
                if title[:15] == seen[:15]:
                    is_dup = True
                    break
                if SequenceMatcher(None, title, seen).ratio() > threshold:
                    is_dup = True
                    break
            if not is_dup:
                seen_titles.append(title)
                result.append(item)
        return result


from datetime import datetime as _dt
_MIN_DT = _dt(2000, 1, 1)

_aggregator: NewsAggregator | None = None


def get_aggregator() -> NewsAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = NewsAggregator()
    return _aggregator
