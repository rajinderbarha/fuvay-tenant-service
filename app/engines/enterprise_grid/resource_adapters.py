"""FINAL-L5-05S — Export resource adapter registry.

Maps a resource_key to a real, typed async query function that fetches
rows for that resource, scoped by the export job's authoritative
server-recorded tenant scope (never a client-controlled override).

Only resources with a real adapter here are RUNTIME_SUPPORTED -- every
other one of the 39 authorization-mapped resources (FINAL-L5-05R) remains
AUTHORIZATION_ONLY: it can be permission-checked but a job created against
it fails with EXPORT_GENERATOR_UNAVAILABLE rather than hanging PENDING
forever. This sprint deliberately implements exactly 5 representative
adapters -- one per required domain (Part 8's minimum candidate set) --
rather than all 39, which would require a full query-adapter design pass
per resource (many of the 39 have no matching real table columns for
their declared `allowed_export_fields`, a pre-existing Sprint 26 metadata
gap noted below, not something this sprint's bounded scope can fully
reconcile).

Each adapter returns `list[dict]` using the SAME field-name keys as
`EnterpriseFilterRegistry.get_allowed_export_fields(resource_key)` so the
existing `ExportService.generate_csv()` field-allowlist filtering works
unchanged. Field selection is bounded by `MAX_EXPORT_ROWS` per adapter
call -- callers must not load unbounded datasets into memory.
"""
from __future__ import annotations

import uuid
from typing import Awaitable, Callable

from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry

MAX_EXPORT_ROWS = 5000

AdapterFn = Callable[[AsyncSession, "uuid.UUID | None", dict], Awaitable[list[dict]]]


async def _adapter_admin_reviews(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.customer_reviews.models import CustomerReview
    q = select(CustomerReview).order_by(CustomerReview.created_at.desc()).limit(MAX_EXPORT_ROWS)
    if tenant_scope is not None:
        q = q.where(CustomerReview.tenant_id == tenant_scope)
    elif filters.get("tenant_id"):
        q = q.where(CustomerReview.tenant_id == uuid.UUID(str(filters["tenant_id"])))
    if filters.get("status"):
        q = q.where(CustomerReview.status == filters["status"])
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "review_number": r.review_number,
            "status": r.status,
            "overall_rating": r.overall_rating,
            "record_type": r.record_type,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


async def _adapter_admin_finance_topups(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.finance_hub.models import CreditTopupOrder
    from app.engines.tenant_engine.models import Tenant
    q = (
        select(CreditTopupOrder, Tenant.business_name)
        .join(Tenant, Tenant.id == CreditTopupOrder.tenant_id, isouter=True)
        .order_by(CreditTopupOrder.created_at.desc())
        .limit(MAX_EXPORT_ROWS)
    )
    if tenant_scope is not None:
        q = q.where(CreditTopupOrder.tenant_id == tenant_scope)
    elif filters.get("tenant_id"):
        q = q.where(CreditTopupOrder.tenant_id == uuid.UUID(str(filters["tenant_id"])))
    if filters.get("payment_status"):
        q = q.where(CreditTopupOrder.payment_status == filters["payment_status"])
    rows = (await db.execute(q)).all()
    return [
        {
            "tenant_name": business_name or "",
            "order_ref": order.order_ref or "",
            "credits_purchased": str(order.credits_purchased),
            "amount_paid": str(order.amount_paid),
            "payment_method": order.payment_method or "",
            "payment_status": order.payment_status,
            "wallet_credit_status": order.wallet_credit_status,
            "created_at": order.created_at.isoformat() if order.created_at else "",
        }
        for order, business_name in rows
    ]


async def _adapter_admin_audit_logs(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.security.models import PlatformAuditLog
    # NOTE: the Sprint 26 filter_registry config for "admin_audit_logs"
    # declares allowed_export_fields = ["event_type","record_type",
    # "actor_type","created_at"] -- none of those columns exist on the real
    # PlatformAuditLog model (which has operation/entity_type/actor_role
    # instead). This adapter maps to the real columns and aliases them to
    # the declared field names so the existing allowlist filter in
    # generate_csv() still works; documented as a pre-existing metadata
    # mismatch (bug register), not silently "fixed" by renaming the
    # registry (out of this sprint's bounded scope).
    q = select(PlatformAuditLog).order_by(PlatformAuditLog.created_at.desc()).limit(MAX_EXPORT_ROWS)
    if tenant_scope is not None:
        q = q.where(PlatformAuditLog.tenant_id == tenant_scope)
    elif filters.get("tenant_id"):
        q = q.where(PlatformAuditLog.tenant_id == uuid.UUID(str(filters["tenant_id"])))
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "event_type": r.operation,
            "record_type": r.entity_type or "",
            "actor_type": r.actor_role or "",
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


async def _adapter_admin_tenants(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.tenant_engine.models import Tenant
    q = select(Tenant).order_by(Tenant.created_at.desc()).limit(MAX_EXPORT_ROWS)
    if tenant_scope is not None:
        # admin_tenants is a platform-global resource; a non-None tenant_scope
        # here means a caller was scoped to a single tenant (should not
        # normally happen for a Tenant-Administration export, but enforced
        # defensively -- never trust absence of scope as "no restriction").
        q = q.where(Tenant.id == tenant_scope)
    if filters.get("status"):
        q = q.where(Tenant.status == filters["status"])
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(Tenant.business_name.ilike(term), Tenant.tenant_name.ilike(term),
                        Tenant.email.ilike(term), Tenant.phone.ilike(term), Tenant.tenant_code.ilike(term)))
    for key in ("vertical", "verification_status", "health_band"):
        if filters.get(key):
            q = q.where(getattr(Tenant, key) == filters[key])
    if filters.get("city"):
        q = q.where(Tenant.city.ilike(f"%{filters['city']}%"))
    if filters.get("state"):
        q = q.where(Tenant.state.ilike(f"%{filters['state']}%"))
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "business_name": r.business_name or "",
            "status": r.status,
            "contact_email": r.email or "",
            "subdomain": r.subdomain or "",
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


async def _adapter_admin_categories(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.admin_catalog.models import ServiceCategory
    # NOTE: Sprint 26's declared "status" field does not exist on
    # ServiceCategory (only boolean is_active) -- aliased below, same
    # documented-mismatch pattern as admin_audit_logs.
    q = select(ServiceCategory)
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(ServiceCategory.name.ilike(term), ServiceCategory.slug.ilike(term)))
    if filters.get("status") == "active":
        q = q.where(ServiceCategory.is_active.is_(True))
    elif filters.get("status") == "inactive":
        q = q.where(ServiceCategory.is_active.is_(False))
    for field in ("vertical_type", "finance_model", "customer_flow_type"):
        if filters.get(field):
            q = q.where(getattr(ServiceCategory, field) == filters[field])
    for field in ("is_customer_visible", "tenant_selectable", "pricing_supported"):
        filter_key = "customer_visible" if field == "is_customer_visible" else field
        value = _optional_bool(filters.get(filter_key))
        if value is not None:
            q = q.where(getattr(ServiceCategory, field) == value)
    q = q.order_by(ServiceCategory.display_order.asc(), ServiceCategory.id.asc()).limit(MAX_EXPORT_ROWS)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "name": r.name,
            "slug": r.slug,
            "status": "active" if r.is_active else "inactive",
            "vertical_type": r.vertical_type or "", "finance_model": r.finance_model or "",
            "customer_flow_type": r.customer_flow_type or "",
            "is_customer_visible": r.is_customer_visible, "tenant_selectable": r.tenant_selectable,
            "pricing_supported": r.pricing_supported, "display_order": r.display_order,
            "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else "",
            "updated_at": r.updated_at.isoformat() if getattr(r, "updated_at", None) else "",
        }
        for r in rows
    ]


async def _adapter_admin_service_groups(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.admin_catalog.models import ServiceCategory, ServiceGroup
    retired = _optional_bool(filters.get("retired")) is True
    q = (
        select(ServiceGroup, ServiceCategory.name)
        .join(ServiceCategory, ServiceCategory.id == ServiceGroup.category_id)
        .where(ServiceGroup.deleted_at.isnot(None) if retired else ServiceGroup.deleted_at.is_(None))
    )
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(ServiceGroup.name.ilike(term), ServiceGroup.code.ilike(term), ServiceGroup.slug.ilike(term)))
    if filters.get("status"):
        q = q.where(ServiceGroup.status == filters["status"])
    if filters.get("category_id"):
        q = q.where(ServiceGroup.category_id == uuid.UUID(str(filters["category_id"])))
    rows = (await db.execute(q.order_by(ServiceGroup.display_order, ServiceGroup.id).limit(MAX_EXPORT_ROWS))).all()
    return [{
        "name": row.name, "code": row.code, "slug": row.slug, "category_name": category_name,
        "status": row.status, "display_order": row.display_order,
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "deleted_at": row.deleted_at.isoformat() if row.deleted_at else "",
    } for row, category_name in rows]


async def _adapter_admin_master_services(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.admin_catalog.models import MasterService, ServiceCategory, ServiceGroup, TenantService
    retired = _optional_bool(filters.get("retired")) is True
    provider_exists = exists().where(
        TenantService.master_service_id == MasterService.id,
        TenantService.is_enabled.is_(True), TenantService.deleted_at.is_(None),
    )
    q = (
        select(MasterService, ServiceCategory.name, ServiceGroup.name)
        .outerjoin(ServiceCategory, ServiceCategory.id == MasterService.category_id)
        .outerjoin(ServiceGroup, ServiceGroup.id == MasterService.service_group_id)
        .where(MasterService.deleted_at.isnot(None) if retired else MasterService.deleted_at.is_(None))
    )
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(MasterService.service_name.ilike(term), MasterService.slug.ilike(term)))
    if filters.get("category_id"):
        q = q.where(MasterService.category_id == uuid.UUID(str(filters["category_id"])))
    if filters.get("service_group_id"):
        q = q.where(MasterService.service_group_id == uuid.UUID(str(filters["service_group_id"])))
    for field in ("job_type", "pricing_model"):
        if filters.get(field):
            q = q.where(getattr(MasterService, field) == filters[field])
    active = _optional_bool(filters.get("is_active"))
    if active is not None:
        q = q.where(MasterService.is_active == active)
    has_providers = _optional_bool(filters.get("has_providers"))
    if has_providers is not None:
        q = q.where(provider_exists if has_providers else ~provider_exists)
    rows = (await db.execute(q.order_by(MasterService.display_order, MasterService.service_name, MasterService.id).limit(MAX_EXPORT_ROWS))).all()
    return [{
        "name": row.service_name, "slug": row.slug, "category_name": category_name or "Missing category",
        "group_name": group_name or "", "job_type": row.job_type or "",
        "pricing_model": row.pricing_model or "", "status": "active" if row.is_active else "inactive",
        "display_order": row.display_order,
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "deleted_at": row.deleted_at.isoformat() if row.deleted_at else "",
    } for row, category_name, group_name in rows]


async def _adapter_admin_service_types(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.admin_catalog.models import ServiceType, ServiceTypeMapping
    mapping_count = (select(ServiceTypeMapping.type_id, func.count(ServiceTypeMapping.id).label("count"))
        .where(ServiceTypeMapping.status != "archived").group_by(ServiceTypeMapping.type_id).subquery())
    retired = _optional_bool(filters.get("retired")) is True
    q = (select(ServiceType, func.coalesce(mapping_count.c.count, 0))
         .outerjoin(mapping_count, mapping_count.c.type_id == ServiceType.id)
         .where(ServiceType.deleted_at.isnot(None) if retired else ServiceType.deleted_at.is_(None)))
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(ServiceType.name.ilike(term), ServiceType.code.ilike(term), ServiceType.slug.ilike(term)))
    for field in ("status", "type_family"):
        if filters.get(field): q = q.where(getattr(ServiceType, field) == filters[field])
    rows = (await db.execute(q.order_by(ServiceType.name, ServiceType.id).limit(MAX_EXPORT_ROWS))).all()
    return [{"name": row.name, "code": row.code, "slug": row.slug, "type_family": row.type_family or "",
             "status": row.status, "customer_visible": row.customer_visible, "mapping_count": int(count),
             "display_order": row.display_order, "created_at": row.created_at.isoformat() if row.created_at else "",
             "updated_at": row.updated_at.isoformat() if row.updated_at else "",
             "deleted_at": row.deleted_at.isoformat() if row.deleted_at else ""} for row, count in rows]


async def _adapter_admin_brands(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.admin_catalog.models import Brand, BrandCategoryMapping, MasterServiceBrand, TenantSupportedBrand
    svc = (select(MasterServiceBrand.brand_id, func.count(MasterServiceBrand.id).label("count"))
           .where(MasterServiceBrand.is_active.is_(True)).group_by(MasterServiceBrand.brand_id).subquery())
    cat = (select(BrandCategoryMapping.brand_id, func.count(BrandCategoryMapping.id).label("count"))
           .where(BrandCategoryMapping.status == "active", BrandCategoryMapping.deleted_at.is_(None))
           .group_by(BrandCategoryMapping.brand_id).subquery())
    usage = (select(TenantSupportedBrand.brand_id, func.count(TenantSupportedBrand.id).label("count"))
             .where(TenantSupportedBrand.status == "active").group_by(TenantSupportedBrand.brand_id).subquery())
    retired = _optional_bool(filters.get("retired")) is True
    q = (select(Brand, func.coalesce(svc.c.count, 0), func.coalesce(cat.c.count, 0), func.coalesce(usage.c.count, 0))
         .outerjoin(svc, svc.c.brand_id == Brand.id).outerjoin(cat, cat.c.brand_id == Brand.id)
         .outerjoin(usage, usage.c.brand_id == Brand.id)
         .where(Brand.deleted_at.isnot(None) if retired else Brand.deleted_at.is_(None)))
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"; q = q.where(or_(Brand.name.ilike(term), Brand.code.ilike(term), Brand.slug.ilike(term)))
    if filters.get("status"): q = q.where(Brand.status == filters["status"])
    rows = (await db.execute(q.order_by(Brand.display_order, Brand.name, Brand.id).limit(MAX_EXPORT_ROWS))).all()
    return [{"name": row.name, "code": row.code or "", "slug": row.slug, "status": row.status,
             "is_global": row.is_global, "service_mapping_count": int(sc), "category_mapping_count": int(cc),
             "provider_usage_count": int(pc), "display_order": row.display_order,
             "created_at": row.created_at.isoformat() if row.created_at else "", "updated_at": row.updated_at.isoformat() if row.updated_at else "",
             "deleted_at": row.deleted_at.isoformat() if row.deleted_at else ""} for row, sc, cc, pc in rows]


async def _adapter_admin_checklist_templates(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.checklist_catalog.models import ChecklistTemplate, ChecklistTemplateVersion, JobTypeChecklistMapping
    latest = (select(
        ChecklistTemplateVersion.checklist_template_id.label("template_id"),
        func.max(ChecklistTemplateVersion.version_number).label("version_number"),
    ).group_by(ChecklistTemplateVersion.checklist_template_id).subquery())
    latest_version = (select(ChecklistTemplateVersion)
        .join(latest, (latest.c.template_id == ChecklistTemplateVersion.checklist_template_id) &
              (latest.c.version_number == ChecklistTemplateVersion.version_number)).subquery())
    active_mapping_count = (select(
        ChecklistTemplateVersion.checklist_template_id.label("template_id"),
        func.count(JobTypeChecklistMapping.id).label("count"),
    ).join(JobTypeChecklistMapping, JobTypeChecklistMapping.checklist_template_version_id == ChecklistTemplateVersion.id)
     .where(JobTypeChecklistMapping.status == "active")
     .group_by(ChecklistTemplateVersion.checklist_template_id).subquery())
    q = (select(ChecklistTemplate, latest_version.c.version_number, latest_version.c.status,
                func.coalesce(active_mapping_count.c.count, 0))
         .outerjoin(latest_version, latest_version.c.checklist_template_id == ChecklistTemplate.id)
         .outerjoin(active_mapping_count, active_mapping_count.c.template_id == ChecklistTemplate.id))
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(ChecklistTemplate.name.ilike(term), ChecklistTemplate.code.ilike(term), ChecklistTemplate.description.ilike(term)))
    for field in ("status", "purpose", "owner_scope"):
        if filters.get(field):
            q = q.where(getattr(ChecklistTemplate, field) == filters[field])
    rows = (await db.execute(q.order_by(ChecklistTemplate.updated_at.desc(), ChecklistTemplate.id).limit(MAX_EXPORT_ROWS))).all()
    return [{
        "name": row.name, "code": row.code, "description": row.description or "", "purpose": row.purpose,
        "status": row.status, "owner_scope": row.owner_scope, "latest_version": version_number or "",
        "version_status": version_status or "", "active_mapping_count": int(mapping_count),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "archived_at": row.archived_at.isoformat() if row.archived_at else "",
        "archive_reason": row.archive_reason or "",
    } for row, version_number, version_status, mapping_count in rows]


async def _adapter_admin_checklist_mappings(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.admin_catalog.models import JobTypeDefinition, MasterService, MasterServiceJobType
    from app.engines.checklist_catalog.models import ChecklistTemplate, ChecklistTemplateVersion, JobTypeChecklistMapping
    q = (select(JobTypeChecklistMapping, ChecklistTemplate.name, ChecklistTemplate.code,
                ChecklistTemplateVersion.version_number, MasterService.service_name, JobTypeDefinition.label)
         .join(ChecklistTemplateVersion, ChecklistTemplateVersion.id == JobTypeChecklistMapping.checklist_template_version_id)
         .join(ChecklistTemplate, ChecklistTemplate.id == ChecklistTemplateVersion.checklist_template_id)
         .join(MasterServiceJobType, MasterServiceJobType.id == JobTypeChecklistMapping.master_service_job_type_id)
         .join(MasterService, MasterService.id == MasterServiceJobType.master_service_id)
         .join(JobTypeDefinition, JobTypeDefinition.id == MasterServiceJobType.job_type_id))
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(ChecklistTemplate.name.ilike(term), ChecklistTemplate.code.ilike(term),
                        MasterService.service_name.ilike(term), JobTypeDefinition.label.ilike(term),
                        JobTypeChecklistMapping.phase.ilike(term)))
    for field in ("status", "usage", "actor", "phase"):
        if filters.get(field):
            q = q.where(getattr(JobTypeChecklistMapping, field) == filters[field])
    rows = (await db.execute(q.order_by(JobTypeChecklistMapping.updated_at.desc(), JobTypeChecklistMapping.id).limit(MAX_EXPORT_ROWS))).all()
    return [{
        "template_name": template_name, "template_code": template_code, "template_version": version_number,
        "master_service_name": service_name, "job_type_label": job_type_label, "phase": row.phase,
        "usage": row.usage, "actor": row.actor, "completion_gate": row.completion_gate, "status": row.status,
        "effective_from": row.effective_from.isoformat() if row.effective_from else "",
        "effective_until": row.effective_until.isoformat() if row.effective_until else "",
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "disabled_at": row.disabled_at.isoformat() if row.disabled_at else "",
        "disable_reason": row.disable_reason or "",
    } for row, template_name, template_code, version_number, service_name, job_type_label in rows]


async def _adapter_admin_verticals(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.vertical_catalog.models import Vertical
    q = select(Vertical)
    search = filters.get("q") or filters.get("search")
    if search:
        term = f"%{search}%"
        q = q.where(or_(Vertical.label.ilike(term), Vertical.key.ilike(term), Vertical.slug.ilike(term)))
    if filters.get("status") == "enabled":
        q = q.where(Vertical.is_enabled.is_(True))
    elif filters.get("status") == "disabled":
        q = q.where(Vertical.is_enabled.is_(False))
    for field in ("finance_model", "lifecycle_status", "release_stage"):
        if filters.get(field):
            q = q.where(getattr(Vertical, field) == filters[field])
    for field in ("registration_allowed", "is_beta"):
        value = _optional_bool(filters.get(field))
        if value is not None:
            q = q.where(getattr(Vertical, field) == value)
    rows = (await db.execute(q.order_by(Vertical.sort_order.asc(), Vertical.id.asc()).limit(MAX_EXPORT_ROWS))).scalars().all()
    return [{
        "label": row.label, "key": row.key, "status": "enabled" if row.is_enabled else "disabled",
        "finance_model": row.finance_model or "", "lifecycle_status": row.lifecycle_status,
        "release_stage": row.release_stage, "registration_allowed": row.registration_allowed,
        "is_beta": row.is_beta, "sort_order": row.sort_order,
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    } for row in rows]


def _optional_bool(value):
    if value in (True, "true", "yes", "1", 1):
        return True
    if value in (False, "false", "no", "0", 0):
        return False
    return None


async def _adapter_admin_customers(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from sqlalchemy import text
    from app.engines.auth.admin_customers_router import _SELECT_COLS, _JOINS, _build_filters, _where_clause

    conditions, params = _build_filters(
        filters.get("q") or filters.get("search"), filters.get("tenant_id"),
        filters.get("health_band"), filters.get("engagement_status"), filters.get("city"),
        filters.get("state"), filters.get("zipcode"), _optional_bool(filters.get("has_complaints")),
        _optional_bool(filters.get("has_reviews")), filters.get("booking_count_min"),
        filters.get("booking_count_max"), filters.get("last_booking_from"), filters.get("last_booking_to"),
        filters.get("created_from"), filters.get("created_to"),
    )
    outer = []
    if filters.get("health_band"):
        outer.append("sq.health_band = :health_band")
        params["health_band"] = filters["health_band"]
    if filters.get("engagement_status") == "active":
        outer.append("sq.health_band IN ('healthy','active')")
    outer_sql = " AND " + " AND ".join(outer) if outer else ""
    rows = (await db.execute(text(f"""
        SELECT * FROM ({_SELECT_COLS} {_JOINS} {_where_clause(conditions)}) sq
        WHERE TRUE {outer_sql}
        ORDER BY sq.created_at DESC LIMIT {MAX_EXPORT_ROWS}
    """), params)).mappings().all()
    allowed = EnterpriseFilterRegistry.get_allowed_export_fields("admin_customers")
    return [{key: (value.isoformat() if hasattr(value, "isoformat") else value) for key, value in row.items() if key in allowed} for row in rows]


async def _adapter_admin_staff(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from sqlalchemy import text
    from app.engines.auth.admin_staff_router import _SELECT_COLS, _JOINS, _build_filters

    where, params = _build_filters(
        filters.get("q") or filters.get("search"), filters.get("tenant_id"), filters.get("role"),
        filters.get("availability_status"), _optional_bool(filters.get("is_active")),
        _optional_bool(filters.get("is_verified")), filters.get("city"), filters.get("job_count_min"),
        filters.get("job_count_max"), filters.get("rating_min"), filters.get("created_from"), filters.get("created_to"),
    )
    rows = (await db.execute(text(f"""
        SELECT {_SELECT_COLS} {_JOINS} WHERE {where}
        ORDER BY u.full_name LIMIT {MAX_EXPORT_ROWS}
    """), params)).mappings().all()
    allowed = EnterpriseFilterRegistry.get_allowed_export_fields("admin_staff")
    return [{key: (value.isoformat() if hasattr(value, "isoformat") else value) for key, value in row.items() if key in allowed} for row in rows]


async def _adapter_admin_complaints(db: AsyncSession, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    from app.engines.complaints.models import CustomerComplaint

    q = select(CustomerComplaint).order_by(CustomerComplaint.created_at.desc()).limit(MAX_EXPORT_ROWS)
    if filters.get("tenant_id"):
        q = q.where(CustomerComplaint.tenant_id == uuid.UUID(str(filters["tenant_id"])))
    for key in ("status", "priority", "severity", "sla_status", "record_type", "complaint_type"):
        value = filters.get(key)
        if value and hasattr(CustomerComplaint, key):
            q = q.where(getattr(CustomerComplaint, key) == value)
    rows = (await db.execute(q)).scalars().all()
    return [{
        "complaint_number": row.complaint_number, "status": row.status,
        "priority": row.priority, "complaint_type": row.complaint_type,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    } for row in rows]


# resource_key -> adapter. Only these 5 are RUNTIME_SUPPORTED this sprint.
RESOURCE_ADAPTERS: dict[str, AdapterFn] = {
    "admin_reviews":         _adapter_admin_reviews,
    "admin_finance_topups":  _adapter_admin_finance_topups,
    "admin_audit_logs":      _adapter_admin_audit_logs,
    "admin_tenants":         _adapter_admin_tenants,
    "admin_categories":      _adapter_admin_categories,
    "admin_service_groups":  _adapter_admin_service_groups,
    "admin_master_services": _adapter_admin_master_services,
    "admin_service_types": _adapter_admin_service_types,
    "admin_brands": _adapter_admin_brands,
    "admin_checklist_templates": _adapter_admin_checklist_templates,
    "admin_checklist_mappings": _adapter_admin_checklist_mappings,
    "admin_verticals":       _adapter_admin_verticals,
    "admin_customers":       _adapter_admin_customers,
    "admin_staff":           _adapter_admin_staff,
    "admin_complaints":      _adapter_admin_complaints,
}


def is_runtime_supported(resource_key: str) -> bool:
    return resource_key in RESOURCE_ADAPTERS


async def fetch_rows(db: AsyncSession, resource_key: str, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    adapter = RESOURCE_ADAPTERS.get(resource_key)
    if adapter is None:
        raise ValueError(f"EXPORT_GENERATOR_UNAVAILABLE: {resource_key}")
    return await adapter(db, tenant_scope, filters or {})
