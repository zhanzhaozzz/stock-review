"""Tushare data fetcher — secondary source, works with low credits (>=120).

流控策略（参考 daily_stock_analysis）：
1. 每分钟调用计数器，超过 80 次强制休眠到下一分钟
2. tenacity 指数退避重试（网络/超时错误）
3. 实时行情支持 Pro API + 旧版 SDK 双通道
"""
import logging
import time
import threading
from datetime import datetime, timedelta

import pandas as pd
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings
from app.data_provider.base import BaseFetcher

logger = logging.getLogger(__name__)


class TushareFetcher(BaseFetcher):
    name = "tushare"

    MAX_CALLS_PER_MINUTE = 80
    _call_count = 0
    _minute_start = 0.0
    _rate_lock = threading.Lock()

    def __init__(self):
        self._pro = None
        self._ts_module = None

    def _get_api(self):
        if self._pro is None:
            settings = get_settings()
            if not settings.tushare_token:
                return None
            import tushare as ts
            ts.set_token(settings.tushare_token)
            self._pro = ts.pro_api()
            self._ts_module = ts
        return self._pro

    def _check_rate_limit(self):
        with self._rate_lock:
            now = time.time()
            if now - self._minute_start >= 60:
                self._call_count = 0
                self._minute_start = now
            self._call_count += 1
            if self._call_count > self.MAX_CALLS_PER_MINUTE:
                sleep_time = 61 - (now - self._minute_start)
                logger.info("Tushare rate limit reached (%d/%d), sleeping %.1fs",
                            self._call_count, self.MAX_CALLS_PER_MINUTE, sleep_time)
                time.sleep(max(sleep_time, 1))
                self._call_count = 1
                self._minute_start = time.time()

    def _to_ts_code(self, code: str) -> str:
        ts_code = code.strip().upper()
        if not (ts_code.endswith(".SZ") or ts_code.endswith(".SH")):
            if ts_code.startswith("6"):
                ts_code = ts_code[:6] + ".SH"
            else:
                ts_code = ts_code[:6] + ".SZ"
        return ts_code

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    async def get_daily(self, code: str, days: int = 120) -> pd.DataFrame | None:
        try:
            pro = self._get_api()
            if pro is None:
                return None

            self._check_rate_limit()
            ts_code = self._to_ts_code(code)

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                self.record_failure()
                return None

            df = df.rename(columns={
                "trade_date": "date", "vol": "volume",
                "amount": "turnover", "pct_chg": "change_pct",
            })
            df["date"] = pd.to_datetime(df["date"]).dt.date
            if "turnover" in df.columns:
                df["turnover"] = df["turnover"] * 1000

            df = df.sort_values("date").tail(days).reset_index(drop=True)
            self.record_success()
            return df[["date", "open", "high", "low", "close", "volume", "turnover", "change_pct"]]

        except (ConnectionError, TimeoutError, OSError):
            raise
        except Exception as e:
            logger.warning("Tushare get_daily failed for %s: %s", code, e)
            self.record_failure()
            return None

    async def get_realtime_quote(self, code: str) -> dict | None:
        """实时行情：先尝试旧版 SDK get_realtime_quotes，失败返回 None。"""
        try:
            if self._get_api() is None:
                return None

            ts = self._ts_module
            if ts is None:
                return None

            self._check_rate_limit()
            raw_code = code.strip().split(".")[0][:6]
            df = ts.get_realtime_quotes(raw_code)
            if df is None or df.empty:
                return None

            row = df.iloc[0]
            price = float(row.get("price", 0) or 0)
            pre_close = float(row.get("pre_close", 0) or 0)
            if price <= 0:
                return None

            change = price - pre_close if pre_close > 0 else 0
            change_pct = (change / pre_close * 100) if pre_close > 0 else 0

            self.record_success()
            return {
                "code": raw_code,
                "name": str(row.get("name", "")),
                "price": price,
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "volume": float(row.get("volume", 0) or 0),
                "amount": float(row.get("amount", 0) or 0),
                "high": float(row.get("high", 0) or 0),
                "low": float(row.get("low", 0) or 0),
                "open": float(row.get("open", 0) or 0),
                "source": "tushare",
            }
        except Exception as e:
            logger.debug("Tushare get_realtime_quote failed for %s: %s", code, e)
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    async def get_index_daily(self, code: str, days: int = 60) -> pd.DataFrame | None:
        try:
            pro = self._get_api()
            if pro is None:
                return None

            self._check_rate_limit()

            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            df = pro.index_daily(ts_code=code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return None

            df = df.rename(columns={
                "trade_date": "date", "vol": "volume",
                "amount": "turnover", "pct_chg": "change_pct",
            })
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df = df.sort_values("date").tail(days).reset_index(drop=True)
            self.record_success()
            return df[["date", "open", "high", "low", "close", "volume", "turnover", "change_pct"]]

        except (ConnectionError, TimeoutError, OSError):
            raise
        except Exception as e:
            logger.warning("Tushare get_index_daily failed for %s: %s", code, e)
            return None

    async def get_limit_up_pool(self, trade_date: str = "") -> pd.DataFrame | None:
        """通过 Tushare limit_list 获取涨停池（作为 AKShare 的 fallback）。"""
        try:
            pro = self._get_api()
            if pro is None:
                return None

            self._check_rate_limit()
            if not trade_date:
                trade_date = datetime.now().strftime("%Y%m%d")
            else:
                trade_date = trade_date.replace("-", "")

            df = pro.limit_list_d(trade_date=trade_date, limit_type="U")
            if df is None or df.empty:
                return None

            self.record_success()
            return df
        except Exception as e:
            logger.debug("Tushare get_limit_up_pool failed: %s", e)
            return None

    async def get_sector_ranking(self, sector_type: str = "concept", limit: int = 30) -> list[dict]:
        """通过 Tushare ths_daily 获取板块排行（作为 AKShare 的 fallback）。"""
        try:
            pro = self._get_api()
            if pro is None:
                return []

            self._check_rate_limit()
            trade_date = datetime.now().strftime("%Y%m%d")

            exchange = "N" if sector_type == "concept" else "A"
            df = pro.ths_daily(trade_date=trade_date, exchange=exchange)
            if df is None or df.empty:
                return []

            df = df.sort_values("pct_change", ascending=False).head(limit)
            result = []
            for _, row in df.iterrows():
                result.append({
                    "name": row.get("name", ""),
                    "code": row.get("ts_code", ""),
                    "change_pct": float(row.get("pct_change", 0) or 0),
                    "source": "tushare",
                })

            self.record_success()
            return result
        except Exception as e:
            logger.debug("Tushare get_sector_ranking failed: %s", e)
            return []
