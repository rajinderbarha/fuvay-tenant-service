"""TENANT-CATALOG-WORKSPACE — Services & Pricing 3-panel workspace projection.

Reuses TenantCatalogService (tenant_service.py) end-to-end -- this is a thin
read-side aggregator over its existing methods (list_home_services_enabled,
get_enabled_service, validate_for_publish, resolve_tenant_price,
get_tenant_service_types/brands) plus direct joins for type/brand pricing
display (same query pattern already proven in
home_service_assignment/team_directory_router.py::get_capabilities).

Does NOT introduce a second catalog/pricing engine. Ownership boundary
enforced throughout: tenant sets amounts only; type/brand mode, checklist,
technician/schedule/estimate requirements always come from
MasterService/ServiceJobWorkflow (admin-owned), never invented here.

Known architectural limitation (documented, not hidden): TenantService has
UniqueConstraint(tenant_id, master_service_id) -- NOT (..., job_type_id) --
so on the newer MasterServiceJobType hierarchy a tenant cannot yet have
independent rows per Job Type under one Master Service. This workspace is
built against the live, populated model (one MasterService row per job-type
flavor, e.g. "AC Repair" / "AC Installation" as distinct rows), which is
what real tenant data actually uses today. Fixing the constraint to also
support the newer per-Job-Type hierarchy is a separate, tracked follow-up.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.admin_catalog.tenant_service import TenantCatalogService, project_tenant_blueprint
from app.engines.admin_catalog.models import (
    TenantService, MasterService, ServiceGroup, JobTypeDefinition,
    ServiceJobWorkflow, TenantServiceType, TenantServiceBrand,
)

router = APIRouter(prefix="/v1/tenant/home-services/services", tags=["Tenant Home Services — Services & Pricing"])


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_REQUIRED", "This workspace requires a tenant-scoped session.", status_code=403)
    return uuid.UUID(str(user.tenant_id))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", None) or r.headers.get("X-Request-ID", "—")


def _svc(db: AsyncSession, user: UserContext) -> TenantCatalogService:
    return TenantCatalogService(
        db=db, request_id="—",
        actor_id=uuid.UUID(user.user_id) if user.user_id else None,
        actor_role=user.role, actor_tenant_id=_tid(user),
    )


@router.get("")
async def get_workspace(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    svc = _svc(db, user)
    enabled = (await svc.list_home_services_enabled())["services"]

    ts_ids = [uuid.UUID(s["tenant_service_id"]) for s in enabled]
    master_ids = {uuid.UUID(s["master_service_id"]) for s in enabled}
    master_rows = {}
    if master_ids:
        rows = (await db.execute(
            select(MasterService).where(MasterService.id.in_(master_ids))
        )).scalars().all()
        master_rows = {str(m.id): m for m in rows}

    group_ids = {m.service_group_id for m in master_rows.values() if m.service_group_id}
    group_names: dict[str, str] = {}
    if group_ids:
        rows = (await db.execute(select(ServiceGroup.id, ServiceGroup.name).where(ServiceGroup.id.in_(group_ids)))).all()
        group_names = {str(gid): name for gid, name in rows}

    type_override_count = await db.scalar(
        select(func.count()).select_from(TenantServiceType).where(
            TenantServiceType.tenant_id == tid, TenantServiceType.tenant_min_price.isnot(None),
        )
    ) or 0
    brand_override_count = await db.scalar(
        select(func.count()).select_from(TenantServiceBrand).where(
            TenantServiceBrand.tenant_id == tid, TenantServiceBrand.tenant_min_price.isnot(None),
        )
    ) or 0

    tree: dict[str, dict] = {}
    published = draft = missing_pricing = 0
    for s in enabled:
        m = master_rows.get(s["master_service_id"])
        group_key = str(m.service_group_id) if m and m.service_group_id else "ungrouped"
        group_label = group_names.get(group_key, "Other")
        tree.setdefault(group_key, {"service_group_id": group_key, "name": group_label, "services": []})

        if s["setup_status"] == "published":
            published += 1
        else:
            draft += 1
        validation = await svc.validate_for_publish(uuid.UUID(s["tenant_service_id"]))
        has_missing_price = any(e["code"] == "MISSING_TENANT_PRICE" for e in validation["errors"])
        if has_missing_price:
            missing_pricing += 1

        job_type_label = None
        if m and m.job_type_id:
            job_type_label = await db.scalar(select(JobTypeDefinition.label).where(JobTypeDefinition.id == m.job_type_id))
        elif s.get("job_type"):
            job_type_label = s["job_type"].replace("_", " ").title()

        tree[group_key]["services"].append({
            "tenant_service_id": s["tenant_service_id"],
            "master_service_id": s["master_service_id"],
            "name": s["tenant_display_name"] or (m.service_name if m else "Service"),
            "job_type_label": job_type_label,
            "setup_status": s["setup_status"],
            "missing_pricing": has_missing_price,
        })

    return ok({
        "summary": {
            "enabled_services": len(enabled),
            "published": published,
            "draft": draft,
            "missing_pricing": missing_pricing,
            "type_overrides": type_override_count,
            "brand_overrides": brand_override_count,
        },
        "catalog_tree": list(tree.values()),
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }, _rid(request), "admin_catalog")


@router.get("/{tenant_service_id}")
async def get_offering_detail(
    tenant_service_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    svc = _svc(db, user)
    ts_row = await db.get(TenantService, tenant_service_id)
    if not ts_row or ts_row.tenant_id != tid or ts_row.deleted_at is not None:
        raise ServiceOSException("SERVICE_NOT_FOUND", "Tenant service not found.", status_code=404)

    ts_dict = await svc.get_enabled_service(tenant_service_id)
    master = await db.get(MasterService, ts_row.master_service_id)

    job_type_label = None
    workflow = None
    # Older TenantService rows may not carry job_type_id even though their
    # MasterService does.  Setup reads the master row, so using only the
    # tenant row here made the dashboard silently fall back to legacy fields
    # for the very same offering.  Resolve one canonical job type for both.
    workflow_job_type_id = ts_row.job_type_id or (master.job_type_id if master else None)
    if workflow_job_type_id:
        job_type_label = await db.scalar(select(JobTypeDefinition.label).where(JobTypeDefinition.id == workflow_job_type_id))
        workflow_row = (await db.execute(
            select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == ts_row.master_service_id,
                ServiceJobWorkflow.job_type_id == workflow_job_type_id,
                ServiceJobWorkflow.is_current.is_(True),
                ServiceJobWorkflow.status == "published",
            ).order_by(ServiceJobWorkflow.version_number.desc())
        )).scalars().first()
        if workflow_row:
            workflow = workflow_row.to_dict()
    elif ts_row.job_type:
        job_type_label = ts_row.job_type.replace("_", " ").title()

    # Admin blueprint -- prefer the real per-(master_service, job_type)
    # ServiceJobWorkflow row when it exists; fall back to MasterService's own
    # scalar fields for tenants still on the legacy one-row-per-job-type
    # model (documented in this router's module docstring).
    blueprint = project_tenant_blueprint(master, workflow)

    validation = await svc.validate_for_publish(tenant_service_id)
    types = (await svc.get_tenant_service_types(tenant_service_id))["types"]
    brands = (await svc.get_tenant_service_brands(tenant_service_id))["brands"]

    # Effective pricing tree: default, then real per-type / per-type+brand
    # rows that actually have an override, resolved through the SAME
    # resolve_tenant_price precedence used by validate_for_publish and the
    # real customer-facing price resolution -- one authority, not a second
    # calculation for display purposes.
    default_price = await svc.resolve_tenant_price(tenant_service_id, None, None)
    type_pricing = []
    for t in types:
        resolved = await svc.resolve_tenant_price(tenant_service_id, uuid.UUID(t["service_type_id"]), None)
        brand_rows = (await db.execute(
            select(TenantServiceBrand, ).where(
                TenantServiceBrand.tenant_service_id == tenant_service_id,
                TenantServiceBrand.service_type_id == uuid.UUID(t["service_type_id"]),
                TenantServiceBrand.tenant_min_price.isnot(None),
            )
        )).scalars().all()
        brand_overrides = []
        for b in brand_rows:
            b_resolved = await svc.resolve_tenant_price(tenant_service_id, uuid.UUID(t["service_type_id"]), b.brand_id)
            brand_overrides.append({"brand_id": str(b.brand_id), **b_resolved})
        type_pricing.append({"service_type_id": t["service_type_id"], "name": t["name"], **resolved,
                              "brand_overrides": brand_overrides})

    return ok({
        "tenant_service": ts_dict,
        "service_name": master.service_name if master else ts_dict.get("tenant_display_name"),
        "job_type_label": job_type_label,
        "blueprint": blueprint,
        "readiness": {
            "ready": validation["valid"],
            "status": "ready" if validation["valid"] else ("draft" if ts_row.setup_status == "draft" else "incomplete"),
            "blockers": validation["errors"],
        },
        "types": types,
        "brands": brands,
        "effective_pricing": {
            "default": default_price,
            "by_type": type_pricing,
        },
    }, _rid(request), "admin_catalog")
