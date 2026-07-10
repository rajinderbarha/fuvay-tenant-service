"""
Dependency: engine_guard
Checks that the requested engine is enabled for the current tenant.
Core engines always pass. Plugin engines checked against tenant_engines table (Redis-cached).
"""
from typing import Callable

from fastapi import Depends

from app.dependencies.tenant import TenantContext, get_tenant
from app.exceptions import EngineDisabledException

# Core engines are always enabled — never behind a feature flag
CORE_ENGINES = frozenset({
    "auth", "rag", "notification", "payment",
    "analytics", "media", "review", "chat", "settings",
})


def require_engine(engine_id: str) -> Callable:
    """
    Factory that returns a FastAPI dependency for a specific engine.

    Usage:
        @router.get("/jobs", dependencies=[Depends(require_engine("field_ops"))])
        async def list_jobs(...): ...
    """
    async def _guard(tenant: TenantContext = Depends(get_tenant)) -> TenantContext:
        # Core engines are always available
        if engine_id in CORE_ENGINES:
            return tenant
        # Plugin engines must be explicitly enabled
        if not tenant.has_engine(engine_id):
            raise EngineDisabledException(engine_id, tenant.tenant_id)
        return tenant

    # Give the dependency a meaningful name for FastAPI docs
    _guard.__name__ = f"engine_guard_{engine_id}"
    return _guard
