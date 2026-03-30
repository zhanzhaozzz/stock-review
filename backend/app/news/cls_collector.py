"""财联社 7x24 快讯采集器。"""
import logging
from datetime import datetime

import httpx

from app.news.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)

CLS_TELEGRAPH_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
CLS_FLASH_URL = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"


class CLSCollector(BaseCollector):
    name = "cls"

    async def fetch_latest(self, limit: int = 30) -> list[NewsItem]:
        """获取财联社 7x24 快讯。"""
        items = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://www.cls.cn/nodeapi/updateTelegraph",
                    params={"app": "CailianpressWeb", "os": "web", "sv": "7.7.5", "rn": str(limit)},
                    headers={"Referer": "https://www.cls.cn/telegraph"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    rolls = data.get("data", {}).get("roll_data", [])
                    for r in rolls:
                        title = r.get("title") or r.get("brief", "")
                        content = r.get("content", "")
                        if not title and content:
                            title = content[:80]
                        if not title:
                            continue
                        ts = r.get("ctime")
                        pub_time = datetime.fromtimestamp(ts) if ts else None
                        items.append(NewsItem(
                            title=title,
                            url=f"https://www.cls.cn/detail/{r.get('id', '')}",
                            source="财联社",
                            summary=content[:200] if content else "",
                            publish_time=pub_time,
                        ))
        except Exception as e:
            logger.warning("CLS fetch failed: %s", e)

        if not items:
            items = await self._fallback_flash(limit)

        logger.info("CLS: %d items", len(items))
        return items

    async def _fallback_flash(self, limit: int) -> list[NewsItem]:
        """降级方案：东方财富 7x24 快讯。"""
        items = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns",
                    params={"columns": "102", "limit": str(limit)},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for art in data.get("data", {}).get("list", []):
                        title = art.get("title", "")
                        if not title:
                            continue
                        ts = art.get("showtime")
                        pub_time = None
                        if ts:
                            try:
                                pub_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                pass
                        items.append(NewsItem(
                            title=title,
                            url=art.get("url_w", ""),
                            source="财联社(东财)",
                            summary=art.get("digest", "")[:200],
                            publish_time=pub_time,
                        ))
        except Exception as e:
            logger.warning("CLS fallback failed: %s", e)
        return items
