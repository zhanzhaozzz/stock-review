"""efinance data fetcher — fallback source."""
import logging
from datetime import datetime, timedelta

import pandas as pd

from app.data_provider.base import BaseFetcher

logger = logging.getLogger(__name__)


class EfinanceFetcher(BaseFetcher):
    name = "efinance"

    async def get_daily(self, code: str, days: int = 120) -> pd.DataFrame | None:
        try:
            import efinance as ef

            clean_code = code.split(".")[0].strip()
            df = ef.stock.get_quote_history(clean_code)

            if df is None or df.empty:
                self.record_failure()
                return None

            col_map = {"日期": "date", "开盘": "open", "最高": "high", "最低": "low",
                       "收盘": "close", "成交量": "volume", "成交额": "turnover", "涨跌幅": "change_pct"}
            df = df.rename(columns=col_map)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df = df.sort_values("date").tail(days).reset_index(drop=True)
            self.record_success()
            return df[["date", "open", "high", "low", "close", "volume", "turnover", "change_pct"]]

        except Exception as e:
            logger.warning("efinance get_daily failed for %s: %s", code, e)
            self.record_failure()
            return None

    async def get_realtime_quote(self, code: str) -> dict | None:
        try:
            import efinance as ef

            clean_code = code.split(".")[0].strip()
            df = ef.stock.get_realtime_quotes([clean_code])

            if df is None or df.empty:
                return None

            r = df.iloc[0]
            self.record_success()
            return {
                "code": code,
                "name": r.get("股票名称", ""),
                "price": float(r.get("最新价", 0) or 0),
                "change": float(r.get("涨跌额", 0) or 0),
                "change_pct": float(r.get("涨跌幅", 0) or 0),
                "volume": float(r.get("成交量", 0) or 0),
                "turnover": float(r.get("成交额", 0) or 0),
            }
        except Exception as e:
            logger.warning("efinance get_realtime_quote failed for %s: %s", code, e)
            self.record_failure()
            return None
