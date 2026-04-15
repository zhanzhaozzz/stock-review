"""市场总览 — 大盘指数、涨跌面、板块排行、资金流向。

数据获取优先走 DataFetcherManager 统一入口，减少直连外部库。
仅 HSI 恒生指数、板块成分股、资金流向等无法走 Manager 的场景保留 akshare 直连。
"""
import logging
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

INDEX_LIST = [
    {"code": "000001.SH", "name": "上证指数"},
    {"code": "399001.SZ", "name": "深证成指"},
    {"code": "399006.SZ", "name": "创业板指"},
    {"code": "HSI", "name": "恒生指数"},
]


async def get_market_overview() -> dict:
    """获取大盘指数 + 涨跌面统计。"""
    indices = []
    for idx in INDEX_LIST:
        try:
            if idx["code"] == "HSI":
                quote = await _get_hsi_quote()
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
    """涨跌面统计 — 通过 DataFetcherManager 获取。"""
    from app.cache import cache_get, cache_set

    cached = await cache_get("sr:market:breadth")
    if cached:
        return cached

    breadth = {"up": 0, "down": 0, "flat": 0, "limit_up": 0, "limit_down": 0, "total": 0}
    try:
        from app.data_provider.manager import get_data_manager
        manager = get_data_manager()
        result = await manager.get_market_breadth()
        if result:
            breadth["up"] = result.get("up", 0)
            breadth["down"] = result.get("down", 0)
            breadth["flat"] = result.get("flat", 0)
            breadth["limit_up"] = result.get("limit_up", 0)
            breadth["limit_down"] = result.get("limit_down", 0)
            breadth["total"] = result.get("total", 0)
        await cache_set("sr:market:breadth", breadth, ttl=120)
    except Exception as e:
        logger.warning("Failed to get breadth: %s", e)

    return breadth


async def _get_index_quote(code: str) -> dict | None:
    from app.data_provider.realtime import get_tencent_quote
    return await get_tencent_quote(code)


async def _get_hsi_quote() -> dict | None:
    """获取恒生指数行情 — 优先腾讯接口，降级 akshare。"""
    try:
        from app.data_provider.realtime import get_tencent_quote
        quote = await get_tencent_quote("HSI")
        if quote:
            return quote
    except Exception as e:
        logger.debug("Tencent HSI quote failed: %s", e)

    try:
        import asyncio
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_hk_index_spot_em)
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
    except Exception as e:
        logger.warning("AKShare HSI quote failed: %s", e)
        return None


async def get_sector_ranking(sector_type: str = "concept", limit: int = 30) -> list[dict]:
    """板块排行 — 通过 DataFetcherManager 获取（akshare -> tushare fallback）。"""
    try:
        from app.data_provider.manager import get_data_manager
        manager = get_data_manager()
        result = await manager.get_sector_ranking(sector_type, limit)
        if result:
            return result
    except Exception as e:
        logger.warning("get_sector_ranking via manager failed: %s", e)

    return []


async def get_sector_constituents(board_name: str, limit: int = 30) -> list[dict]:
    """获取概念板块的成分股列表。"""
    import asyncio
    from app.cache import cache_get, cache_set

    cache_key = f"sr:sector:cons:{board_name}"
    cached = await cache_get(cache_key)
    if cached:
        return cached[:limit]

    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_board_concept_cons_em, symbol=board_name)
        if df is None or df.empty:
            return []

        col_map = {
            "代码": "code",
            "名称": "name",
            "最新价": "price",
            "涨跌幅": "change_pct",
            "成交量": "volume",
            "成交额": "amount",
            "换手率": "turnover_rate",
            "最高": "high",
            "最低": "low",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        result = []
        for _, row in df.iterrows():
            item = {
                "code": str(row.get("code", "")),
                "name": str(row.get("name", "")),
                "price": float(row.get("price", 0) or 0),
                "change_pct": float(row.get("change_pct", 0) or 0),
                "volume": float(row.get("volume", 0) or 0),
                "amount": float(row.get("amount", 0) or 0),
                "turnover_rate": float(row.get("turnover_rate", 0) or 0),
            }
            result.append(item)

        result.sort(key=lambda x: x["change_pct"], reverse=True)
        await cache_set(cache_key, result, ttl=300)
        return result[:limit]

    except Exception as e:
        logger.warning("get_sector_constituents(%s) failed: %s", board_name, e)
        return []


async def get_money_flow() -> list[dict]:
    """行业资金流向。"""
    import asyncio
    import akshare as ak
    try:
        df = await asyncio.to_thread(
            ak.stock_sector_fund_flow_rank, indicator="今日", sector_type="行业资金流"
        )
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


async def get_total_volume_with_delta(target_date: str = "today") -> dict:
    """获取沪深成交额与较上一交易日的增缩量 — 通过 DataFetcherManager 获取。"""
    try:
        from app.data_provider.manager import get_data_manager
        manager = get_data_manager()
        result = await manager.get_market_turnover(target_date)
        if result:
            delta = result.get("delta_amount_yi", 0.0)
            trend = "增量" if delta > 0 else "缩量" if delta < 0 else "平量"
            result["trend"] = trend
            return result
    except Exception as e:
        logger.warning("get_total_volume_with_delta via manager failed: %s", e)

    return {"total_volume": "", "total_amount_yi": 0.0, "delta_amount_yi": 0.0, "trend": "平量"}


async def get_daily_context(
    target_date: str = "today",
    limit_up_data_override: dict | None = None,
    market_overview_override: dict | None = None,
) -> dict:
    """装配复盘 LLM 所需的客观盘面上下文。"""
    from app.core.limit_up_tracker import get_limit_up_data

    limit_up_data = limit_up_data_override or await get_limit_up_data(target_date)
    market_overview = market_overview_override or await get_market_overview()
    sector_ranking = await get_sector_ranking("concept", 10)
    volume_info = await get_total_volume_with_delta(target_date)
    breadth = market_overview.get("breadth", {}) if isinstance(market_overview, dict) else {}
    ladder = limit_up_data.get("ladder", [])

    ladder_summary = ", ".join(
        f"{item.get('level', 0)}板{item.get('count', 0)}家"
        for item in sorted(ladder, key=lambda x: x.get("level", 0), reverse=True)
    )
    dragon = limit_up_data.get("market_leader") or {}
    sector_dist = limit_up_data.get("sector_distribution", {})
    main_sector_names = list(sector_dist.keys())[:3]
    sub_sector_names = list(sector_dist.keys())[3:6]

    return {
        "date": limit_up_data.get("date", str(_parse_trade_day(target_date))),
        "market_height": int(limit_up_data.get("market_height", 0) or 0),
        "dragon_stock": str(dragon.get("name", "") or ""),
        "core_middle_stock": "",
        "market_ladder": ladder_summary,
        "market_ladder_detail": ladder,
        "total_volume": volume_info.get("total_volume", ""),
        "limit_down_count": int(limit_up_data.get("limit_down_count", 0) or breadth.get("limit_down", 0) or 0),
        "promotion_rate": float(limit_up_data.get("promotion_rate", 0.0) or 0.0),
        "promotion_rate_text": limit_up_data.get("promotion_rate_text", ""),
        "main_sectors": ", ".join(main_sector_names),
        "sub_sectors": ", ".join(sub_sector_names),
        "market_overview": market_overview,
        "sector_ranking": sector_ranking,
        "limit_up_data": limit_up_data,
    }


def _parse_trade_day(target_date: str) -> date:
    if target_date and target_date != "today":
        try:
            dt = datetime.fromisoformat(target_date).date()
        except ValueError:
            dt = date.today()
    else:
        dt = date.today()
    while dt.weekday() >= 5:
        dt -= timedelta(days=1)
    return dt
