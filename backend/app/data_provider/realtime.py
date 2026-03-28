"""Realtime quote fetchers via Tencent and Sina HTTP APIs (no library dependency)."""
import logging
import re

import httpx

logger = logging.getLogger(__name__)


async def get_tencent_quote(code: str) -> dict | None:
    """Fetch realtime quote from Tencent finance API."""
    try:
        clean = code.split(".")[0].strip()
        if code.endswith(".SH") or clean.startswith("6"):
            tc_code = f"sh{clean}"
        elif code.endswith(".HK"):
            tc_code = f"hk{clean}"
        else:
            tc_code = f"sz{clean}"

        url = f"https://qt.gtimg.cn/q={tc_code}"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)

        text = resp.text
        parts = text.split("~")
        if len(parts) < 45:
            return None

        return {
            "code": code,
            "name": parts[1],
            "price": float(parts[3]),
            "change": float(parts[31]),
            "change_pct": float(parts[32]),
            "volume": float(parts[6]),
            "turnover": float(parts[37]) * 10000 if parts[37] else 0,
            "high": float(parts[33]),
            "low": float(parts[34]),
            "open": float(parts[5]),
            "prev_close": float(parts[4]),
        }
    except Exception as e:
        logger.debug("Tencent quote failed for %s: %s", code, e)
        return None


async def get_sina_quote(code: str) -> dict | None:
    """Fetch realtime quote from Sina finance API (A-shares only)."""
    try:
        clean = code.split(".")[0].strip()
        if code.endswith(".SH") or clean.startswith("6"):
            sina_code = f"sh{clean}"
        else:
            sina_code = f"sz{clean}"

        url = f"https://hq.sinajs.cn/list={sina_code}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url, headers=headers)

        match = re.search(r'"(.*)"', resp.text)
        if not match:
            return None

        parts = match.group(1).split(",")
        if len(parts) < 32:
            return None

        return {
            "code": code,
            "name": parts[0],
            "open": float(parts[1]),
            "prev_close": float(parts[2]),
            "price": float(parts[3]),
            "high": float(parts[4]),
            "low": float(parts[5]),
            "volume": float(parts[8]),
            "turnover": float(parts[9]),
            "change": float(parts[3]) - float(parts[2]),
            "change_pct": round((float(parts[3]) - float(parts[2])) / float(parts[2]) * 100, 2) if float(parts[2]) else 0,
        }
    except Exception as e:
        logger.debug("Sina quote failed for %s: %s", code, e)
        return None
