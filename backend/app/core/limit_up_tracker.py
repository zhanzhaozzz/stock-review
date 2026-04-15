"""涨停板/连板梯队追踪 — 替代 Excel 截图。

数据获取全部走 DataFetcherManager，不再直连 akshare。
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)


async def get_limit_up_data(target_date: str = "today") -> dict:
    """获取涨停板/连板梯队结构化数据。

    Returns:
        {
            "date": "2026-03-27",
            "market_height": 8,
            "market_leader": {"code": "...", "name": "...", "board_count": 8, "sector": "..."},
            "ladder": [{"level": N, "stocks": [...]}],
            "first_board_count": 67,
            "broken_boards": [...],
            "sector_distribution": {"板块名": 数量}
        }
    """
    from app.data_provider.manager import get_data_manager
    manager = get_data_manager()

    trade_day = _parse_trade_day(target_date)
    trade_day_str = str(trade_day)
    result = {
        "date": trade_day_str,
        "market_height": 0,
        "market_leader": None,
        "ladder": [],
        "first_board_count": 0,
        "broken_boards": [],
        "sector_distribution": {},
        "limit_down_count": 0,
        "promotion_rate": 0.0,
        "promotion_rate_text": "",
    }

    try:
        zt_df = await manager.get_limit_up_pool(trade_day_str)
    except Exception as e:
        logger.warning("get_limit_up_pool failed: %s", e)
        zt_df = None

    if zt_df is None or zt_df.empty:
        return result

    col_map = {
        "代码": "code", "名称": "name", "涨跌幅": "change_pct",
        "成交额": "turnover", "流通市值": "circulating_cap",
        "连板数": "board_count", "所属行业": "sector",
        "首次封板时间": "first_lock_time",
    }
    zt_df = zt_df.rename(columns={k: v for k, v in col_map.items() if k in zt_df.columns})

    if "board_count" not in zt_df.columns:
        zt_df["board_count"] = 1

    zt_df["board_count"] = zt_df["board_count"].fillna(1).astype(int)

    max_board = int(zt_df["board_count"].max())
    result["market_height"] = max_board

    leader_row = zt_df[zt_df["board_count"] == max_board].iloc[0]
    result["market_leader"] = {
        "code": str(leader_row.get("code", "")),
        "name": str(leader_row.get("name", "")),
        "board_count": max_board,
        "sector": str(leader_row.get("sector", "")),
    }

    ladder_groups = defaultdict(list)
    sector_counter = defaultdict(int)

    for _, row in zt_df.iterrows():
        bc = int(row.get("board_count", 1))
        stock_info = {
            "code": str(row.get("code", "")),
            "name": str(row.get("name", "")),
            "board_count": bc,
            "change_pct": float(row.get("change_pct", 0) or 0),
            "turnover": float(row.get("turnover", 0) or 0),
            "sector": str(row.get("sector", "")),
        }
        ladder_groups[bc].append(stock_info)

        sector = str(row.get("sector", ""))
        if sector:
            sector_counter[sector] += 1

    ladder = []
    for level in sorted(ladder_groups.keys(), reverse=True):
        stocks = ladder_groups[level]
        if level == 1:
            result["first_board_count"] = len(stocks)
            ladder.append({
                "level": level,
                "count": len(stocks),
                "stocks": sorted(stocks, key=lambda x: x["turnover"], reverse=True)[:10],
            })
        else:
            ladder.append({
                "level": level,
                "count": len(stocks),
                "stocks": stocks,
            })

    result["ladder"] = ladder
    result["sector_distribution"] = dict(sorted(sector_counter.items(), key=lambda x: x[1], reverse=True)[:15])
    result["limit_down_count"] = await _get_limit_down_count(manager, trade_day)
    result["promotion_rate"], result["promotion_rate_text"] = await _get_promotion_rate(manager, trade_day, zt_df)

    try:
        broken_df = await manager.get_broken_board_pool(trade_day_str)
        if broken_df is not None and not broken_df.empty:
            for _, row in broken_df.iterrows():
                result["broken_boards"].append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                })
    except Exception as e:
        logger.debug("get_broken_board_pool failed: %s", e)

    return result


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


async def _get_limit_down_count(manager, trade_day: date) -> int:
    try:
        dt_df = await manager.get_limit_down_pool(str(trade_day))
        if dt_df is not None and not dt_df.empty:
            return len(dt_df)
    except Exception as e:
        logger.debug("get_limit_down_pool failed: %s", e)

    try:
        breadth = await manager.get_market_breadth()
        if breadth:
            return 0
    except Exception:
        pass

    return 0


async def _get_promotion_rate(manager, trade_day: date, today_zt_df) -> tuple[float, str]:
    yesterday = trade_day - timedelta(days=1)
    while yesterday.weekday() >= 5:
        yesterday -= timedelta(days=1)

    try:
        y_df = await manager.get_limit_up_pool(str(yesterday))
    except Exception as e:
        logger.debug("get_limit_up_pool yesterday failed: %s", e)
        return 0.0, ""

    if y_df is None or y_df.empty or today_zt_df is None or today_zt_df.empty:
        return 0.0, ""

    y_col_map = {"代码": "code", "连板数": "board_count"}
    t_col_map = {"代码": "code", "连板数": "board_count"}
    y_df = y_df.rename(columns={k: v for k, v in y_col_map.items() if k in y_df.columns})
    t_df = today_zt_df.rename(columns={k: v for k, v in t_col_map.items() if k in today_zt_df.columns})

    if "code" not in y_df.columns or "code" not in t_df.columns:
        return 0.0, ""

    if "board_count" not in y_df.columns:
        y_df["board_count"] = 1
    if "board_count" not in t_df.columns:
        t_df["board_count"] = 1

    y_df["board_count"] = y_df["board_count"].fillna(1).astype(int)
    t_df["board_count"] = t_df["board_count"].fillna(1).astype(int)
    y_df["code"] = y_df["code"].astype(str)
    t_df["code"] = t_df["code"].astype(str)

    yesterday_lianban = y_df[y_df["board_count"] >= 2]
    if yesterday_lianban.empty:
        return 0.0, ""

    today_map = {row["code"]: int(row["board_count"]) for _, row in t_df.iterrows()}
    total = len(yesterday_lianban)
    success = 0
    for _, row in yesterday_lianban.iterrows():
        code = row["code"]
        y_bc = int(row["board_count"])
        t_bc = today_map.get(code, 0)
        if t_bc > y_bc:
            success += 1

    rate = round((success / total) * 100, 2) if total > 0 else 0.0
    return rate, f"{rate:.2f}% ({success}/{total})"
