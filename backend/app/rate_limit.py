"""In-process helpers that count hits in Redis."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request

from .redis_client import get_redis

log = logging.getLogger(__name__)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce(request: Request, bucket: str, limit: int, window_s: int = 60) -> None:
    try:
        redis = get_redis()
        key = f"rl:{bucket}:{client_ip(request)}"
        count = int(redis.incr(key))
        if count == 1:
            redis.expire(key, window_s)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("rate limit redis failed")
        raise HTTPException(
            status_code=503, detail="Service temporarily unavailable."
        ) from exc
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again in a minute.",
        )
