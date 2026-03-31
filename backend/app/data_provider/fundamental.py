"""Fundamental data fetcher via East Money / Tencent Finance / AKShare APIs.

扩展字段覆盖：核心估值、资金流明细、市场微观（量比/换手率/委比/振幅）。
多周期涨跌幅和连涨天数由 compute_price_derived 从 stock_prices 表计算。

数据源优先级：
  1. 东方财富 push2 API（交易时段字段最全，非交易时间可能不可用）
  2. 腾讯财经 qt API（7x24h 可用，覆盖 PE/PB/市值/换手率/振幅等核心字段）
"""
import logging
from datetime import date, timedelta

import httpx
import pandas as pd
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

EM_INDIVIDUAL_URL = "https://push2.eastmoney.com/api/qt/stock/get"

# 东方财富 push2 字段映射
# f9=PE(TTM), f23=PB(MRQ), f37=ROE, f34=EPS
# f116=总市值, f117=流通市值
# f62=主力净流入, f66=超大单净流入, f72=大单净流入, f78=中单净流入, f84=小单净流入
# f10=量比, f8=换手率, f31=委比, f22=振幅
EM_FIELDS = (
    "f8,f9,f10,f22,f23,f31,f34,f37,"
    "f62,f66,f72,f78,f84,"
    "f116,f117"
)

TENCENT_QT_URL = "https://qt.gtimg.cn/q="


async def get_fundamental(code: str) -> dict | None:
    """获取个股基本面 + 资金流 + 微观数据。

    先尝试东方财富 push2，失败则 fallback 到腾讯财经。
    """
    result = await _get_fundamental_em(code)
    if result:
        return result

    logger.info("EM push2 unavailable for %s, falling back to Tencent QT", code)
    return await _get_fundamental_tencent(code)


async def _get_fundamental_em(code: str) -> dict | None:
    """从东方财富 push2 API 获取个股基本面 + 资金流 + 微观数据。"""
    try:
        clean = code.split(".")[0].strip()
        market_id = "1" if code.endswith(".SH") or clean.startswith("6") else "0"
        secid = f"{market_id}.{clean}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(EM_INDIVIDUAL_URL, params={
                "secid": secid,
                "fields": EM_FIELDS,
                "ut": "fa5fd1943c7b386f172d6893dbbd1",
            })
            data = resp.json().get("data", {})

        if not data:
            return None

        main_inflow = _safe_float(data.get("f62"))
        large_inflow = _safe_float(data.get("f66"))
        mid_inflow = _safe_float(data.get("f78"))
        small_inflow = _safe_float(data.get("f84"))
        retail_inflow = None
        if mid_inflow is not None and small_inflow is not None:
            retail_inflow = mid_inflow + small_inflow

        result = {
            "code": code,
            "pe_ttm": _safe_float(data.get("f9")),
            "pb_mrq": _safe_float(data.get("f23")),
            "roe": _safe_float(data.get("f37")),
            "eps": _safe_float(data.get("f34")),
            "market_cap": _safe_float(data.get("f116")),
            "circulating_cap": _safe_float(data.get("f117")),
            "main_net_inflow": main_inflow,
            "retail_net_inflow": retail_inflow,
            "large_net_inflow": large_inflow,
            "vol_ratio": _safe_float(data.get("f10")),
            "turnover_ratio": _safe_float(data.get("f8")),
            "committee": _safe_float(data.get("f31")),
            "swing": _safe_float(data.get("f22")),
        }

        try:
            result["debt_ratio"] = await _fetch_debt_ratio(clean)
        except Exception:
            result["debt_ratio"] = None

        return result

    except Exception as e:
        logger.warning("EM get_fundamental failed for %s: %s", code, e)
        return None


async def _get_fundamental_tencent(code: str) -> dict | None:
    """从腾讯财经 qt API 获取基本面数据（7x24h 可用）。

    腾讯 qt 响应格式：v_sz300903="1~科蓝软件~300903~31.97~...";
    字段索引：[3]现价 [5]开盘 [33]最高 [34]最低 [38]换手率 [39]PE [43]振幅
               [44]流通市值 [45]总市值 [46]PB
    """
    try:
        clean = code.split(".")[0].strip()
        prefix = "sh" if clean.startswith("6") else "sz"
        symbol = f"{prefix}{clean}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{TENCENT_QT_URL}{symbol}",
                headers={"User-Agent": "Mozilla/5.0"},
            )

        parts = resp.text.split("~")
        if len(parts) < 50:
            return None

        result = {
            "code": code,
            "pe_ttm": _safe_float(parts[39]),
            "pb_mrq": _safe_float(parts[46]),
            "market_cap": _safe_float(parts[45]),
            "circulating_cap": _safe_float(parts[44]),
            "turnover_ratio": _safe_float(parts[38]),
            "swing": _safe_float(parts[43]),
            "roe": None,
            "eps": None,
            "debt_ratio": None,
            "main_net_inflow": None,
            "retail_net_inflow": None,
            "large_net_inflow": None,
            "vol_ratio": None,
            "committee": None,
        }
        return result

    except Exception as e:
        logger.warning("Tencent get_fundamental failed for %s: %s", code, e)
        return None


async def _fetch_debt_ratio(clean_code: str) -> float | None:
    """通过 akshare 获取资产负债率。"""
    try:
        import akshare as ak
        info_df = ak.stock_individual_info_em(symbol=clean_code)
        if info_df is not None and not info_df.empty:
            info_dict = dict(zip(info_df["item"], info_df["value"]))
            val = info_dict.get("资产负债率")
            return _safe_float(val)
    except Exception:
        pass
    return None


async def compute_price_derived(code: str, db: AsyncSession) -> dict:
    """从 stock_prices 表计算多周期涨跌幅和连涨/跌天数。

    Returns:
        dict with keys: chg_5d, chg_10d, chg_20d, chg_60d, chg_year, rise_day_count
    """
    from app.models.stock import StockPrice

    stmt = (
        select(StockPrice)
        .where(StockPrice.code == code)
        .order_by(desc(StockPrice.date))
        .limit(120)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return {}

    prices = list(reversed(rows))
    latest_close = prices[-1].close
    if latest_close is None:
        return {}

    derived: dict = {}

    for period, key in [(5, "chg_5d"), (10, "chg_10d"), (20, "chg_20d"), (60, "chg_60d")]:
        if len(prices) > period:
            base = prices[-(period + 1)].close
            if base and base > 0:
                derived[key] = round((latest_close - base) / base * 100, 2)

    # 年初至今
    year_start = date(date.today().year, 1, 1)
    year_prices = [p for p in prices if p.date >= year_start]
    if year_prices and year_prices[0].close and year_prices[0].close > 0:
        derived["chg_year"] = round(
            (latest_close - year_prices[0].close) / year_prices[0].close * 100, 2
        )

    # 连涨/跌天数
    derived["rise_day_count"] = _calc_consecutive_days(prices)

    return derived


def _calc_consecutive_days(prices: list) -> int:
    """计算最近连涨或连跌天数。正数=连涨，负数=连跌。"""
    if len(prices) < 2:
        return 0

    count = 0
    direction = None

    for i in range(len(prices) - 1, 0, -1):
        cur = prices[i].change_pct
        if cur is None:
            break
        if cur > 0:
            if direction is None:
                direction = 1
            if direction == 1:
                count += 1
            else:
                break
        elif cur < 0:
            if direction is None:
                direction = -1
            if direction == -1:
                count += 1
            else:
                break
        else:
            break

    return count * (direction or 1)


def _safe_float(val) -> float | None:
    if val is None or val == "-":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
