from __future__ import annotations

import json
import logging
from functools import lru_cache

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def get_json(key: str) -> dict | None:
    try:
        raw = get_redis_client().get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning('redis cache get failed for key=%s: %s', key, exc)
        return None


def set_json(key: str, payload: dict, ttl_seconds: int = 45) -> None:
    try:
        get_redis_client().setex(key, ttl_seconds, json.dumps(payload, separators=(',', ':')))
    except Exception as exc:
        logger.warning('redis cache set failed for key=%s: %s', key, exc)
