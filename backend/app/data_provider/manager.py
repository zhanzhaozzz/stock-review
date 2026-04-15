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
from app.data_provider.circuit_breaker import realtime_breaker, market_data_breaker

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
        sources = [
            ("tencent", lambda: get_tencent_quote(code)),
            ("sina", lambda: get_sina_quote(code)),
        ]
        for name, fn in sources:
            if not realtime_breaker.allow_request(name):
                continue
            try:
                quote = await fn()
                if quote:
                    realtime_breaker.record_success(name)
                    return quote
            except Exception as e:
                realtime_breaker.record_failure(name, str(e))

        for fetcher in self._get_ordered_fetchers():
            src = f"fetcher_{fetcher.name}"
            if not realtime_breaker.allow_request(src):
                continue
            try:
                quote = await fetcher.get_realtime_quote(code)
                if quote:
                    realtime_breaker.record_success(src)
                    return quote
            except Exception as e:
                realtime_breaker.record_failure(src, str(e))
        return None

    async def get_fundamental(self, code: str) -> dict | None:
        return await get_fundamental(code)

    async def get_limit_up_pool(self, trade_date: str = "today") -> pd.DataFrame | None:
        """涨停池：akshare -> tushare fallback。"""
        ak_fetcher: AKShareFetcher = self._fetchers.get("akshare")
        ts_fetcher: TushareFetcher = self._fetchers.get("tushare")

        if ak_fetcher and market_data_breaker.allow_request("akshare_limit_up"):
            try:
                result = await ak_fetcher.get_limit_up_pool(trade_date)
                if result is not None and not result.empty:
                    market_data_breaker.record_success("akshare_limit_up")
                    return result
            except Exception as e:
                market_data_breaker.record_failure("akshare_limit_up", str(e))

        if ts_fetcher and market_data_breaker.allow_request("tushare_limit_up"):
            try:
                result = await ts_fetcher.get_limit_up_pool(trade_date)
                if result is not None and not result.empty:
                    market_data_breaker.record_success("tushare_limit_up")
                    return result
            except Exception as e:
                market_data_breaker.record_failure("tushare_limit_up", str(e))

        logger.warning("get_limit_up_pool failed on all providers")
        return None

    async def get_broken_board_pool(self, trade_date: str = "today") -> pd.DataFrame | None:
        """炸板池：akshare。"""
        ak_fetcher: AKShareFetcher = self._fetchers.get("akshare")
        if ak_fetcher:
            try:
                return await ak_fetcher.get_broken_board_pool(trade_date)
            except Exception as e:
                logger.debug("get_broken_board_pool failed: %s", e)
        return None

    async def get_limit_down_pool(self, trade_date: str = "today") -> pd.DataFrame | None:
        """跌停池：akshare。"""
        ak_fetcher: AKShareFetcher = self._fetchers.get("akshare")
        if ak_fetcher:
            try:
                return await ak_fetcher.get_limit_down_pool(trade_date)
            except Exception as e:
                logger.debug("get_limit_down_pool failed: %s", e)
        return None

    async def get_market_turnover(self, trade_date: str = "today") -> dict | None:
        """成交额：akshare -> tushare fallback。"""
        ak_fetcher: AKShareFetcher = self._fetchers.get("akshare")
        if ak_fetcher:
            try:
                result = await ak_fetcher.get_market_turnover(trade_date)
                if result:
                    return result
            except Exception as e:
                logger.debug("akshare get_market_turnover failed: %s", e)
        return None

    async def get_sector_ranking(self, sector_type: str = "concept", limit: int = 30) -> list[dict]:
        """板块排行：akshare -> tushare fallback。"""
        ak_fetcher: AKShareFetcher = self._fetchers.get("akshare")
        ts_fetcher: TushareFetcher = self._fetchers.get("tushare")

        if ak_fetcher:
            try:
                result = await ak_fetcher.get_sector_ranking(sector_type, limit)
                if result:
                    return result
            except Exception as e:
                logger.debug("akshare get_sector_ranking failed: %s", e)

        if ts_fetcher:
            try:
                result = await ts_fetcher.get_sector_ranking(sector_type, limit)
                if result:
                    return result
            except Exception as e:
                logger.debug("tushare get_sector_ranking failed: %s", e)

        return []

    async def get_market_breadth(self) -> dict | None:
        """涨跌面统计：akshare。"""
        ak_fetcher: AKShareFetcher = self._fetchers.get("akshare")
        if ak_fetcher:
            try:
                return await ak_fetcher.get_market_breadth()
            except Exception as e:
                logger.debug("get_market_breadth failed: %s", e)
        return None


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
