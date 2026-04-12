"""AKShare data fetcher — primary data source for A-shares and HK stocks."""
import logging
from datetime import datetime, timedelta

import pandas as pd

from app.data_provider.base import BaseFetcher

logger = logging.getLogger(__name__)


def _normalize_code(code: str) -> tuple[str, str]:
    """Normalize stock code and detect market.

    Returns (clean_code, market) where clean_code is without suffix.
    """
    code = code.strip().upper()
    if code.endswith(".SZ") or code.endswith(".SH"):
        return code[:6], "A"
    if code.endswith(".HK"):
        return code.replace(".HK", ""), "HK"
    if code.startswith("6"):
        return code[:6], "A"
    if code.startswith(("0", "3")):
        return code[:6], "A"
    return code, "A"


class AKShareFetcher(BaseFetcher):
    name = "akshare"

    async def get_daily(self, code: str, days: int = 120) -> pd.DataFrame | None:
        try:
            import akshare as ak
            clean_code, market = _normalize_code(code)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            if market == "HK":
                df = ak.stock_hk_hist(symbol=clean_code, period="daily",
                                      start_date=start_date, end_date=end_date, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=clean_code, period="daily",
                                        start_date=start_date, end_date=end_date, adjust="qfq")

            if df is None or df.empty:
                self.record_failure()
                return None

            col_map = {"日期": "date", "开盘": "open", "最高": "high", "最低": "low",
                       "收盘": "close", "成交量": "volume", "成交额": "turnover", "涨跌幅": "change_pct"}
            df = df.rename(columns=col_map)

            required = ["date", "open", "high", "low", "close"]
            if not all(c in df.columns for c in required):
                self.record_failure()
                return None

            df["date"] = pd.to_datetime(df["date"]).dt.date
            df = df.sort_values("date").tail(days).reset_index(drop=True)
            self.record_success()
            return df[["date", "open", "high", "low", "close", "volume", "turnover", "change_pct"]]

        except Exception as e:
            logger.warning("AKShare get_daily failed for %s: %s", code, e)
            self.record_failure()
            return None

    async def get_realtime_quote(self, code: str) -> dict | None:
        try:
            import akshare as ak
            clean_code, market = _normalize_code(code)

            if market == "HK":
                df = ak.stock_hk_spot_em()
                row = df[df["代码"] == clean_code]
            else:
                df = ak.stock_zh_a_spot_em()
                row = df[df["代码"] == clean_code]

            if row.empty:
                return None

            r = row.iloc[0]
            self.record_success()
            return {
                "code": code,
                "name": r.get("名称", ""),
                "price": float(r.get("最新价", 0)),
                "change": float(r.get("涨跌额", 0)),
                "change_pct": float(r.get("涨跌幅", 0)),
                "volume": float(r.get("成交量", 0)),
                "turnover": float(r.get("成交额", 0)),
                "high": float(r.get("最高", 0)),
                "low": float(r.get("最低", 0)),
                "open": float(r.get("今开", 0)),
                "prev_close": float(r.get("昨收", 0)),
            }
        except Exception as e:
            logger.warning("AKShare get_realtime_quote failed for %s: %s", code, e)
            self.record_failure()
            return None

    async def get_index_daily(self, code: str, days: int = 60) -> pd.DataFrame | None:
        try:
            import akshare as ak

            index_map = {
                "000001.SH": "000001", "399001.SZ": "399001",
                "399006.SZ": "399006", "000688.SH": "000688",
            }
            symbol = index_map.get(code, code.split(".")[0])
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")

            df = ak.index_zh_a_hist(symbol=symbol, period="daily",
                                    start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return None

            col_map = {"日期": "date", "开盘": "open", "最高": "high", "最低": "low",
                       "收盘": "close", "成交量": "volume", "成交额": "turnover", "涨跌幅": "change_pct"}
            df = df.rename(columns=col_map)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            df = df.sort_values("date").tail(days).reset_index(drop=True)
            self.record_success()
            return df[["date", "open", "high", "low", "close", "volume", "turnover", "change_pct"]]

        except Exception as e:
            logger.warning("AKShare get_index_daily failed for %s: %s", code, e)
            return None

    async def get_market_turnover(self, trade_date: str = "today") -> dict | None:
        """获取沪深成交额及与上一交易日的增缩量。"""
        try:
            import akshare as ak

            target = datetime.now().date()
            if trade_date and trade_date != "today":
                try:
                    target = datetime.fromisoformat(trade_date).date()
                except ValueError:
                    target = datetime.now().date()

            start_date = (target - timedelta(days=15)).strftime("%Y%m%d")
            end_date = target.strftime("%Y%m%d")
            sh_df = ak.index_zh_a_hist(symbol="000001", period="daily", start_date=start_date, end_date=end_date)
            sz_df = ak.index_zh_a_hist(symbol="399001", period="daily", start_date=start_date, end_date=end_date)
            if sh_df is None or sh_df.empty or sz_df is None or sz_df.empty:
                return None

            sh_amounts = sh_df["成交额"].dropna().tolist()
            sz_amounts = sz_df["成交额"].dropna().tolist()
            if len(sh_amounts) < 2 or len(sz_amounts) < 2:
                return None

            today_yi = _to_yi(sh_amounts[-1]) + _to_yi(sz_amounts[-1])
            prev_yi = _to_yi(sh_amounts[-2]) + _to_yi(sz_amounts[-2])
            delta_yi = today_yi - prev_yi
            sign = "+" if delta_yi >= 0 else ""
            self.record_success()
            return {
                "total_volume": f"{today_yi:.0f}亿 {sign}{delta_yi:.0f}亿",
                "total_amount_yi": round(today_yi, 2),
                "delta_amount_yi": round(delta_yi, 2),
            }
        except Exception as e:
            logger.warning("AKShare get_market_turnover failed: %s", e)
            self.record_failure()
            return None

    async def get_limit_up_pool(self, trade_date: str = "today") -> pd.DataFrame | None:
        """获取指定日期涨停池。"""
        try:
            import akshare as ak

            target = datetime.now().date()
            if trade_date and trade_date != "today":
                try:
                    target = datetime.fromisoformat(trade_date).date()
                except ValueError:
                    target = datetime.now().date()
            df = ak.stock_zt_pool_em(date=target.strftime("%Y%m%d"))
            if df is None or df.empty:
                self.record_failure()
                return None
            self.record_success()
            return df
        except Exception as e:
            logger.warning("AKShare get_limit_up_pool failed: %s", e)
            self.record_failure()
            return None


def _to_yi(amount: float) -> float:
    amount = float(amount or 0)
    if abs(amount) >= 1_000_000:
        return amount / 100_000_000
    return amount
