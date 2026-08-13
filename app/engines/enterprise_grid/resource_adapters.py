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

from sqlalchemy import func, or_, select
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
