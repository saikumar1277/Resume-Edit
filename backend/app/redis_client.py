"""Sync Redis client for rate limits and short-lived auth tokens."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis

from .config import REDIS_URL

log = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def ping_redis() -> bool:
    return bool(get_redis().ping())


def reset_client() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            log.debug("redis close failed", exc_info=True)
        _client = None


def put_token(kind: str, token: str, value: str, ttl_s: int) -> None:
    get_redis().setex(f"{kind}:{_digest(token)}", ttl_s, value)


def take_token(kind: str, token: str) -> str | None:
    key = f"{kind}:{_digest(token)}"
    pipe = get_redis().pipeline()
    pipe.get(key)
    pipe.delete(key)
    value, _deleted = pipe.execute()
    if value is None:
        return None
    return str(value)


def put_json(kind: str, token: str, payload: dict[str, Any], ttl_s: int) -> None:
    put_token(kind, token, json.dumps(payload), ttl_s)


def take_json(kind: str, token: str) -> dict[str, Any] | None:
    raw = take_token(kind, token)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
