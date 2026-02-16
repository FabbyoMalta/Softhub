from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def cache_get_json(key: str) -> dict[str, Any] | None:
    try:
        raw = get_redis().get(key)
        if not raw:
            return None
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception as exc:
        logger.warning('cache_get_json failed key=%s err=%s', key, exc)
        return None


def cache_set_json(key: str, value: dict[str, Any], ttl_s: int | None = None) -> None:
    ttl = ttl_s or get_settings().dashboard_cache_ttl_s
    try:
        get_redis().setex(key, int(ttl), json.dumps(value, ensure_ascii=False, separators=(',', ':')))
    except Exception as exc:
        logger.warning('cache_set_json failed key=%s err=%s', key, exc)


def stable_json_hash(payload: dict[str, Any] | None) -> str:
    canonical = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha1(canonical.encode('utf-8')).hexdigest()
