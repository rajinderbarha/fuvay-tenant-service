"""
ServiceOS — Loyalty & Rewards Engine
Prefix: /v1/loyalty
Phase: Stub router — full implementation in Phase 6
"""
from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.engine_guard import require_engine
from app.dependencies.tenant import TenantContext, get_tenant
from app.schemas.base import ApiResponse, Meta
from app.engine_registry.registry import registry

router = APIRouter(prefix="/v1/loyalty", tags=["Loyalty & Rewards"])
ENGINE_ID = "loyalty"


@router.get("/meta", summary="Engine introspection")
async def engine_meta(request: Request) -> dict:
    """Returns engine capabilities, version, endpoint count, dependencies."""
    engine = registry.get(ENGINE_ID)
    return {
        "engine_id": ENGINE_ID,
        "name": engine.name if engine else "Loyalty & Rewards",
        "version": engine.version if engine else "1.0.0",
        "description": engine.description if engine else "",
        "api_prefix": "/v1/loyalty",
        "status": "stub_phase1",
        "planned_endpoints": ['points', 'tiers', 'redeem'],
        "phase": 6,
        "links": {
            "docs": "/docs#loyalty",
            "registry": "/v1/engines/loyalty",
        },
    }


@router.get(
    "",
    summary="List Loyalty & Rewards resources",
    description="Phase 6 stub — returns placeholder. Full implementation in Phase 6.",
)
async def list_resources(
    request: Request,
    tenant: TenantContext = Depends(require_engine(ENGINE_ID)),
    user: UserContext = Depends(get_current_user),
) -> ApiResponse[dict]:
    return ApiResponse(
        data={
            "engine": ENGINE_ID,
            "status": "coming_in_phase_6",
            "message": "Loyalty & Rewards engine is registered and guard is active. Full implementation in Phase 6.",
            "tenant_id": str(tenant.tenant_id),
        },
        meta=Meta(
            request_id=getattr(request.state, "request_id", "—"),
            engine_id=ENGINE_ID,
        ),
    )
