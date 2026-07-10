"""Dependency: get_redis — returns the shared async Redis client."""
import redis.asyncio as aioredis
from app.redis_client import get_redis as _get_redis


def get_redis() -> aioredis.Redis:
    """FastAPI dependency — returns shared Redis client."""
    return _get_redis()
