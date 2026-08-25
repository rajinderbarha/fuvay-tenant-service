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

TenantService is one row per (tenant, master service, job type). Repair and
Installation therefore keep independent setup, pricing, publication, and
readiness while booking/jobs snapshot the exact published workflow version.
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
from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.engines.admin_catalog.models import (
    TenantService, MasterService, ServiceGroup, JobTypeDefinition,
    TenantServiceType, TenantServiceBrand,
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
    job_type_ids = {
        uuid.UUID(s["job_type_id"])
        for s in enabled
        if s.get("job_type_id")
    }
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

    # Resolve job type labels in one query. The earlier implementation made
    # one database round-trip per offering, which became increasingly slow as
    # a provider enabled more catalog entries.
    job_type_labels: dict[str, str] = {}
    if job_type_ids:
        rows = (await db.execute(
            select(JobTypeDefinition.id, JobTypeDefinition.label).where(
                JobTypeDefinition.id.in_(job_type_ids)
            )
        )).all()
        job_type_labels = {str(job_type_id): label for job_type_id, label in rows}

    tree: dict[str, dict] = {}
    published = draft = missing_pricing = 0
    dimension_pricing_service_ids: list[uuid.UUID] = []
    for s in enabled:
        m = master_rows.get(s["master_service_id"])
        group_key = str(m.service_group_id) if m and m.service_group_id else "ungrouped"
        group_label = group_names.get(group_key, "Other")
        tree.setdefault(group_key, {"service_group_id": group_key, "name": group_label, "services": []})

        if s["setup_status"] == "published":
            published += 1
        else:
            draft += 1
        tenant_service_id = uuid.UUID(s["tenant_service_id"])
        validation = await svc.validate_for_publish(tenant_service_id)
        pricing_error_codes = {
            "MISSING_TENANT_PRICE", "MISSING_VISIT_FEE", "MISSING_CONSULTATION_FEE",
            "INCOMPLETE_TYPE_PRICE_OVERRIDE", "INCOMPLETE_BRAND_PRICE_OVERRIDE",
        }
        has_missing_price = any(e["code"] in pricing_error_codes for e in validation["errors"])
        if has_missing_price:
            missing_pricing += 1

        blueprint = await svc._tenant_setup_blueprint(  # noqa: SLF001
            m, uuid.UUID(s["job_type_id"]) if s.get("job_type_id") else None
        ) if m else {}
        pricing_behavior = str(blueprint.get("pricing_behavior") or "").lower()
        is_inspection_pricing = pricing_behavior in {
            "inspection_required", "inspection_quote", "visit_fee_plus_quote", "quote", "custom_quote",
        }
        is_consultation = str(s.get("job_type") or "").lower() == "consultation"
        if not is_inspection_pricing and not is_consultation:
            dimension_pricing_service_ids.append(tenant_service_id)

        job_type_label = job_type_labels.get(str(s.get("job_type_id")))
        if not job_type_label and s.get("job_type"):
            job_type_label = s["job_type"].replace("_", " ").title()

        tree[group_key]["services"].append({
            "tenant_service_id": s["tenant_service_id"],
            "master_service_id": s["master_service_id"],
            "name": s["tenant_display_name"] or (m.service_name if m else "Service"),
            "job_type_label": job_type_label,
            "setup_status": s["setup_status"],
            "missing_pricing": has_missing_price,
            "readiness_ready": validation["valid"],
            "blocker_count": len(validation["errors"]),
            "customer_visible": s["setup_status"] == "published" and validation["valid"],
            "pricing_behavior": pricing_behavior or None,
        })

    # Price override KPIs count only offerings for which the active Admin
    # blueprint actually resolves type/brand prices. Historical repair
    # overrides are ignored because repair dimensions are routing-only.
    type_override_count = 0
    brand_override_count = 0
    if dimension_pricing_service_ids:
        type_override_count = await db.scalar(
            select(func.count()).select_from(TenantServiceType).where(
                TenantServiceType.tenant_id == tid,
                TenantServiceType.tenant_service_id.in_(dimension_pricing_service_ids),
                TenantServiceType.tenant_min_price.isnot(None),
            )
        ) or 0
        brand_override_count = await db.scalar(
            select(func.count()).select_from(TenantServiceBrand).where(
                TenantServiceBrand.tenant_id == tid,
                TenantServiceBrand.tenant_service_id.in_(dimension_pricing_service_ids),
                TenantServiceBrand.tenant_min_price.isnot(None),
            )
        ) or 0

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

    # Admin blueprint -- exact same job-type-specific requirements used by
    # Tenant Setup and its publish gate.
    blueprint = await svc._tenant_setup_blueprint(master, ts_row.job_type_id)  # noqa: SLF001
    job_type_label = await db.scalar(
        select(JobTypeDefinition.label).where(JobTypeDefinition.id == ts_row.job_type_id)
    )
    if not job_type_label and ts_row.job_type:
        job_type_label = ts_row.job_type.replace("_", " ").title()

    validation = await svc.validate_for_publish(tenant_service_id)
    types = (await svc.get_tenant_service_types(tenant_service_id))["types"]
    brands = (await svc.get_tenant_service_brands(tenant_service_id))["brands"]

    # Effective pricing tree: default, then real per-type / per-type+brand
    # rows that actually have an override, resolved through the SAME
    # resolve_tenant_price precedence used by validate_for_publish and the
    # real customer-facing price resolution -- one authority, not a second
    # calculation for display purposes.
    pricing_behavior = str(blueprint.get("pricing_behavior") or "").lower()
    is_inspection_pricing = pricing_behavior in {
        "inspection_required", "inspection_quote", "visit_fee_plus_quote", "quote", "custom_quote",
    }
    is_consultation = str(ts_row.job_type or "").lower() == "consultation"
    dimension_pricing_applies = not is_inspection_pricing and not is_consultation
    default_price = (
        await svc.resolve_tenant_price(tenant_service_id, None, None)
        if dimension_pricing_applies
        else {
            "resolved": False,
            "reason": "INSPECTION_ESTIMATE_WORKFLOW" if is_inspection_pricing else "PROVIDER_WIDE_CONSULTATION_FEE",
        }
    )
    type_pricing = []
    for t in types if dimension_pricing_applies else []:
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
