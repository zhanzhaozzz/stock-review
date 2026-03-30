"""新浪财经滚动新闻采集器。"""
import logging
from datetime import datetime

import httpx

from app.news.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)


class SinaCollector(BaseCollector):
    name = "sina"

    async def fetch_latest(self, limit: int = 30) -> list[NewsItem]:
        """获取新浪财经滚动新闻。"""
        items = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://feed.mix.sina.com.cn/api/roll/get",
                    params={
                        "pageid": "153",
                        "lid": "2516",
                        "k": "",
                        "num": str(limit),
                        "page": "1",
                        "r": "0.1",
                    },
                    headers={
                        "Referer": "https://finance.sina.com.cn/",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for art in data.get("result", {}).get("data", []):
                        title = art.get("title", "").strip()
                        if not title or len(title) < 6:
                            continue
                        pub_time = None
                        ts = art.get("ctime") or art.get("mtime")
                        if ts:
                            try:
                                pub_time = datetime.fromtimestamp(int(ts))
                            except (ValueError, TypeError):
                                pass
                        items.append(NewsItem(
                            title=title,
                            url=art.get("url", ""),
                            source="新浪财经",
                            summary=art.get("intro", "")[:200],
                            publish_time=pub_time,
                        ))
        except Exception as e:
            logger.warning("Sina fetch failed: %s", e)

        logger.info("Sina: %d items", len(items))
        return items
