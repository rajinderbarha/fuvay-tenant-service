"""
Dependency: get_tenant
Extracts and validates the current tenant from the JWT claims.
Checks tenant status (active, suspended, trial) and caches in request state.
"""
from __future__ import annotations
from typing import Annotated

import structlog
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.exceptions import TenantSuspendedException, NotFoundException
from app.redis_client import cache_get, cache_set, RedisKeys
from app.config import get_settings

logger = structlog.get_logger("dependency.tenant")


class TenantContext:
    """Tenant data available to every request handler."""
    def __init__(
        self,
        tenant_id: str,
        tenant_name: str,
        plan_type: str,
        status: str,
        subdomain: str,
        enabled_engines: set[str],
    ):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name
        self.plan_type = plan_type
        self.status = status
        self.subdomain = subdomain
        self.enabled_engines = enabled_engines

    def has_engine(self, engine_id: str) -> bool:
        return engine_id in self.enabled_engines


async def get_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    Extracts tenant_id from JWT (set on request.state by AuthMiddleware in Phase 2).
    In Phase 1: reads X-Tenant-ID header for testing.
    """
    # Phase 2: replace with JWT extraction
    tenant_id = request.headers.get("X-Tenant-ID", "00000000-0000-0000-0000-000000000001")

    # Check cache first
    cache_key = RedisKeys.tenant_config(tenant_id)
    cached = await cache_get(cache_key)
    if cached:
        return TenantContext(**cached)

    # Phase 2: replace stub with real DB lookup
    # For Phase 1, return a stub tenant with all engines enabled
    tenant = TenantContext(
        tenant_id=tenant_id,
        tenant_name="Demo Tenant",
        plan_type="growth",
        status="active",
        subdomain="demo",
        enabled_engines={
            # Core (always on)
            "auth", "rag", "notification", "payment", "analytics",
            "media", "review", "chat", "settings",
            # Plugin (enabled for demo)
            "booking", "field_ops", "dispatch", "notification",
        },
    )

    # Cache tenant context
    await cache_set(cache_key, {
        "tenant_id": tenant.tenant_id,
        "tenant_name": tenant.tenant_name,
        "plan_type": tenant.plan_type,
        "status": tenant.status,
        "subdomain": tenant.subdomain,
        "enabled_engines": list(tenant.enabled_engines),
    }, ttl=get_settings().REDIS_CACHE_TTL_SECONDS)

    if tenant.status == "suspended":
        raise TenantSuspendedException(tenant_id)

    return tenant
