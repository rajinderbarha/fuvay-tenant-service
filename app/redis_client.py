"""
ServiceOS — Redis Client
Used for:
  1. Engine flag cache per tenant (TTL 5min)
  2. Rate limiting counters
  3. Event bus pub/sub channel
  4. Session/token blacklist (Phase 2)
  5. Job queue status (Phase 5)
"""
import redis.asyncio as aioredis
import structlog

from app.config import get_settings

logger = structlog.get_logger("redis")

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    settings = get_settings()
    _redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    # Verify connection
    await _redis.ping()
    logger.info("redis.connected", url=settings.REDIS_URL)


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        logger.info("redis.disconnected")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Check app lifespan.")
    return _redis


# ── Key Builders (namespaced, consistent) ────────────────────────────────────
class RedisKeys:
    """Centralized key builder — prevents key collision across engines."""

    @staticmethod
    def tenant_engines(tenant_id: str) -> str:
        """Engine flags for a tenant: {'field_ops': true, 'rag': false, ...}"""
        return f"serviceos:tenant:{tenant_id}:engines"

    @staticmethod
    def tenant_config(tenant_id: str) -> str:
        """Tenant config/settings blob."""
        return f"serviceos:tenant:{tenant_id}:config"

    @staticmethod
    def rate_limit(tenant_id: str, endpoint: str) -> str:
        return f"serviceos:ratelimit:{tenant_id}:{endpoint}"

    @staticmethod
    def token_blacklist(jti: str) -> str:
        """Blacklisted JWT token IDs (logout, password change)."""
        return f"serviceos:auth:blacklist:{jti}"

    @staticmethod
    def job_status(tenant_id: str, job_id: str) -> str:
        return f"serviceos:job:{tenant_id}:{job_id}:status"

    @staticmethod
    def async_job_progress(job_id: str) -> str:
        """Async task progress (bulk ops, PDF generation, embedding)."""
        return f"serviceos:async:{job_id}:progress"

    @staticmethod
    def staff_location(tenant_id: str, staff_id: str) -> str:
        return f"serviceos:geo:{tenant_id}:staff:{staff_id}"

    @staticmethod
    def session(session_id: str) -> str:
        return f"serviceos:session:{session_id}"


# ── Cache Helpers ────────────────────────────────────────────────────────────
import json
from typing import Any


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    value = await r.get(key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    r = get_redis()
    serialized = json.dumps(value) if not isinstance(value, str) else value
    if ttl:
        await r.setex(key, ttl, serialized)
    else:
        await r.set(key, serialized)


async def cache_delete(key: str) -> None:
    r = get_redis()
    await r.delete(key)


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Use sparingly."""
    r = get_redis()
    keys = await r.keys(pattern)
    if keys:
        return await r.delete(*keys)
    return 0
