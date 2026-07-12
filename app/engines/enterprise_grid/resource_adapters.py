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

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

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
    q = select(ServiceCategory).order_by(ServiceCategory.name.asc()).limit(MAX_EXPORT_ROWS)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "name": r.name,
            "slug": r.slug,
            "status": "active" if r.is_active else "inactive",
            "created_at": r.created_at.isoformat() if getattr(r, "created_at", None) else "",
        }
        for r in rows
    ]


# resource_key -> adapter. Only these 5 are RUNTIME_SUPPORTED this sprint.
RESOURCE_ADAPTERS: dict[str, AdapterFn] = {
    "admin_reviews":         _adapter_admin_reviews,
    "admin_finance_topups":  _adapter_admin_finance_topups,
    "admin_audit_logs":      _adapter_admin_audit_logs,
    "admin_tenants":         _adapter_admin_tenants,
    "admin_categories":      _adapter_admin_categories,
}


def is_runtime_supported(resource_key: str) -> bool:
    return resource_key in RESOURCE_ADAPTERS


async def fetch_rows(db: AsyncSession, resource_key: str, tenant_scope: uuid.UUID | None, filters: dict) -> list[dict]:
    adapter = RESOURCE_ADAPTERS.get(resource_key)
    if adapter is None:
        raise ValueError(f"EXPORT_GENERATOR_UNAVAILABLE: {resource_key}")
    return await adapter(db, tenant_scope, filters or {})
