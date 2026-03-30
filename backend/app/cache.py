import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def _is_trading_hours() -> bool:
    """Check if current time is within A-share trading hours (9:15 - 15:15 Beijing time)."""
    now = datetime.now()
    weekday = now.weekday()
    if weekday >= 5:
        return False
    hour, minute = now.hour, now.minute
    t = hour * 60 + minute
    return 9 * 60 + 15 <= t <= 15 * 60 + 15


def get_cache_ttl(override_ttl: int | None = None) -> int:
    if override_ttl is not None:
        return override_ttl
    settings = get_settings()
    return settings.cache_ttl_trading if _is_trading_hours() else settings.cache_ttl_non_trading


async def cache_get(key: str) -> Any | None:
    r = await get_redis()
    try:
        val = await r.get(key)
        if val is not None:
            return json.loads(val)
    except Exception as e:
        logger.warning("Redis GET failed for %s: %s", key, e)
    return None


async def cache_set(key: str, value: Any, ttl: int | None = None):
    r = await get_redis()
    try:
        await r.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=get_cache_ttl(ttl))
    except Exception as e:
        logger.warning("Redis SET failed for %s: %s", key, e)
