"""涨停板/连板梯队追踪 — 替代 Excel 截图。"""
import logging
from collections import defaultdict
from datetime import date

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
    import akshare as ak

    result = {
        "date": str(date.today()),
        "market_height": 0,
        "market_leader": None,
        "ladder": [],
        "first_board_count": 0,
        "broken_boards": [],
        "sector_distribution": {},
    }

    try:
        zt_df = ak.stock_zt_pool_em(date=date.today().strftime("%Y%m%d"))
    except Exception as e:
        logger.warning("stock_zt_pool_em failed: %s", e)
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

    try:
        broken_df = ak.stock_zt_pool_zbgc_em(date=date.today().strftime("%Y%m%d"))
        if broken_df is not None and not broken_df.empty:
            for _, row in broken_df.iterrows():
                result["broken_boards"].append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "change_pct": float(row.get("涨跌幅", 0) or 0),
                })
    except Exception as e:
        logger.debug("stock_zt_pool_zbgc_em failed: %s", e)

    return result
