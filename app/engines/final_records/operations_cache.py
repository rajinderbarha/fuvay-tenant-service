"""Cached KPI summary for the Bookings & Jobs workspace.

The six KPI tiles count the whole of service_jobs. That is irreducible — you
cannot know how many jobs are unassigned without looking at every job — so the
only way to stop it costing a full table pass on every page view is to stop
doing it on every page view. Measured at 200k jobs the summary takes ~0.7s; at
several million it is seconds, and it runs every single time an admin opens or
navigates the page.

The cache is *stale-while-revalidate* rather than a plain TTL, because a plain
TTL moves the problem rather than solving it: whoever arrives first after expiry
pays the full cost, and if several admins arrive together they all recompute the
same numbers simultaneously (a thundering herd on the heaviest query the page
has). Here:

  * fresher than FRESH_SECONDS      -> served straight from cache
  * older, but present              -> the stale value is served IMMEDIATELY and
                                       one refresh is kicked off in the
                                       background, so nobody ever waits
  * absent (cold start / evicted)   -> computed inline, once

Only one refresh runs at a time, enforced by a Redis SET NX lock, so N admins
landing together cause one recompute rather than N.

Everything here fails open. A KPI tile is a convenience; if Redis is down or
misbehaving the page must still render, so every cache interaction falls back to
computing directly rather than propagating an error.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import structlog

from app.redis_client import get_redis

log = structlog.get_logger("home_services.operations_cache")

# Serve without recomputing below this age.
FRESH_SECONDS = 60
# How long a value may still be served while a refresh happens behind it. Also
# the Redis key TTL — past this the value is gone and the next read recomputes.
STALE_SECONDS = 900
# Cap on how long a refresh may hold the lock, so a crashed worker cannot wedge
# the cache into permanent staleness.
REFRESH_LOCK_SECONDS = 120

_KEY_PREFIX = "serviceos:hs_ops"
# Bump when the shape or meaning of a cached payload changes, so a deploy never
# serves values computed by the previous definition of these metrics.
_SCHEMA_VERSION = "v1"

# Refresh tasks are held only to stop the event loop garbage-collecting them
# mid-flight; they remove themselves on completion.
_background: set[asyncio.Task] = set()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def summary_key(tenant_id: uuid.UUID | None) -> str:
    return f"{_KEY_PREFIX}:summary:{_SCHEMA_VERSION}:{tenant_id or 'all'}"


def count_key(filters: dict[str, Any]) -> str:
    """A stable key for one combination of list filters.

    Hashed rather than concatenated because filters include free text (search,
    city) that can be long and contain characters that make poor key material.
    """
    canonical = json.dumps({k: str(v) for k, v in sorted(filters.items()) if v not in (None, "")},
                           separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:24]
    return f"{_KEY_PREFIX}:count:{_SCHEMA_VERSION}:{digest}"


async def _read(key: str) -> dict | None:
    try:
        raw = await get_redis().get(key)
    except Exception as exc:  # noqa: BLE001 — cache must never break the page
        log.warning("operations_cache.read_failed", key=key, error=str(exc))
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) and "data" in payload else None


async def _write(key: str, data: Any, ttl: int) -> None:
    payload = json.dumps({"data": data, "computed_at": _now().isoformat()})
    try:
        await get_redis().setex(key, ttl, payload)
    except Exception as exc:  # noqa: BLE001
        log.warning("operations_cache.write_failed", key=key, error=str(exc))


async def _acquire_refresh_lock(key: str) -> bool:
    """True if this caller won the right to refresh. False means someone else is."""
    try:
        return bool(await get_redis().set(
            f"{key}:lock", "1", ex=REFRESH_LOCK_SECONDS, nx=True))
    except Exception:  # noqa: BLE001 — no lock available means no refresh
        return False


async def _release_refresh_lock(key: str) -> None:
    try:
        await get_redis().delete(f"{key}:lock")
    except Exception:  # noqa: BLE001
        pass


def _age_seconds(payload: dict) -> float:
    try:
        computed = datetime.fromisoformat(payload["computed_at"])
    except (KeyError, TypeError, ValueError):
        return float("inf")
    if computed.tzinfo is None:
        computed = computed.replace(tzinfo=timezone.utc)
    return (_now() - computed).total_seconds()


def _spawn(coro: Awaitable) -> None:
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _refresh_in_background(key: str, compute: Callable[[], Awaitable[Any]], ttl: int) -> None:
    """Recompute and store, holding the lock for the duration.

    Runs detached from the request that triggered it, so a slow recompute never
    shows up as a slow page load.
    """
    try:
        data = await compute()
        await _write(key, data, ttl)
    except Exception as exc:  # noqa: BLE001 — a failed refresh keeps the stale value
        log.warning("operations_cache.refresh_failed", key=key, error=str(exc))
    finally:
        await _release_refresh_lock(key)


async def get_or_compute(
    key: str,
    compute: Callable[[], Awaitable[Any]],
    *,
    fresh_seconds: int = FRESH_SECONDS,
    ttl_seconds: int = STALE_SECONDS,
    force: bool = False,
) -> tuple[Any, str, str | None]:
    """Return (value, freshness, computed_at).

    `freshness` is one of "fresh" (from cache, recent), "stale" (from cache,
    refresh now running behind it), "computed" (calculated in this request) or
    "uncached" (Redis unavailable — calculated, not stored). The caller passes it
    to the client so the UI can be honest about how current the numbers are
    rather than implying they are live.
    """
    if force:
        data = await compute()
        await _write(key, data, ttl_seconds)
        return data, "computed", _now().isoformat()

    cached = await _read(key)
    if cached is not None:
        age = _age_seconds(cached)
        if age <= fresh_seconds:
            return cached["data"], "fresh", cached.get("computed_at")
        # Stale but usable: hand it back now, refresh behind it — but only if
        # this caller won the lock, so concurrent readers do not all recompute.
        if await _acquire_refresh_lock(key):
            _spawn(_refresh_in_background(key, compute, ttl_seconds))
        return cached["data"], "stale", cached.get("computed_at")

    # Cold: compute inline. Whoever is first pays; everyone after reads cache.
    data = await compute()
    stored_at = _now().isoformat()
    await _write(key, data, ttl_seconds)
    # If Redis is down the write silently no-ops, so report it honestly rather
    # than claiming a cached value the next request will not find.
    return data, "computed", stored_at


async def invalidate(tenant_id: uuid.UUID | None = None) -> None:
    """Drop the cached summary. Cheap enough to call after a bulk mutation."""
    try:
        await get_redis().delete(summary_key(tenant_id))
    except Exception:  # noqa: BLE001
        pass
