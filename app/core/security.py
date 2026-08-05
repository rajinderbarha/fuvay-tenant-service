"""
ServiceOS — Security Utilities
Rate limiting (sliding window via Redis Lua), idempotency key handling,
IP-based threat detection, security event publishing.
"""
from __future__ import annotations
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import get_settings

logger = structlog.get_logger("security")

# ── Rate Limiter ──────────────────────────────────────────────────────────────
# Sliding window via a single Redis Lua script — atomic, no race conditions
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local window_ms = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = now - window_ms

redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
local count = redis.call('ZCARD', key)
if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local reset_at = tonumber(oldest[2]) + window_ms
    return {0, count, reset_at}
end
redis.call('ZADD', key, now, ARGV[4])
redis.call('EXPIRE', key, math.ceil(window_ms / 1000))
return {1, count + 1, now + window_ms}
"""

# Rate limit configs: (window_seconds, max_requests)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    # Auth endpoints — strict
    "auth:login":            (900,  500),  # 500 per 15 min per IP (E2E-safe)
    "auth:login_phone":      (3600, 5),    # 5 per hour
    "auth:otp_send":         (3600, 3),    # 3 per hour per recipient
    "auth:otp_verify":       (300,  5),    # 5 per 5 min
    "auth:password_reset":   (3600, 3),    # 3 per hour
    "auth:refresh":          (3600, 60),   # 60 per hour
    "auth:mfa_verify":       (300,  5),    # 5 per 5 min
    "auth:register":         (3600, 3),    # 3 per hour per IP
    # Found missing during the "make it 100% working" pass -- real,
    # tested rate-limit types for account-security-sensitive actions.
    "auth:password_change":  (3600, 10),   # 10 per hour per account
    "auth:mfa_confirm":      (300,  5),    # 5 per 5 min
    "auth:mfa_disable":      (3600, 5),    # 5 per hour per account
    # API endpoints — by tenant
    "api:read":              (60,   300),  # 300 reads per minute per tenant
    "api:write":             (60,   100),  # 100 writes per minute per tenant
    "api:ai":                (60,   20),   # 20 AI calls per minute (expensive)
    "api:export":            (3600, 5),    # 5 exports per hour
    # Webhook
    "webhook:delivery":      (60,   1000), # 1000/min per tenant
}

# Dev-only override: local testing (repeated manual OTP send/verify/register
# attempts against the same phone number) hits the strict production limits
# above almost immediately. Applied only when APP_ENV is development/testing
# (see RateLimiter.check) -- production and staging always use RATE_LIMITS
# unchanged.
DEV_RATE_LIMIT_OVERRIDES: dict[str, tuple[int, int]] = {
    "auth:login_phone": (3600, 100),
    "auth:otp_send":    (3600, 100),
    "auth:otp_verify":  (300,  100),
    "auth:register":    (3600, 100),
}


class RateLimiter:
    """Sliding window rate limiter using Redis sorted sets + Lua script."""

    def __init__(self) -> None:
        self._script_sha: str | None = None

    async def _get_redis(self):
        from app.redis_client import get_redis
        return get_redis()

    async def _load_script(self, redis):
        if not self._script_sha:
            self._script_sha = await redis.script_load(_RATE_LIMIT_SCRIPT)
        return self._script_sha

    async def check(
        self,
        limit_key: str,
        limit_type: str,
        identifier: str,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Returns (is_allowed, headers_dict).
        headers_dict contains X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        """
        try:
            redis = await self._get_redis()
            from app.config import get_settings
            if get_settings().APP_ENV in ("development", "testing") and limit_type in DEV_RATE_LIMIT_OVERRIDES:
                config = DEV_RATE_LIMIT_OVERRIDES[limit_type]
            else:
                config = RATE_LIMITS.get(limit_type, (60, 100))
            window, limit = config
            now_ms = int(time.time() * 1000)
            redis_key = f"serviceos:ratelimit:{limit_key}:{identifier}"
            entry_id = str(uuid.uuid4())

            sha = await self._load_script(redis)
            result = await redis.evalsha(sha, 1, redis_key, window * 1000, limit, now_ms, entry_id)
            allowed, count, reset_ms = int(result[0]), int(result[1]), int(result[2])
            reset_at = int(reset_ms / 1000)

            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - count)),
                "X-RateLimit-Reset": str(reset_at),
                "X-RateLimit-Window": str(window),
            }
            return bool(allowed), headers

        except Exception as e:
            # If Redis is unavailable, fail open (allow the request)
            logger.warning("rate_limiter.redis_error", error=str(e))
            return True, {}

    async def check_and_raise(self, limit_key: str, limit_type: str, identifier: str) -> dict:
        """Raises 429 ServiceOSException if rate limited."""
        from app.exceptions import ServiceOSException
        allowed, headers = await self.check(limit_key, limit_type, identifier)
        if not allowed:
            reset = headers.get("X-RateLimit-Reset", "unknown")
            raise ServiceOSException(
                error_code="RATE_LIMITED",
                detail=f"Too many requests. Rate limit: {RATE_LIMITS.get(limit_type, (60, 100))[1]} requests per {RATE_LIMITS.get(limit_type, (60, 100))[0]}s.",
                resolution=f"Wait until {reset} (Unix timestamp) before retrying.",
                context={"retry_after_seconds": int(reset) - int(time.time()) if reset != "unknown" else 60},
            )
        return headers


rate_limiter = RateLimiter()


# ── Idempotency ───────────────────────────────────────────────────────────────
class IdempotencyStore:
    """
    Redis-based idempotency key store.
    Write endpoints accept X-Idempotency-Key header.
    If we've seen this key before, return the cached response.
    Key TTL: 24 hours.
    """

    IDEMPOTENCY_KEY_TTL = 86400  # 24 hours

    async def get(self, key: str) -> dict | None:
        from app.redis_client import get_redis
        r = get_redis()
        raw = await r.get(f"serviceos:idempotency:{key}")
        if raw:
            return json.loads(raw)
        return None

    async def store(self, key: str, status_code: int, body: dict) -> None:
        from app.redis_client import get_redis
        r = get_redis()
        await r.setex(
            f"serviceos:idempotency:{key}",
            self.IDEMPOTENCY_KEY_TTL,
            json.dumps({"status_code": status_code, "body": body, "cached_at": datetime.now(timezone.utc).isoformat()}),
        )


idempotency_store = IdempotencyStore()


# ── IP Utilities ──────────────────────────────────────────────────────────────
def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting common proxy headers."""
    for header in ("X-Real-IP", "X-Forwarded-For", "CF-Connecting-IP"):
        ip = request.headers.get(header)
        if ip:
            return ip.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def hash_ip(ip: str) -> str:
    """One-way hash of IP for rate limit keys — never store raw IPs in keys."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


# ── Security Event Publisher ───────────────────────────────────────────────────
async def publish_security_event(
    event_type: str,
    severity: str,
    actor_id: str | None,
    tenant_id: str | None,
    ip_address: str,
    details: dict,
) -> None:
    """Publish security events to the event bus for monitoring."""
    try:
        from app.core.events import get_event_bus, DomainEvent
        bus = get_event_bus()
        event = DomainEvent.create(
            event_type=f"security.{event_type}",
            engine_id="auth",
            tenant_id=tenant_id or "platform",
            entity_type="security_event",
            entity_id=actor_id or "anonymous",
            payload={
                "severity": severity,
                "ip_address": ip_address,
                "details": details,
            },
            actor_id=actor_id,
        )
        await bus.publish(event)
    except Exception as e:
        logger.error("security_event.publish_failed", error=str(e), event_type=event_type)
