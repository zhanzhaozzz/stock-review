"""Fundamental data fetcher via East Money / AKShare APIs."""
import logging

import httpx

logger = logging.getLogger(__name__)

EM_INDIVIDUAL_URL = "https://push2.eastmoney.com/api/qt/stock/get"


async def get_fundamental(code: str) -> dict | None:
    """Fetch fundamental data for a stock (PE, PB, ROE, market cap, net flow etc.)."""
    try:
        import akshare as ak

        clean = code.split(".")[0].strip()
        market_id = "1" if code.endswith(".SH") or clean.startswith("6") else "0"
        secid = f"{market_id}.{clean}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(EM_INDIVIDUAL_URL, params={
                "secid": secid,
                "fields": "f9,f23,f37,f116,f117,f62,f184,f164,f130",
                "ut": "fa5fd1943c7b386f172d6893dbbd1",
            })
            data = resp.json().get("data", {})

        result = {
            "code": code,
            "pe": _safe_float(data.get("f9")),
            "pb": _safe_float(data.get("f23")),
            "roe": _safe_float(data.get("f37")),
            "market_cap": _safe_float(data.get("f116")),
            "circulating_cap": _safe_float(data.get("f117")),
            "net_flow": _safe_float(data.get("f62")),
        }

        try:
            info_df = ak.stock_individual_info_em(symbol=clean)
            if info_df is not None and not info_df.empty:
                info_dict = dict(zip(info_df["item"], info_df["value"]))
                result["industry"] = info_dict.get("行业", "")
                result["total_shares"] = _safe_float(info_dict.get("总股本"))
        except Exception:
            pass

        return result

    except Exception as e:
        logger.warning("get_fundamental failed for %s: %s", code, e)
        return None


def _safe_float(val) -> float | None:
    if val is None or val == "-":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
