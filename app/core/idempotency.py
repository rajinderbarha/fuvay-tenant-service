"""
ServiceOS — Idempotency Key Middleware
All write endpoints accept X-Idempotency-Key header.
Same key within 24h returns the cached response — safe to retry.
"""
import hashlib
import json
from datetime import timedelta

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.redis_client import get_redis

logger = structlog.get_logger("idempotency")

IDEMPOTENCY_TTL = int(timedelta(hours=24).total_seconds())
IDEMPOTENCY_PREFIX = "serviceos:idempotency:"
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Checks X-Idempotency-Key on write requests.
    If key was used before: returns cached response immediately.
    If new key: processes request, caches response, returns it.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        idempotency_key = request.headers.get("X-Idempotency-Key")

        # Only apply to write methods that provide the key
        if not idempotency_key or request.method not in WRITE_METHODS:
            return await call_next(request)

        # Build cache key: hash of (key + path + tenant_id)
        tenant_id = request.headers.get("X-Tenant-ID", "")
        cache_key = f"{IDEMPOTENCY_PREFIX}{hashlib.sha256(f'{idempotency_key}:{request.url.path}:{tenant_id}'.encode()).hexdigest()}"

        try:
            r = get_redis()
            cached = await r.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                logger.info("idempotency.cache_hit", key=idempotency_key[:8] + "...", path=request.url.path)
                return Response(
                    content=cached_data["body"],
                    status_code=cached_data["status_code"],
                    headers={**cached_data.get("headers", {}), "X-Idempotency-Replayed": "true"},
                    media_type="application/json",
                )
        except Exception:
            pass  # Redis unavailable — process normally

        response = await call_next(request)

        # Cache the response if successful
        try:
            if 200 <= response.status_code < 300:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                cache_data = json.dumps({
                    "body": body.decode(),
                    "status_code": response.status_code,
                    "headers": {"Content-Type": response.headers.get("Content-Type", "application/json")},
                })
                r = get_redis()
                await r.setex(cache_key, IDEMPOTENCY_TTL, cache_data)

                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
        except Exception:
            pass

        return response
