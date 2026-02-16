from __future__ import annotations

import json
import logging
import time
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from app.config import get_settings

request_id_ctx: ContextVar[str | None] = ContextVar('request_id', default=None)
_events: deque[dict[str, Any]] = deque(maxlen=500)


def now_ms() -> int:
    return int(time.time() * 1000)


def profiling_enabled() -> bool:
    return bool(get_settings().softhub_profile)


def set_request_id(request_id: str | None) -> None:
    request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def push_event(event: dict[str, Any]) -> None:
    payload = dict(event)
    payload.setdefault('ts_ms', now_ms())
    rid = get_request_id()
    if rid:
        payload.setdefault('request_id', rid)
    _events.append(payload)


def last_events(limit: int = 100) -> list[dict[str, Any]]:
    safe = max(1, min(limit, len(_events) or 1))
    return list(_events)[-safe:]


def log_profile_event(logger: logging.Logger, event: dict[str, Any]) -> None:
    payload = dict(event)
    payload.setdefault('ts_ms', now_ms())
    rid = get_request_id()
    if rid:
        payload.setdefault('request_id', rid)
    push_event(payload)
    if profiling_enabled():
        logger.info(json.dumps(payload, ensure_ascii=False, separators=(',', ':')))


@contextmanager
def timer(name: str, logger: logging.Logger, extra: dict[str, Any] | None = None):
    started = now_ms()
    try:
        yield
    finally:
        elapsed = now_ms() - started
        event = {'step_name': name, 'elapsed_ms': elapsed}
        if extra:
            event.update(extra)
        log_profile_event(logger, event)
