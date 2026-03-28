"""市场总览 — 大盘指数、涨跌面、板块排行、资金流向。"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

INDEX_LIST = [
    {"code": "000001.SH", "name": "上证指数"},
    {"code": "399001.SZ", "name": "深证成指"},
    {"code": "399006.SZ", "name": "创业板指"},
    {"code": "HSI", "name": "恒生指数"},
]


async def get_market_overview() -> dict:
    """获取大盘指数 + 涨跌面统计。

    涨跌面通过 AKShare 获取（较慢），所以分两步：先返回指数，涨跌面单独缓存/异步。
    """
    indices = []
    for idx in INDEX_LIST:
        try:
            if idx["code"] == "HSI":
                quote = _get_hsi_quote()
            else:
                quote = await _get_index_quote(idx["code"])
            if quote:
                quote["name"] = idx["name"]
                indices.append(quote)
        except Exception as e:
            logger.warning("Failed to get index %s: %s", idx["code"], e)

    breadth = await get_market_breadth()

    return {
        "indices": indices,
        "breadth": breadth,
        "timestamp": datetime.now().isoformat(),
    }


async def get_market_breadth() -> dict:
    """涨跌面统计 — 独立函数，方便单独缓存。"""
    from app.cache import cache_get, cache_set

    cached = await cache_get("sr:market:breadth")
    if cached:
        return cached

    breadth = {"up": 0, "down": 0, "flat": 0, "limit_up": 0, "limit_down": 0, "total": 0}
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            pct = df["涨跌幅"]
            breadth["up"] = int((pct > 0).sum())
            breadth["down"] = int((pct < 0).sum())
            breadth["flat"] = int((pct == 0).sum())
            breadth["limit_up"] = int((pct >= 9.9).sum())
            breadth["limit_down"] = int((pct <= -9.9).sum())
            breadth["total"] = len(df)
        await cache_set("sr:market:breadth", breadth, ttl=120)
    except Exception as e:
        logger.warning("Failed to get breadth: %s", e)

    return breadth


async def _get_index_quote(code: str) -> dict | None:
    from app.data_provider.realtime import get_tencent_quote
    return await get_tencent_quote(code)


def _get_hsi_quote() -> dict | None:
    try:
        import akshare as ak
        df = ak.stock_hk_index_spot_em()
        if df is None or df.empty:
            return None
        row = df[df["代码"] == "HSI"]
        if row.empty:
            return None
        r = row.iloc[0]
        return {
            "code": "HSI",
            "price": float(r.get("最新价", 0)),
            "change": float(r.get("涨跌额", 0)),
            "change_pct": float(r.get("涨跌幅", 0)),
        }
    except Exception:
        return None


async def get_sector_ranking(sector_type: str = "concept", limit: int = 30) -> list[dict]:
    """板块排行 — 概念/行业 + 资金流向。"""
    import akshare as ak
    try:
        if sector_type == "industry":
            df = ak.stock_board_industry_name_em()
        else:
            df = ak.stock_board_concept_name_em()

        if df is None or df.empty:
            return []

        col_map = {
            "板块名称": "name", "板块代码": "code",
            "最新价": "price", "涨跌幅": "change_pct",
            "总市值": "market_cap", "换手率": "turnover_rate",
            "上涨家数": "up_count", "下跌家数": "down_count",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        result = []
        for _, row in df.head(limit).iterrows():
            item = {
                "name": row.get("name", ""),
                "change_pct": float(row.get("change_pct", 0) or 0),
                "up_count": int(row.get("up_count", 0) or 0),
                "down_count": int(row.get("down_count", 0) or 0),
            }
            result.append(item)

        return sorted(result, key=lambda x: x["change_pct"], reverse=True)

    except Exception as e:
        logger.warning("get_sector_ranking failed: %s", e)
        return []


async def get_money_flow() -> list[dict]:
    """行业资金流向。"""
    import akshare as ak
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
        if df is None or df.empty:
            return []

        result = []
        for _, row in df.head(20).iterrows():
            result.append({
                "name": row.get("名称", ""),
                "change_pct": float(row.get("今日涨跌幅", 0) or 0),
                "net_flow": float(row.get("今日主力净流入-净额", 0) or 0),
                "net_flow_pct": float(row.get("今日主力净流入-净占比", 0) or 0),
            })
        return result

    except Exception as e:
        logger.warning("get_money_flow failed: %s", e)
        return []
