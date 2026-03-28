"""DataFetcherManager — unified data access with multi-source failover."""
import logging

import pandas as pd

from app.config import get_settings
from app.data_provider.base import BaseFetcher
from app.data_provider.akshare_fetcher import AKShareFetcher
from app.data_provider.tushare_fetcher import TushareFetcher
from app.data_provider.efinance_fetcher import EfinanceFetcher
from app.data_provider.realtime import get_tencent_quote, get_sina_quote
from app.data_provider.fundamental import get_fundamental

logger = logging.getLogger(__name__)

_instance: "DataFetcherManager | None" = None


class DataFetcherManager:
    """Singleton manager that routes data requests through prioritized fetchers."""

    def __init__(self):
        self._fetchers: dict[str, BaseFetcher] = {
            "akshare": AKShareFetcher(),
            "tushare": TushareFetcher(),
            "efinance": EfinanceFetcher(),
        }

    def _get_ordered_fetchers(self) -> list[BaseFetcher]:
        settings = get_settings()
        priority = settings.provider_priority_list
        ordered = []
        healthy = []
        degraded = []
        for name in priority:
            f = self._fetchers.get(name)
            if f:
                if f.is_degraded:
                    degraded.append(f)
                else:
                    healthy.append(f)
        ordered = healthy + degraded
        for name, f in self._fetchers.items():
            if f not in ordered:
                ordered.append(f)
        return ordered

    async def get_daily(self, code: str, days: int = 120) -> pd.DataFrame | None:
        for fetcher in self._get_ordered_fetchers():
            result = await fetcher.get_daily(code, days)
            if result is not None and not result.empty:
                logger.info("get_daily(%s) succeeded via %s", code, fetcher.name)
                return result
            logger.debug("get_daily(%s) failed via %s, trying next", code, fetcher.name)
        logger.error("get_daily(%s) failed on all providers", code)
        return None

    async def get_index_daily(self, code: str, days: int = 60) -> pd.DataFrame | None:
        for fetcher in self._get_ordered_fetchers():
            result = await fetcher.get_index_daily(code, days)
            if result is not None and not result.empty:
                return result
        return None

    async def get_realtime_quote(self, code: str) -> dict | None:
        quote = await get_tencent_quote(code)
        if quote:
            return quote
        quote = await get_sina_quote(code)
        if quote:
            return quote
        for fetcher in self._get_ordered_fetchers():
            quote = await fetcher.get_realtime_quote(code)
            if quote:
                return quote
        return None

    async def get_fundamental(self, code: str) -> dict | None:
        return await get_fundamental(code)


def get_data_manager() -> DataFetcherManager:
    global _instance
    if _instance is None:
        _instance = DataFetcherManager()
    return _instance
