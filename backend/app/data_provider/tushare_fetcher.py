"""Tushare data fetcher — secondary source, works with low credits (>=120)."""
import logging
from datetime import datetime, timedelta

import pandas as pd

from app.config import get_settings
from app.data_provider.base import BaseFetcher

logger = logging.getLogger(__name__)


class TushareFetcher(BaseFetcher):
    name = "tushare"

    def __init__(self):
        self._pro = None

    def _get_api(self):
        if self._pro is None:
            settings = get_settings()
            if not settings.tushare_token:
                return None
            import tushare as ts
            ts.set_token(settings.tushare_token)
            self._pro = ts.pro_api()
        return self._pro

    async def get_daily(self, code: str, days: int = 120) -> pd.DataFrame | None:
        try:
            pro = self._get_api()
            if pro is None:
                return None

            ts_code = code.strip().upper()
            if not (ts_code.endswith(".SZ") or ts_code.endswith(".SH")):
                if ts_code.startswith("6"):
                    ts_code = ts_code[:6] + ".SH"
                else:
                    ts_code = ts_code[:6] + ".SZ"

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

        except Exception as e:
            logger.warning("Tushare get_daily failed for %s: %s", code, e)
            self.record_failure()
            return None

    async def get_realtime_quote(self, code: str) -> dict | None:
        return None

    async def get_index_daily(self, code: str, days: int = 60) -> pd.DataFrame | None:
        try:
            pro = self._get_api()
            if pro is None:
                return None

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

        except Exception as e:
            logger.warning("Tushare get_index_daily failed for %s: %s", code, e)
            return None
