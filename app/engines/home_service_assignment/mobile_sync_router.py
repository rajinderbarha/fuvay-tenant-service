"""Technician Mobile App Phase Z — Offline & Sync Center support route.

Read-only idempotency-status lookup only (spec section 16's "unknown
outcome recovery" + section 22's explicit ban on a generic sync-any-request
endpoint). Reuses the EXISTING app/core/idempotency.py cache -- the exact
same Redis key formula the IdempotencyMiddleware already writes on every
successful write -- so a mobile client that lost connectivity after
sending a mutation but before receiving the response can ask "did this
already happen?" without resubmitting. tenant_id is always derived from
the caller's own JWT (UserContext.tenant_id), never a client-supplied
value, so one tenant can never probe another tenant's idempotency cache.
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Query, Request

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.redis_client import get_redis
from app.schemas.base import ok
from app.core.idempotency import IDEMPOTENCY_PREFIX

router = APIRouter(prefix="/v1/mobile/sync", tags=["Technician Mobile Offline & Sync"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/idempotency-status")
async def get_idempotency_status(
    request: Request,
    key: str = Query(..., min_length=1, max_length=200),
    path: str = Query(..., min_length=1, max_length=500),
    user: UserContext = Depends(require_staff_or_technician_only),
):
    tenant_id = user.tenant_id or ""
    cache_key = f"{IDEMPOTENCY_PREFIX}{hashlib.sha256(f'{key}:{path}:{tenant_id}'.encode()).hexdigest()}"
    status = "unknown"
    try:
        r = get_redis()
        cached = await r.get(cache_key)
        if cached:
            status = "confirmed"
    except Exception:
        # Fails open to "unknown" -- never claims confirmed without real
        # evidence in the cache (spec's "never green without evidence" rule
        # applies equally to sync-outcome confirmation).
        status = "unknown"
    return ok({"status": status}, _rid(request), "home_service_assignment")
