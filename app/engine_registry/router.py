"""
GET /v1/engines — Engine registry introspection endpoint.
Returns all registered engines with their metadata.
This is the source of truth for what's available on the platform.
"""
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.tenant import TenantContext, get_tenant
from app.engine_registry.registry import registry
from app.schemas.base import ApiResponse, Meta

router = APIRouter(prefix="/engines", tags=["Engine Registry"])


@router.get(
    "",
    summary="List all platform engines",
    description="Returns all 23 registered engines with metadata, health status, and tenant-specific enabled state.",
    response_model=ApiResponse[dict],
)
async def list_engines(
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    user: UserContext = Depends(get_current_user),
) -> ApiResponse[dict]:
    engines_out = []
    for engine in registry.all():
        engines_out.append({
            "engine_id": engine.engine_id,
            "name": engine.name,
            "description": engine.description,
            "engine_type": engine.engine_type,
            "version": engine.version,
            "category": engine.category,
            "api_prefix": engine.api_prefix,
            "endpoint_count": engine.endpoint_count,
            "dependencies": engine.dependencies,
            "is_enabled": engine.engine_id in tenant.enabled_engines,
            "is_healthy": engine.is_healthy,
            "is_core": engine.engine_type == "core",
            "links": {
                "introspect": f"{engine.api_prefix}/meta",
                "docs": f"/docs#{engine.engine_id}",
            },
        })

    return ApiResponse(
        data={
            "total": len(engines_out),
            "core": sum(1 for e in engines_out if e["is_core"]),
            "plugin": sum(1 for e in engines_out if not e["is_core"]),
            "tenant_enabled": sum(1 for e in engines_out if e["is_enabled"]),
            "engines": engines_out,
        },
        meta=Meta(
            request_id=getattr(request.state, "request_id", "—"),
            engine_id="registry",
        ),
    )


@router.get(
    "/{engine_id}",
    summary="Get engine details",
    response_model=ApiResponse[dict],
)
async def get_engine(
    engine_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant),
    user: UserContext = Depends(get_current_user),
) -> ApiResponse[dict]:
    from app.exceptions import NotFoundException
    engine = registry.get(engine_id)
    if not engine:
        raise NotFoundException("Engine", engine_id)

    return ApiResponse(
        data={
            **engine.__dict__,
            "is_enabled_for_tenant": engine_id in tenant.enabled_engines,
        },
        meta=Meta(request_id=getattr(request.state, "request_id", "—")),
    )
