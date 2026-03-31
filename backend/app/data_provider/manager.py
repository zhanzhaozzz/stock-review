"""DataFetcherManager — unified data access with multi-source failover."""
import logging
from datetime import datetime, timedelta

import httpx
import pandas as pd

from app.config import get_settings
from app.data_provider.base import BaseFetcher
from app.data_provider.akshare_fetcher import AKShareFetcher
from app.data_provider.tushare_fetcher import TushareFetcher
from app.data_provider.efinance_fetcher import EfinanceFetcher
from app.data_provider.realtime import get_tencent_quote, get_sina_quote
from app.data_provider.fundamental import get_fundamental

logger = logging.getLogger(__name__)

TENCENT_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

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

        result = await _fetch_daily_tencent(code, days)
        if result is not None and not result.empty:
            logger.info("get_daily(%s) succeeded via tencent_kline", code)
            return result

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


async def _fetch_daily_tencent(code: str, days: int = 120) -> pd.DataFrame | None:
    """腾讯财经前复权日 K 线（7x24h 可用），作为最终 fallback。"""
    try:
        clean = code.split(".")[0].strip()
        prefix = "sh" if clean.startswith("6") else "sz"
        symbol = f"{prefix}{clean}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                TENCENT_KLINE_URL,
                params={"param": f"{symbol},day,,,{days},qfq"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            data = resp.json().get("data", {}).get(symbol, {})

        klines = data.get("qfqday") or data.get("day", [])
        if not klines:
            return None

        records = []
        prev_close = None
        for k in klines:
            dt = datetime.strptime(k[0], "%Y-%m-%d").date()
            o, c, h, l, vol = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
            chg = round((c - prev_close) / prev_close * 100, 2) if prev_close and prev_close > 0 else 0
            records.append({
                "date": dt, "open": o, "high": h, "low": l,
                "close": c, "volume": vol, "turnover": None, "change_pct": chg,
            })
            prev_close = c

        return pd.DataFrame(records).tail(days).reset_index(drop=True)

    except Exception as e:
        logger.warning("Tencent kline fetch failed for %s: %s", code, e)
        return None


def get_data_manager() -> DataFetcherManager:
    global _instance
    if _instance is None:
        _instance = DataFetcherManager()
    return _instance
