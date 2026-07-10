"""
Cross-engine usage counters for tenant plan quotas.

TenantLimits.current_* fields were defined and enforced by
TenantService.check_limit(), but nothing anywhere ever incremented or
decremented them — every tenant's usage silently stayed at zero forever,
making the plan limits unenforceable in practice. This gives other engines
(auth for staff count, field_ops for active jobs) a lightweight way to keep
those counters honest without taking a dependency on the full TenantService.

Tenants with no TenantLimits row are treated as unrestricted (same
philosophy as TenantService.check_limit) — this is a no-op for them, not
an error.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.tenant_engine.models import TenantLimits

VALID_FIELDS = {"current_staff_count", "current_active_jobs", "current_api_calls_today"}


async def adjust_usage(db: AsyncSession, tenant_id: uuid.UUID, field: str, delta: int) -> None:
    if field not in VALID_FIELDS:
        raise ValueError(f"Unknown usage counter field: {field}")
    r = await db.execute(select(TenantLimits).where(TenantLimits.tenant_id == tenant_id))
    limits = r.scalar_one_or_none()
    if not limits:
        return
    current = getattr(limits, field)
    setattr(limits, field, max(0, current + delta))


# ── API call quota (Redis-backed, daily) ─────────────────────────────────────
# Counted in Redis, not Postgres: a per-request DB write would add a write to
# every single API call. The key's TTL is set to expire at the next UTC
# midnight, so the counter "resets daily" for free — no cron/scheduler needed.
def _api_calls_key(tenant_id: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"serviceos:usage:api_calls:{tenant_id}:{today}"


async def increment_api_calls(redis, tenant_id: str) -> int:
    key = _api_calls_key(tenant_id)
    count = await redis.incr(key)
    if count == 1:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await redis.expire(key, int((next_midnight - now).total_seconds()))
    return count


async def get_api_calls_today(redis, tenant_id: str) -> int:
    val = await redis.get(_api_calls_key(tenant_id))
    if val is None:
        return 0
    return int(val.decode() if isinstance(val, bytes) else val)
