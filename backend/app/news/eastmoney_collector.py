"""东方财富新闻采集器 — 支持关键词搜索和个股新闻。"""
import json
import logging
import re
import urllib.parse
from datetime import datetime

import httpx

from app.news.base import BaseCollector, NewsItem

logger = logging.getLogger(__name__)


class EastMoneyCollector(BaseCollector):
    name = "eastmoney"

    async def fetch_latest(self, limit: int = 30) -> list[NewsItem]:
        """获取东方财富财经要闻。"""
        items = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns",
                    params={"columns": "350", "limit": str(limit)},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for art in data.get("data", {}).get("list", []):
                        title = art.get("title", "").strip()
                        if not title:
                            continue
                        pub_time = None
                        ts = art.get("showtime")
                        if ts:
                            try:
                                pub_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                pass
                        items.append(NewsItem(
                            title=title,
                            url=art.get("url_w", ""),
                            source="东方财富",
                            summary=art.get("digest", "")[:200],
                            publish_time=pub_time,
                        ))
        except Exception as e:
            logger.warning("EastMoney latest failed: %s", e)
        logger.info("EastMoney latest: %d items", len(items))
        return items

    async def fetch_by_stock(self, code: str, name: str, limit: int = 10) -> list[NewsItem]:
        """按股票名称搜索东方财富新闻。"""
        return await self._search(name, limit)

    async def _search(self, keyword: str, limit: int = 15) -> list[NewsItem]:
        items = []
        try:
            encoded = urllib.parse.quote(keyword)
            url = (
                f"https://search-api-web.eastmoney.com/search/jsonp?"
                f"cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{encoded}%22"
                f"%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D"
                f"%2C%22client%22%3A%22web%22%2C%22clientType%22%3A%22web%22"
                f"%2C%22clientVersion%22%3A%22curr%22"
                f"%2C%22param%22%3A%7B%22cmsArticleWebOld%22%3A%7B%22searchScope%22%3A%22default%22"
                f"%2C%22sort%22%3A%22default%22%2C%22pageIndex%22%3A1%2C%22pageSize%22%3A{limit}"
                f"%2C%22preTag%22%3A%22%22%2C%22postTag%22%3A%22%22%7D%7D%7D"
            )
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers={
                    "Referer": "https://www.eastmoney.com/",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                })
                if resp.status_code == 200:
                    match = re.search(r"jQuery\((\{.*\})\)", resp.text, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        cms = data.get("result", {}).get("cmsArticleWebOld", {})
                        raw_list = cms if isinstance(cms, list) else (cms.get("list", []) if isinstance(cms, dict) else [])
                        for item in raw_list:
                            if not isinstance(item, dict):
                                continue
                            title = re.sub(r"<[^>]+>", "", item.get("title", "")).strip()
                            if title and len(title) > 6:
                                pub_time = None
                                ts = item.get("date")
                                if ts:
                                    try:
                                        pub_time = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
                                    except ValueError:
                                        pass
                                items.append(NewsItem(
                                    title=title,
                                    url=item.get("url", ""),
                                    source="东方财富",
                                    publish_time=pub_time,
                                ))
        except Exception as e:
            logger.warning("EastMoney search '%s' failed: %s", keyword, e)
        return items
