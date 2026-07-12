"""Sprint 4 — Admin Tenant Router.

All endpoints under /v1/admin/tenants/.
Write endpoints require super_admin role.
Read endpoints require authenticated user (super_admin or internal tools).
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth import require_super_admin, get_current_user, UserContext
from app.engines.tenant_engine.admin_service import AdminTenantService
from app.exceptions import ServiceOSException, NotFoundException

router = APIRouter(prefix="/v1/admin/tenants", tags=["Admin: Tenants"])


def _svc(db: AsyncSession, request: Request, user: UserContext | None = None) -> AdminTenantService:
    actor_id = uuid.UUID(user.user_id) if user and user.user_id else None
    actor_role = user.role if user else None
    ip = request.client.host if request.client else None
    return AdminTenantService(
        db=db,
        request_id=request.headers.get("X-Request-ID", "—"),
        actor_id=actor_id,
        actor_role=actor_role,
        ip_address=ip,
    )


# ═══════════════════════════════════════════════════════════════
# PHASE 2 — ATOMIC ONBOARDING
# ═══════════════════════════════════════════════════════════════

from app.schemas.base import ok, ApiResponse  # noqa: E402 — needed before route definitions


def _rid(r: Request) -> str:
    return r.headers.get("X-Request-ID", getattr(r.state, "request_id", "—"))


# ═══════════════════════════════════════════════════════════════
# ENTERPRISE — SUMMARY + INSIGHTS
# ═══════════════════════════════════════════════════════════════

@router.get("/summary")
async def get_tenants_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    """Summary counts for KPI cards (delegates to provider portal summary SQL)."""
    from sqlalchemy import text
    rid = _rid(request)
    row = (await db.execute(text("""
        WITH pkg_latest AS (
            SELECT DISTINCT ON (tenant_id) tenant_id, status AS pkg_status
            FROM tenant_package_assignments WHERE deleted_at IS NULL
            ORDER BY tenant_id, created_at DESC
        )
        SELECT
            COUNT(*)                                                         AS total,
            SUM(CASE WHEN t.status='active' AND t.verification_status IN ('approved','verified') THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN t.status='suspended'                            THEN 1 ELSE 0 END) AS suspended,
            SUM(CASE WHEN t.verification_status='not_started' AND t.status NOT IN ('suspended','rejected') THEN 1 ELSE 0 END) AS pending_setup,
            SUM(CASE WHEN t.verification_status IN ('pending','under_review') THEN 1 ELSE 0 END) AS pending_review,
            SUM(CASE WHEN t.verification_status='changes_requested'       THEN 1 ELSE 0 END) AS changes_requested,
            SUM(CASE WHEN t.verification_status='rejected' OR t.status='rejected' THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN lp.pkg_status IN ('selected','paid_pending_approval') THEN 1 ELSE 0 END) AS package_pending_approval
        FROM tenants t
        LEFT JOIN pkg_latest lp ON lp.tenant_id = t.id
        WHERE t.terminated_at IS NULL AND t.archived_at IS NULL
    """))).fetchone()
    return ok({
        "total": int(row[0] or 0), "active": int(row[1] or 0),
        "suspended": int(row[2] or 0), "pending_setup": int(row[3] or 0),
        "pending_review": int(row[4] or 0), "changes_requested": int(row[5] or 0),
        "rejected": int(row[6] or 0), "package_pending_approval": int(row[7] or 0),
    }, rid)


@router.get("/insights")
async def get_tenants_insights(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    """All insight panels: verification overview, plan distribution, top locations, health, finance, activity."""
    svc = _svc(db, request, user)
    return ok(await svc.get_insights(), _rid(request))


@router.get("/export")
async def export_tenants(
    request: Request,
    status: str | None = Query(None),
    verification_status: str | None = Query(None),
    plan_type: str | None = Query(None),
    state: str | None = Query(None),
    city: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    from fastapi.responses import StreamingResponse
    svc = _svc(db, request, user)
    csv_text = await svc.export_tenants_csv({
        k: v for k, v in {
            "status": status, "verification_status": verification_status,
            "plan_type": plan_type, "state": state, "city": city, "search": search,
        }.items() if v is not None
    })
    return StreamingResponse(
        iter([csv_text]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tenants_export.csv"},
    )


@router.post("/onboard", status_code=201)
async def onboard_tenant(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    """Atomically onboard a new tenant with owner user, wallet, and security deposit."""
    svc = _svc(db, request, user)
    return await svc.onboard_tenant(payload)


# ═══════════════════════════════════════════════════════════════
# PHASE 3 — TENANT CRUD
# ═══════════════════════════════════════════════════════════════

@router.get("")
async def list_tenants(
    request: Request,
    # Pagination
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(25, ge=1, le=100, description="Records per page (max 100)"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_direction: str = Query("desc", pattern="^(asc|desc)$"),
    # Search
    search: str | None = Query(None, description="Search name, email, phone, code, slug"),
    # Status filters
    status: str | None = Query(None),
    verification_status: str | None = Query(None),
    plan_type: str | None = Query(None),
    # Location filters
    state: str | None = Query(None, description="State name (partial match)"),
    district: str | None = Query(None, description="District name (partial match)"),
    city: str | None = Query(None, description="City name (partial match)"),
    city_tier: str | None = Query(None, description="City tier: small|mid|large|metro"),
    zipcode: str | None = Query(None),
    # Other filters
    category_id: str | None = Query(None),
    created_from: str | None = Query(None, description="ISO date string"),
    created_to: str | None = Query(None, description="ISO date string"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    """
    Server-side paginated tenant list.
    Supports full-text search, location cascade filters, status filters, date range, sorting.
    """
    svc = _svc(db, request, user)
    filters = {k: v for k, v in {
        "page": page, "page_size": page_size,
        "sort_by": sort_by, "sort_direction": sort_direction,
        "search": search, "status": status,
        "verification_status": verification_status, "plan_type": plan_type,
        "state": state, "district": district, "city": city,
        "city_tier": city_tier, "zipcode": zipcode,
        "category_id": category_id,
        "created_from": created_from, "created_to": created_to,
    }.items() if v is not None}
    return ok(await svc.list_tenants(filters), _rid(request))


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.get_tenant(tenant_id)


@router.patch("/{tenant_id}")
async def update_tenant(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.update_tenant(tenant_id, payload)


# ── Lifecycle ──────────────────────────────────────────────────

@router.post("/{tenant_id}/verify")
async def verify_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.verify_tenant(tenant_id)


@router.post("/{tenant_id}/reject-verification")
async def reject_verification(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    reason = payload.get("reason", "")
    svc = _svc(db, request, user)
    return await svc.reject_verification(tenant_id, reason)


@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.activate_tenant(tenant_id)


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    reason = payload.get("reason", "No reason provided")
    svc = _svc(db, request, user)
    return await svc.suspend_tenant(tenant_id, reason)


@router.post("/{tenant_id}/notes")
async def add_admin_note(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    note = payload.get("note", "")
    svc = _svc(db, request, user)
    return await svc.add_admin_note(tenant_id, note)


@router.post("/{tenant_id}/archive")
async def archive_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.archive_tenant(tenant_id)


# ═══════════════════════════════════════════════════════════════
# PHASE 5 — OVERVIEW
# ═══════════════════════════════════════════════════════════════

@router.post("/{tenant_id}/reactivate")
async def reactivate_tenant(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    svc = _svc(db, request, user)
    return ok(await svc.reactivate_tenant(tenant_id, reason=payload.get("reason", "")), _rid(request))


@router.post("/{tenant_id}/request-changes")
async def request_changes(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    reason = str(payload.get("reason", "")).strip()
    if not reason:
        raise HTTPException(status_code=422, detail="reason is required")
    svc = _svc(db, request, user)
    return ok(await svc.request_changes(tenant_id, reason), _rid(request))


@router.post("/{tenant_id}/add-usage-credits")
async def add_usage_credits(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    """FINAL-L5-05J CANONICAL_ADAPTER: delegates to UsageCreditService
    instead of AdminTenantService.add_usage_credits, which mutated
    tenant_billing.credit_balance with zero usage_credit_ledger row
    (FINAL-L5-05I, L5-05I finding on rule 14 "ledger evidence" gap).
    idempotency_key is optional for backward compatibility with existing
    frontend callers that predate this fix; a server-generated key is used
    when the client does not supply one, so repeated legacy calls without a
    key are still each individually valid mutations (not deduplicated) —
    callers that want dedup must pass idempotency_key explicitly."""
    import uuid as _uuid
    from decimal import Decimal
    from app.engines.usage_credits.service import UsageCreditService

    amount = payload.get("amount", 0)
    reason = str(payload.get("reason", "")).strip()
    if not reason:
        raise HTTPException(status_code=422, detail="reason is required")
    try:
        amount = Decimal(str(amount))
    except Exception:
        raise HTTPException(status_code=422, detail="amount must be a number")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")

    idem_key = payload.get("idempotency_key") or f"legacy-add-usage-credits:{_uuid.uuid4()}"
    svc = UsageCreditService(
        db, actor_id=uuid.UUID(user.user_id) if user.user_id else None,
        actor_role=user.role, request_id=_rid(request),
        actor_ip=request.client.host if request.client else None,
    )
    result = await svc.adjust_credit(
        tenant_id=tenant_id, direction="credit", amount=amount,
        reason_code="manual_operational_adjustment", reason=reason,
        idempotency_key=idem_key,
    )
    await db.commit()
    return ok({"new_balance": result["balance_after"], **result}, _rid(request))


# HS9 — usage credit ledger, real deduction/credit history for a tenant.
@router.get("/{tenant_id}/usage-credit-ledger")
async def get_usage_credit_ledger(
    tenant_id: uuid.UUID,
    request: Request,
    job_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    from sqlalchemy import select
    from app.engines.tenant_engine.models import UsageCreditLedger
    q = select(UsageCreditLedger).where(UsageCreditLedger.tenant_id == tenant_id)
    if job_id:
        q = q.where(UsageCreditLedger.job_id == job_id)
    q = q.order_by(UsageCreditLedger.created_at.desc()).limit(200)
    res = await db.execute(q)
    entries = [e.to_dict() for e in res.scalars().all()]
    return ok({"tenant_id": str(tenant_id), "job_id": str(job_id) if job_id else None,
               "entries": entries, "count": len(entries)}, _rid(request))


@router.post("/{tenant_id}/change-plan")
async def change_plan(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    new_plan = str(payload.get("plan", "")).strip()
    reason = str(payload.get("reason", "")).strip()
    if not new_plan:
        raise HTTPException(status_code=422, detail="plan is required")
    if not reason:
        raise HTTPException(status_code=422, detail="reason is required")
    svc = _svc(db, request, user)
    return ok(await svc.change_plan(tenant_id, new_plan, reason), _rid(request))


@router.post("/{tenant_id}/send-notification")
async def send_notification(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> ApiResponse[dict]:
    message = str(payload.get("message", "")).strip()
    subject = str(payload.get("subject", "")).strip()
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    svc = _svc(db, request, user)
    return ok(await svc.send_notification(tenant_id, message, subject), _rid(request))


@router.get("/{tenant_id}/overview")
async def get_overview(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.get_overview(tenant_id)


# ── Settings ───────────────────────────────────────────────────

@router.get("/{tenant_id}/settings")
async def get_settings(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.get_settings(tenant_id)


@router.patch("/{tenant_id}/settings")
async def update_settings(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.update_settings(tenant_id, payload)


# ═══════════════════════════════════════════════════════════════
# PHASE 6 — USERS
# ═══════════════════════════════════════════════════════════════

@router.get("/{tenant_id}/users")
async def list_users(
    tenant_id: uuid.UUID,
    request: Request,
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.list_users(tenant_id, search=search)


@router.post("/{tenant_id}/users", status_code=201)
async def create_user(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.create_user(tenant_id, payload)


@router.patch("/{tenant_id}/users/{user_id}")
async def update_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.update_user(tenant_id, user_id, payload)


@router.post("/{tenant_id}/users/{user_id}/activate")
async def activate_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.activate_user(tenant_id, user_id)


@router.post("/{tenant_id}/users/{user_id}/suspend")
async def suspend_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.suspend_user(tenant_id, user_id)


@router.post("/{tenant_id}/users/{user_id}/reset-password")
async def reset_user_password(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.reset_user_password(tenant_id, user_id)


# ═══════════════════════════════════════════════════════════════
# PHASE 7 — STAFF
# ═══════════════════════════════════════════════════════════════

@router.get("/{tenant_id}/staff")
async def list_staff(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.list_staff(tenant_id)


@router.post("/{tenant_id}/staff", status_code=201)
async def create_staff(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.create_staff(tenant_id, payload)


@router.patch("/{tenant_id}/staff/{staff_id}")
async def update_staff(
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.update_staff(tenant_id, staff_id, payload)


@router.post("/{tenant_id}/staff/{staff_id}/activate")
async def activate_staff(
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.activate_staff(tenant_id, staff_id)


@router.post("/{tenant_id}/staff/{staff_id}/deactivate")
async def deactivate_staff(
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.deactivate_staff(tenant_id, staff_id)


@router.post("/{tenant_id}/staff/{staff_id}/reset-password")
async def reset_staff_password(
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.reset_staff_password(tenant_id, staff_id)


@router.patch("/{tenant_id}/staff/{staff_id}/photo")
async def update_staff_photo(
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    photo_url = payload.get("photo_url", "")
    if not photo_url:
        raise HTTPException(status_code=422, detail="photo_url is required")
    svc = _svc(db, request, user)
    return await svc.update_staff_photo(tenant_id, staff_id, photo_url)


# ═══════════════════════════════════════════════════════════════
# PHASE 8 — SERVICE AREAS
# ═══════════════════════════════════════════════════════════════

@router.get("/{tenant_id}/service-areas")
async def list_service_areas(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.list_service_areas(tenant_id)


@router.post("/{tenant_id}/service-areas", status_code=201)
async def create_service_area(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.create_service_area(tenant_id, payload)


@router.patch("/{tenant_id}/service-areas/{area_id}")
async def update_service_area(
    tenant_id: uuid.UUID,
    area_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.update_service_area(tenant_id, area_id, payload)


@router.delete("/{tenant_id}/service-areas/{area_id}")
async def delete_service_area(
    tenant_id: uuid.UUID,
    area_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.delete_service_area(tenant_id, area_id)


# ═══════════════════════════════════════════════════════════════
# PHASE 11 — SECURITY DEPOSIT + CREDIT WALLET
# ═══════════════════════════════════════════════════════════════

# NOTE: GET /{tenant_id}/security-deposit and POST .../security-deposit/mark-paid
# were removed from here (Phase 4 finance certification) — they were shadowing
# the canonical, permission-gated, audited, envelope-wrapped implementations in
# app/engines/package_commerce/admin_router.py (same paths, registered later,
# never reachable while these existed). See PHASE_4_FINANCE_BUG_FIX_REPORT.md.

@router.get("/{tenant_id}/wallet")
async def get_credit_wallet(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.get_credit_wallet(tenant_id)


@router.get("/{tenant_id}/wallet/ledger")
async def get_credit_ledger(
    tenant_id: uuid.UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.get_credit_ledger(tenant_id, limit=limit)


@router.post("/{tenant_id}/wallet/topup")
async def credit_topup(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    """FINAL-L5-05J DEPRECATED_410: this wrote TenantWallet directly (no
    row lock, no idempotency key) and had zero frontend callers (confirmed
    via FINAL-L5-05I/05J grep of frontend/super-admin). Canonical Usage
    Credit adjustments now go through POST /v1/admin/usage-credits/{tenant_id}/adjustments
    (or the pre-existing, now-fixed POST /{tenant_id}/add-usage-credits adapter)."""
    raise HTTPException(status_code=410, detail=(
        "This endpoint is deprecated and blocked. Use "
        "POST /v1/admin/usage-credits/{tenant_id}/adjustments."
    ))


@router.post("/{tenant_id}/wallet/adjust")
async def credit_adjust(
    tenant_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    """FINAL-L5-05J DEPRECATED_410: see credit_topup above — same finding,
    zero frontend callers, wrote TenantWallet with no lock/idempotency."""
    raise HTTPException(status_code=410, detail=(
        "This endpoint is deprecated and blocked. Use "
        "POST /v1/admin/usage-credits/{tenant_id}/adjustments."
    ))


# ═══════════════════════════════════════════════════════════════
# PHASE 13 — AUDIT LOG
# ═══════════════════════════════════════════════════════════════

@router.get("/{tenant_id}/audit-logs")
async def get_audit_logs(
    tenant_id: uuid.UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
) -> dict:
    svc = _svc(db, request, user)
    return await svc.get_audit_logs(tenant_id, limit=limit)


@router.get("/{tenant_id}/export")
async def export_tenant_report(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    from fastapi.responses import StreamingResponse
    svc = _svc(db, request, user)
    csv_text = await svc.export_tenant_report_csv(tenant_id)
    return StreamingResponse(
        iter([csv_text]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tenant_{tenant_id}_report.csv"},
    )


# ── Admin read-only views of provider portal data ────────────────────────────

@router.get("/{tenant_id}/offerings/enabled", summary="Admin view: provider enabled offerings")
async def admin_list_offerings(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    result = await db.execute(text("""
        SELECT peo.id as provider_enabled_offering_id,
               peo.offering_id,
               mo.name as offering_name,
               mo.offering_class as offering_type,
               peo.status,
               peo.readiness_status,
               peo.supported_type_ids,
               peo.supported_brand_ids,
               peo.supports_emergency,
               peo.provider_price_override,
               peo.readiness_blockers,
               peo.activated_at,
               peo.suspended_at,
               peo.suspension_reason,
               peo.is_enabled,
               peo.is_active,
               peo.created_at
        FROM provider_enabled_offerings peo
        JOIN master_offerings mo ON mo.id = peo.offering_id
        WHERE peo.tenant_id = :tid AND peo.deleted_at IS NULL
        ORDER BY mo.name
    """), {"tid": str(tenant_id)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"offerings": rows, "count": len(rows)}, _rid(request))


async def _fetch_offering_row(db: AsyncSession, tenant_id: uuid.UUID, offering_id: uuid.UUID) -> dict[str, Any]:
    result = await db.execute(text("""
        SELECT peo.id as provider_enabled_offering_id,
               peo.offering_id,
               mo.name as offering_name,
               mo.offering_class as offering_type,
               peo.status,
               peo.readiness_status,
               peo.supported_type_ids,
               peo.supported_brand_ids,
               peo.supports_emergency,
               peo.provider_price_override,
               peo.readiness_blockers,
               peo.activated_at,
               peo.suspended_at,
               peo.suspension_reason,
               peo.is_enabled,
               peo.is_active,
               peo.created_at
        FROM provider_enabled_offerings peo
        JOIN master_offerings mo ON mo.id = peo.offering_id
        WHERE peo.tenant_id = :tid AND peo.id = :oid AND peo.deleted_at IS NULL
    """), {"tid": str(tenant_id), "oid": str(offering_id)})
    row = result.fetchone()
    if row is None:
        raise NotFoundException("Enabled offering", str(offering_id), str(tenant_id))
    return dict(row._mapping)


@router.post("/{tenant_id}/offerings/enabled/{offering_id}/suspend", summary="Admin: suspend a provider offering")
async def admin_suspend_offering(
    tenant_id: uuid.UUID,
    offering_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    reason = (payload or {}).get("reason", "").strip()
    if not reason:
        raise ServiceOSException(
            error_code="VALIDATION_ERROR",
            detail="A reason is required to suspend an offering.",
            status_code=422,
        )
    await _fetch_offering_row(db, tenant_id, offering_id)
    await db.execute(text("""
        UPDATE provider_enabled_offerings
        SET status = 'suspended', is_active = false, suspended_at = now(),
            suspension_reason = :reason, updated_at = now()
        WHERE id = :oid AND tenant_id = :tid
    """), {"oid": str(offering_id), "tid": str(tenant_id), "reason": reason})
    await db.commit()
    row = await _fetch_offering_row(db, tenant_id, offering_id)
    return ok(row, _rid(request))


@router.post("/{tenant_id}/offerings/enabled/{offering_id}/reactivate", summary="Admin: reactivate a provider offering")
async def admin_reactivate_offering(
    tenant_id: uuid.UUID,
    offering_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    await _fetch_offering_row(db, tenant_id, offering_id)
    await db.execute(text("""
        UPDATE provider_enabled_offerings
        SET status = 'active', is_active = true, suspended_at = NULL,
            suspension_reason = NULL, updated_at = now()
        WHERE id = :oid AND tenant_id = :tid
    """), {"oid": str(offering_id), "tid": str(tenant_id)})
    await db.commit()
    row = await _fetch_offering_row(db, tenant_id, offering_id)
    return ok(row, _rid(request))


@router.post("/{tenant_id}/offerings/refresh-readiness", summary="Admin: refresh readiness for all provider offerings")
async def admin_refresh_offerings_readiness(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    result = await db.execute(text("""
        UPDATE provider_enabled_offerings
        SET readiness_status = CASE
                WHEN provider_price_override IS NOT NULL THEN 'ready'
                ELSE 'not_ready'
            END,
            updated_at = now()
        WHERE tenant_id = :tid AND deleted_at IS NULL
        RETURNING id
    """), {"tid": str(tenant_id)})
    refreshed = len(result.fetchall())
    await db.commit()
    return ok({"refreshed": refreshed}, _rid(request))


@router.get("/{tenant_id}/team-members", summary="Admin view: provider team members")
async def admin_list_team_members(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    result = await db.execute(text("""
        SELECT id as member_id, member_type, full_name, phone, email,
               designation, skills, can_receive_assignment, status, created_at
        FROM provider_team_members
        WHERE tenant_id = :tid AND deleted_at IS NULL
        ORDER BY created_at DESC
    """), {"tid": str(tenant_id)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"members": rows, "count": len(rows)}, _rid(request))


@router.get("/{tenant_id}/availability", summary="Admin view: provider availability rules")
async def admin_list_availability(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_super_admin),
):
    result = await db.execute(text("""
        SELECT id as availability_id, scope_type, scope_id, day_of_week,
               start_time, end_time, slot_duration_minutes,
               max_bookings_per_slot, is_active, created_at
        FROM provider_availability_rules
        WHERE tenant_id = :tid
        ORDER BY day_of_week, start_time
    """), {"tid": str(tenant_id)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"rules": rows, "count": len(rows)}, _rid(request))
