"""Enterprise Engine Management admin router — /v1/admin/engines/."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin
from app.dependencies.db import get_db
from app.engines.engine_mgmt.service import EngineMgmtService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/engines", tags=["admin-engine-management"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db: AsyncSession, u) -> EngineMgmtService:
    return EngineMgmtService(db, u.user_id, u.role)


def _mounted_route_paths(app) -> set[str]:
    """Collect routes from FastAPI, including lazy ``_IncludedRouter`` nodes."""
    paths: set[str] = set()
    seen: set[int] = set()

    def visit(routes) -> None:
        for route in routes or []:
            if id(route) in seen:
                continue
            seen.add(id(route))
            path = getattr(route, "path", None) or getattr(route, "path_format", None)
            if path:
                paths.add(str(path))
            nested = getattr(route, "routes", None)
            if nested:
                visit(nested)
            original = getattr(route, "original_router", None)
            if original is not None:
                visit(getattr(original, "routes", None))

    visit(getattr(app, "routes", None))
    return paths


# ── Registry (static routes BEFORE /{engine_key}) ────────────────────────────

@router.get("/summary")
async def get_summary(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_summary(), _rid(r), "engine_management")


@router.get("/control-plane")
async def get_control_plane(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    route_paths = _mounted_route_paths(r.app)
    return ok(
        await _svc(db, u).get_control_plane(route_paths),
        _rid(r),
        "engine_management",
    )


@router.get("/vertical-usage")
async def get_vertical_usage(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_vertical_usage(), _rid(r), "engine_management")


@router.get("")
async def list_engines(
    r: Request,
    engine_type: Optional[str] = Query(None),
    global_status: Optional[str] = Query(None),
    lifecycle_status: Optional[str] = Query(None),
    is_core: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_engines(
        engine_type=engine_type, global_status=global_status,
        lifecycle_status=lifecycle_status, is_core=is_core, q=q,
        page=page, limit=limit), _rid(r), "engine_management")


@router.post("")
async def create_engine(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).create_engine(body), _rid(r), "engine_management")


# ── Category Matrix (static — before /{engine_key}) ──────────────────────────

@router.get("/category-matrix/templates")
async def list_category_matrix_templates(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(_svc(db, u).list_category_templates(), _rid(r), "engine_management")


@router.get("/category-matrix")
async def get_category_matrix(
    r: Request,
    category_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_category_matrix(
        category_id=category_id, page=page, limit=limit), _rid(r), "engine_management")


@router.get("/category-matrix/export")
async def export_category_matrix(
    r: Request,
    category_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    if category_id:
        data = await _svc(db, u).get_category_matrix_for_category(category_id)
        rows = data["rows"]
    else:
        data = await _svc(db, u).get_category_matrix()
        rows = data["matrix"]
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), "engine_management")


@router.get("/category-matrix/{category_id}")
async def get_category_matrix_detail(
    r: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_category_matrix_for_category(category_id),
              _rid(r), "engine_management")


@router.get("/category-matrix/{category_id}/summary")
async def get_category_matrix_summary(
    r: Request,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_category_matrix_summary(category_id),
              _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/seed-defaults/preview")
async def seed_category_defaults_preview(
    r: Request,
    category_id: uuid.UUID,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).seed_defaults_preview(category_id, body.get("template")),
              _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/seed-defaults")
async def seed_category_defaults(
    r: Request,
    category_id: uuid.UUID,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).seed_defaults(
        category_id, body.get("template"), body.get("dry_run", False),
        body.get("reason", "Seeded recommended defaults")), _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/engines/{engine_key}/enable-preview")
async def enable_category_engine_preview(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).category_engine_action_preview(category_id, engine_key, "enable"),
              _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/engines/{engine_key}/disable-preview")
async def disable_category_engine_preview(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).category_engine_action_preview(category_id, engine_key, "disable"),
              _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/engines/{engine_key}/enable")
async def enable_category_engine(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).enable_category_engine(
        category_id, engine_key, reason=body.get("reason", ""),
        force=body.get("force", False)), _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/engines/{engine_key}/disable")
async def disable_category_engine(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).disable_category_engine(
        category_id, engine_key, reason=body.get("reason", ""),
        force=body.get("force", False)), _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/engines/{engine_key}/mark-required")
async def mark_category_engine_required(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).mark_category_engine_required(
        category_id, engine_key, body.get("reason", "Marked as required")),
        _rid(r), "engine_management")


@router.post("/category-matrix/{category_id}/engines/{engine_key}/mark-optional")
async def mark_category_engine_optional(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).mark_category_engine_optional(
        category_id, engine_key, body.get("reason", "Marked as optional")),
        _rid(r), "engine_management")


@router.get("/category-matrix/{category_id}/engines/{engine_key}/packages")
async def category_engine_package_usage(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_category_engine_package_usage(category_id, engine_key),
              _rid(r), "engine_management")


@router.get("/category-matrix/{category_id}/engines/{engine_key}/tenant-impact")
async def category_engine_tenant_impact(
    r: Request,
    category_id: uuid.UUID,
    engine_key: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_category_engine_tenant_impact(category_id, engine_key),
              _rid(r), "engine_management")


# ── Dependencies (static — before /{engine_key}) ──────────────────────────────

@router.get("/dependencies/graph")
async def get_dependency_graph(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_dependencies_graph(), _rid(r), "engine_management")


@router.post("/dependencies/validate")
async def validate_dependencies(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    engine_key = body.get("engine_key", "")
    action = body.get("action", "enable")
    preview = await _svc(db, u).get_impact_preview(engine_key, action)
    return ok({
        "engine_key": engine_key,
        "valid": preview["can_proceed"],
        "blockers": preview["blockers"],
        "warnings": preview.get("warnings", []),
    }, _rid(r), "engine_management")


@router.get("/dependencies")
async def list_all_dependencies(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    from sqlalchemy import select
    from app.engines.engine_mgmt.models import EngineDependency
    rows = (await db.execute(
        select(EngineDependency).where(EngineDependency.status == "active")
    )).scalars().all()
    return ok({"dependencies": [row.to_dict() for row in rows], "total": len(rows)},
              _rid(r), "engine_management")


# ── Package Entitlements (static — before /{engine_key}) ─────────────────────

@router.get("/package-entitlements")
async def get_package_entitlements_all(
    r: Request,
    package_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_package_entitlements(
        package_id=package_id, page=page, limit=limit), _rid(r), "engine_management")


@router.get("/package-entitlements/{package_id}")
async def get_package_entitlements(
    r: Request,
    package_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_package_entitlements(
        package_id=package_id), _rid(r), "engine_management")


@router.post("/package-entitlements/{package_id}/engines/{engine_key}/include")
async def include_package_engine(
    r: Request,
    package_id: uuid.UUID,
    engine_key: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).set_package_engine(
        package_id, engine_key, included=True,
        limits=body.get("limits"), feature_flags=body.get("feature_flags"),
        reason=body.get("reason", "")), _rid(r), "engine_management")


@router.post("/package-entitlements/{package_id}/engines/{engine_key}/remove")
async def remove_package_engine(
    r: Request,
    package_id: uuid.UUID,
    engine_key: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).set_package_engine(
        package_id, engine_key, included=False,
        reason=body.get("reason", "")), _rid(r), "engine_management")


@router.post("/package-entitlements/{package_id}/preview-impact")
async def package_entitlement_impact(
    r: Request,
    package_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    engine_key = body.get("engine_key", "")
    preview = await _svc(db, u).get_impact_preview(engine_key, body.get("action", "disable"))
    return ok({**preview, "package_id": str(package_id)}, _rid(r), "engine_management")


# ── Tenant Overrides (static — before /{engine_key}) ─────────────────────────

@router.get("/tenant-overrides")
async def list_all_overrides(
    r: Request,
    tenant_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_tenant_overrides(
        tenant_id=tenant_id, status=status, page=page, limit=limit),
        _rid(r), "engine_management")


@router.get("/tenant-overrides/{tenant_id}")
async def get_tenant_overrides(
    r: Request,
    tenant_id: uuid.UUID,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_tenant_overrides(
        tenant_id=tenant_id, status=status), _rid(r), "engine_management")


@router.post("/tenant-overrides/{tenant_id}")
async def create_tenant_override(
    r: Request,
    tenant_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).create_tenant_override(tenant_id, body),
              _rid(r), "engine_management")


@router.post("/tenant-overrides/{tenant_id}/{override_id}/revoke")
async def revoke_tenant_override(
    r: Request,
    tenant_id: uuid.UUID,
    override_id: uuid.UUID,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).revoke_tenant_override(
        override_id, body.get("reason", "Revoked by admin")), _rid(r), "engine_management")


# ── Health (static — before /{engine_key}) ────────────────────────────────────

@router.get("/health")
async def get_health_overview(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_health_overview(), _rid(r), "engine_management")


@router.post("/health/check-all")
async def run_all_health_checks(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    from sqlalchemy import select
    from app.engines.engine_mgmt.models import PlatformEngine
    engines = (await db.execute(select(PlatformEngine.engine_key))).scalars().all()
    results = []
    svc = _svc(db, u)
    for ek in engines:
        try:
            results.append(await svc.run_health_check(ek))
        except Exception as e:
            results.append({"engine_key": ek, "health_status": "down", "error": str(e)})
    return ok({"results": results, "total": len(results)}, _rid(r), "engine_management")


# ── Permissions (static — before /{engine_key}) ───────────────────────────────

@router.get("/permissions")
async def list_all_permissions(
    r: Request,
    engine_key: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_permissions(
        engine_key=engine_key, scope=scope, q=q, page=page, limit=limit),
        _rid(r), "engine_management")


@router.put("/permissions/{permission_id}")
async def update_permission(
    r: Request,
    permission_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).update_permission(permission_id, body),
              _rid(r), "engine_management")


# ── Audit Logs (static — before /{engine_key}) ────────────────────────────────

@router.get("/audit-logs")
async def list_audit_logs(
    r: Request,
    engine_key: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    scope_type: Optional[str] = Query(None),
    scope_id: Optional[uuid.UUID] = Query(None),
    exclude_health_checks: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_audit_logs(
        engine_key=engine_key, action_type=action_type,
        scope_type=scope_type, scope_id=scope_id,
        exclude_health_checks=exclude_health_checks, page=page, limit=limit),
        _rid(r), "engine_management")


# ── Runtime Access Resolver (static — before /{engine_key}) ──────────────────

@router.post("/resolve-access-preview")
async def resolve_access_preview(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    engine_key = body.get("engine_key", "")
    tenant_id = uuid.UUID(str(body["tenant_id"])) if body.get("tenant_id") else None
    category_id = uuid.UUID(str(body["category_id"])) if body.get("category_id") else None
    package_id = uuid.UUID(str(body["package_id"])) if body.get("package_id") else None
    result = await _svc(db, u).resolve_access(
        engine_key, tenant_id=tenant_id, category_id=category_id, package_id=package_id)
    return ok(result, _rid(r), "engine_management")


# ── Per-engine routes (/{engine_key} — AFTER all static routes) ───────────────

@router.get("/{engine_key}")
async def get_engine(
    r: Request,
    engine_key: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_engine(engine_key), _rid(r), "engine_management")


@router.put("/{engine_key}")
async def update_engine(
    r: Request,
    engine_key: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).update_engine(engine_key, body), _rid(r), "engine_management")


@router.post("/{engine_key}/impact-preview")
async def impact_preview(
    r: Request,
    engine_key: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_impact_preview(engine_key, body.get("action", "disable")),
              _rid(r), "engine_management")


@router.post("/{engine_key}/enable")
async def enable_engine(
    r: Request,
    engine_key: str,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).enable_engine(engine_key, body.get("reason", "")),
              _rid(r), "engine_management")


@router.post("/{engine_key}/disable")
async def disable_engine(
    r: Request,
    engine_key: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).disable_engine(engine_key, body.get("reason", "")),
              _rid(r), "engine_management")


@router.post("/{engine_key}/health/check")
async def run_health_check(
    r: Request,
    engine_key: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).run_health_check(engine_key), _rid(r), "engine_management")


@router.get("/{engine_key}/health")
async def get_engine_health(
    r: Request,
    engine_key: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    from sqlalchemy import select
    from app.engines.engine_mgmt.models import EngineHealthCheck
    rows = (await db.execute(
        select(EngineHealthCheck).where(
            EngineHealthCheck.engine_key == engine_key
        ).order_by(EngineHealthCheck.checked_at.desc()).limit(limit)
    )).scalars().all()
    return ok({"history": [row.to_dict() for row in rows], "total": len(rows)},
              _rid(r), "engine_management")


@router.get("/{engine_key}/permissions")
async def get_engine_permissions(
    r: Request,
    engine_key: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_super_admin),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_permissions(engine_key=engine_key),
              _rid(r), "engine_management")
