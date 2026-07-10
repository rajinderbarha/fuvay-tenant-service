"""Admin Booking Router — platform-wide booking management for super_admin.

ROOT-CAUSE FIX (2026-07-05):
  bookings table inherits ServiceOSBase (no SoftDeleteMixin) → no deleted_at column.
  tenants table also has no deleted_at column.
  Previous code filtered `b.deleted_at IS NULL` which caused a PG column-not-found error
  surfaced as "unexpected error" in the frontend. Fixed by removing those filters.

GET  /v1/admin/bookings             — list with rich filters + pagination
GET  /v1/admin/bookings/summary     — status/SLA counts
GET  /v1/admin/bookings/filters     — distinct categories, cities, states
GET  /v1/admin/bookings/export      — CSV download (same filters, max 5000)
GET  /v1/admin/bookings/tenant-search — async tenant/provider search for filter UX
GET  /v1/admin/bookings/{id}        — enriched booking detail
GET  /v1/admin/bookings/{id}/timeline — status history
GET  /v1/admin/bookings/{id}/notes  — booking notes
POST /v1/admin/bookings/{id}/cancel — admin cancel
POST /v1/admin/bookings/{id}/void   — admin void
"""
import csv
import io
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok

logger = structlog.get_logger("booking.admin_router")
router = APIRouter(prefix="/v1/admin/bookings", tags=["Admin Bookings"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── SQL backbone ──────────────────────────────────────────────────────────────
# NOTE: bookings has NO deleted_at — filter removed.
# NOTE: tenants has NO deleted_at — plain LEFT JOIN used.
# NOTE: users DOES have deleted_at — filter kept.

_JOINS = """
FROM bookings b
LEFT JOIN tenants t  ON t.id  = b.tenant_id
LEFT JOIN users u    ON u.id  = b.customer_id AND u.deleted_at IS NULL
LEFT JOIN master_services ms ON ms.id = b.service_id
LEFT JOIN jobs j     ON j.id  = COALESCE(b.job_id, b.converted_job_id)
"""

_SELECT_COLS = """
SELECT
    b.id,
    b.booking_number,
    b.tenant_id,
    COALESCE(t.business_name, t.tenant_name, '')       AS provider_name,
    COALESCE(t.business_name, t.tenant_name, '')       AS tenant_name,
    b.customer_id,
    COALESCE(u.full_name, '')                          AS customer_name,
    COALESCE(u.phone, '')                              AS customer_phone,
    b.service_category                                 AS category_name,
    COALESCE(ms.service_name, b.service_type_id, '')   AS service_name,
    b.service_type_id,
    b.service_id,
    b.status,
    COALESCE(j.status, '')                             AS job_status,
    COALESCE(j.assigned_staff_id::text, '')            AS assignment_status,
    b.quoted_price                                     AS estimated_amount,
    b.credit_applied                                   AS credit_applied,
    b.payable_amount                                   AS payable_amount,
    COALESCE(j.payment_id IS NOT NULL, FALSE)          AS payment_recorded,
    b.city,
    b.pincode                                          AS zipcode,
    COALESCE(b.address->>'state', '')                  AS state,
    COALESCE(b.address->>'district', '')               AS district,
    COALESCE(b.address->>'city_tier', '')              AS city_tier,
    b.created_at,
    b.scheduled_at,
    b.preferred_date,
    b.preferred_slot,
    COALESCE(b.job_id, b.converted_job_id)              AS job_id,
    b.cancelled_at,
    b.reschedule_count,
    b.job_type,
    COALESCE(j.sla_breached, FALSE)                    AS sla_breached
"""


def _row_to_dict(row) -> dict:
    assignment = "assigned" if (row.assignment_status and row.assignment_status != "") else "unassigned"
    return {
        "id":                str(row.id),
        "booking_number":    row.booking_number,
        "tenant_id":         str(row.tenant_id) if row.tenant_id else None,
        "tenant_name":       row.tenant_name or "",
        "provider_name":     row.provider_name or "",
        "customer_id":       str(row.customer_id) if row.customer_id else None,
        "customer_name":     row.customer_name or "",
        "customer_phone":    row.customer_phone or "",
        "category_name":     row.category_name or "",
        "service_name":      row.service_name or "",
        "service_type_id":   row.service_type_id or "",
        "status":            row.status,
        "job_status":        row.job_status or "",
        "assignment_status": assignment,
        "estimated_amount":  float(row.estimated_amount) if row.estimated_amount is not None else None,
        "credit_applied":    float(row.credit_applied) if row.credit_applied is not None else 0.0,
        "payable_amount":    float(row.payable_amount) if row.payable_amount is not None else (
                                 float(row.estimated_amount) if row.estimated_amount is not None else None),
        "payment_recorded":  bool(row.payment_recorded),
        "city":              row.city or "",
        "zipcode":           row.zipcode or "",
        "state":             row.state or "",
        "district":          row.district or "",
        "city_tier":         row.city_tier or "",
        "created_at":        row.created_at.isoformat() if row.created_at else None,
        "scheduled_at":      row.scheduled_at.isoformat() if row.scheduled_at else None,
        "preferred_date":    row.preferred_date,
        "preferred_slot":    row.preferred_slot,
        "job_id":            str(row.job_id) if row.job_id else None,
        "reschedule_count":  row.reschedule_count or 0,
        "job_type":          row.job_type or "",
        "sla_breached":      bool(row.sla_breached),
    }


_VALID_SORT = {
    "created_at", "scheduled_at", "estimated_amount",
    "status", "provider_name", "customer_name", "city",
}


def _build_filters(
    q:              Optional[str],
    tenant_id:      Optional[str],
    customer_id:    Optional[str],
    status:         Optional[str],
    category:       Optional[str],
    service_id:     Optional[str],
    city:           Optional[str],
    state:          Optional[str],
    district:       Optional[str],
    zipcode:        Optional[str],
    date_from:      Optional[str],
    date_to:        Optional[str],
    scheduled_from: Optional[str],
    scheduled_to:   Optional[str],
    amount_min:     Optional[float],
    amount_max:     Optional[float],
) -> tuple[list[str], dict]:
    conditions: list[str] = []
    params: dict = {}

    if q:
        conditions.append(
            "(b.booking_number ILIKE :q_like "
            "OR COALESCE(u.full_name, '') ILIKE :q_like "
            "OR COALESCE(u.phone, '') ILIKE :q_like "
            "OR COALESCE(t.business_name, t.tenant_name, '') ILIKE :q_like "
            "OR b.city ILIKE :q_like "
            "OR b.pincode ILIKE :q_like)"
        )
        params["q_like"] = f"%{q}%"

    if tenant_id:
        conditions.append("b.tenant_id = CAST(:tenant_id AS uuid)")
        params["tenant_id"] = tenant_id

    if customer_id:
        conditions.append("b.customer_id = CAST(:customer_id AS uuid)")
        params["customer_id"] = customer_id

    if status:
        conditions.append("b.status = :status")
        params["status"] = status

    if category:
        conditions.append("b.service_category ILIKE :cat_like")
        params["cat_like"] = f"%{category}%"

    if service_id:
        conditions.append("b.service_id = CAST(:service_id AS uuid)")
        params["service_id"] = service_id

    if city:
        conditions.append("b.city ILIKE :city_like")
        params["city_like"] = f"%{city}%"

    if state:
        conditions.append("b.address->>'state' ILIKE :state_like")
        params["state_like"] = f"%{state}%"

    if district:
        conditions.append("b.address->>'district' ILIKE :district_like")
        params["district_like"] = f"%{district}%"

    if zipcode:
        conditions.append("b.pincode = :zipcode")
        params["zipcode"] = zipcode

    if date_from:
        try:
            params["date_from"] = datetime.fromisoformat(date_from)
            conditions.append("b.created_at >= :date_from")
        except ValueError:
            pass

    if date_to:
        try:
            params["date_to"] = datetime.fromisoformat(date_to)
            conditions.append("b.created_at <= :date_to")
        except ValueError:
            pass

    if scheduled_from:
        try:
            params["sched_from"] = datetime.fromisoformat(scheduled_from)
            conditions.append("b.scheduled_at >= :sched_from")
        except ValueError:
            pass

    if scheduled_to:
        try:
            params["sched_to"] = datetime.fromisoformat(scheduled_to)
            conditions.append("b.scheduled_at <= :sched_to")
        except ValueError:
            pass

    if amount_min is not None:
        conditions.append("b.quoted_price >= :amt_min")
        params["amt_min"] = amount_min

    if amount_max is not None:
        conditions.append("b.quoted_price <= :amt_max")
        params["amt_max"] = amount_max

    return conditions, params


def _where(conditions: list[str]) -> str:
    return "WHERE " + " AND ".join(conditions) if conditions else ""


# ── Endpoints — fixed paths MUST precede /{booking_id} ───────────────────────

@router.get("/filters")
async def booking_filter_options(
    r:  Request,
    q:  Optional[str] = Query(None),
    u:  UserContext   = Depends(require_super_admin),
    db: AsyncSession  = Depends(get_db),
):
    """Return distinct values for category, city, state filter dropdowns."""
    cat_sql = text("""
        SELECT DISTINCT service_category AS name
        FROM bookings
        WHERE service_category IS NOT NULL AND service_category <> ''
        ORDER BY service_category LIMIT 200
    """)
    city_sql = text("""
        SELECT DISTINCT city AS name
        FROM bookings
        WHERE city IS NOT NULL AND city <> ''
        ORDER BY city LIMIT 200
    """)
    state_sql = text("""
        SELECT DISTINCT address->>'state' AS name
        FROM bookings
        WHERE address->>'state' IS NOT NULL AND address->>'state' <> ''
        ORDER BY 1 LIMIT 100
    """)
    cats   = (await db.execute(cat_sql)).fetchall()
    cities = (await db.execute(city_sql)).fetchall()
    states = (await db.execute(state_sql)).fetchall()
    return ok({
        "categories": [{"value": r.name, "label": r.name} for r in cats],
        "cities":     [{"value": r.name, "label": r.name} for r in cities],
        "states":     [{"value": r.name, "label": r.name} for r in states],
        "statuses": [
            {"value": "pending_confirmation", "label": "Pending Confirmation"},
            {"value": "confirmed",            "label": "Confirmed"},
            {"value": "in_progress",          "label": "In Progress"},
            {"value": "completed",            "label": "Completed"},
            {"value": "cancelled",            "label": "Cancelled"},
            {"value": "void",                 "label": "Void"},
            {"value": "draft",                "label": "Draft"},
        ],
    }, _rid(r), "booking")


@router.get("/summary")
async def booking_summary(
    r:  Request,
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    sql = text("""
        SELECT
            COUNT(*)                                                             AS total,
            COUNT(*) FILTER (WHERE DATE(b.created_at AT TIME ZONE 'UTC') = CURRENT_DATE) AS today,
            COUNT(*) FILTER (WHERE b.status = 'pending_confirmation')           AS pending_confirmation,
            COUNT(*) FILTER (WHERE b.status = 'confirmed')                      AS confirmed,
            COUNT(*) FILTER (WHERE b.status = 'in_progress')                    AS in_progress,
            COUNT(*) FILTER (WHERE b.scheduled_at IS NOT NULL AND b.status NOT IN ('completed','cancelled','void')) AS scheduled,
            COUNT(*) FILTER (WHERE b.status = 'completed')                      AS completed,
            COUNT(*) FILTER (WHERE b.status = 'cancelled')                      AS cancelled,
            COUNT(*) FILTER (WHERE b.status = 'void')                           AS voided,
            COUNT(*) FILTER (WHERE b.job_id IS NULL AND b.status IN ('confirmed','in_progress')) AS unassigned
        FROM bookings b
    """)
    # at_risk from jobs
    at_risk_sql = text("""
        SELECT COUNT(*) AS at_risk
        FROM jobs j
        WHERE j.sla_breached = TRUE AND j.status NOT IN ('completed','cancelled')
    """)
    row = (await db.execute(sql)).one()
    ar  = (await db.execute(at_risk_sql)).one()
    return ok({
        "total":                int(row.total),
        "today":                int(row.today),
        "pending_confirmation": int(row.pending_confirmation),
        "confirmed":            int(row.confirmed),
        "in_progress":          int(row.in_progress),
        "scheduled":            int(row.scheduled),
        "completed":            int(row.completed),
        "cancelled":            int(row.cancelled),
        "voided":               int(row.voided),
        "unassigned":           int(row.unassigned),
        "at_risk":              int(ar.at_risk),
    }, _rid(r), "booking")


@router.get("/tenant-search")
async def tenant_search(
    r:         Request,
    q:         Optional[str] = Query(None),
    page:      int           = Query(1, ge=1),
    page_size: int           = Query(20, ge=1, le=100),
    u:  UserContext   = Depends(require_super_admin),
    db: AsyncSession  = Depends(get_db),
):
    """Async tenant/provider search for filter UX autocomplete."""
    conditions = []
    params: dict = {}
    if q:
        conditions.append("(t.business_name ILIKE :q OR t.tenant_name ILIKE :q OR t.city ILIKE :q)")
        params["q"] = f"%{q}%"
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    offset = (page - 1) * page_size
    sql = text(f"""
        SELECT t.id, COALESCE(t.business_name, t.tenant_name, '') AS name, t.city
        FROM tenants t
        {where}
        ORDER BY name
        LIMIT :lim OFFSET :off
    """)
    rows = (await db.execute(sql, {**params, "lim": page_size, "off": offset})).fetchall()
    return ok({
        "tenants": [{"id": str(r.id), "name": r.name, "city": r.city or ""} for r in rows],
    }, _rid(r), "booking")


@router.get("/export")
async def export_bookings(
    r:              Request,
    q:              Optional[str]   = Query(None),
    tenant_id:      Optional[str]   = Query(None),
    customer_id:    Optional[str]   = Query(None),
    status:         Optional[str]   = Query(None),
    category:       Optional[str]   = Query(None),
    service_id:     Optional[str]   = Query(None),
    city:           Optional[str]   = Query(None),
    state:          Optional[str]   = Query(None),
    district:       Optional[str]   = Query(None),
    zipcode:        Optional[str]   = Query(None),
    date_from:      Optional[str]   = Query(None),
    date_to:        Optional[str]   = Query(None),
    scheduled_from: Optional[str]   = Query(None),
    scheduled_to:   Optional[str]   = Query(None),
    amount_min:     Optional[float] = Query(None),
    amount_max:     Optional[float] = Query(None),
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    conditions, params = _build_filters(
        q, tenant_id, customer_id, status, category, service_id,
        city, state, district, zipcode,
        date_from, date_to, scheduled_from, scheduled_to,
        amount_min, amount_max,
    )
    where = _where(conditions)
    params["limit"] = 5000

    sql = text(f"{_SELECT_COLS} {_JOINS} {where} ORDER BY b.created_at DESC LIMIT :limit")
    rows = (await db.execute(sql, params)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Booking #", "Provider", "Customer", "Phone",
        "Category", "Service", "Status", "Job Status", "Assignment",
        "Amount", "State", "City", "Zipcode",
        "Scheduled", "Created",
    ])
    for row in rows:
        writer.writerow([
            row.booking_number,
            row.tenant_name or "",
            row.customer_name or "",
            row.customer_phone or "",
            row.category_name or "",
            row.service_name or "",
            row.status,
            row.job_status or "",
            "assigned" if row.assignment_status else "unassigned",
            float(row.estimated_amount) if row.estimated_amount else "",
            row.state or "",
            row.city or "",
            row.zipcode or "",
            row.scheduled_at.isoformat() if row.scheduled_at else (row.preferred_date or ""),
            row.created_at.isoformat() if row.created_at else "",
        ])

    fname = f"bookings-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("")
async def list_admin_bookings(
    r:              Request,
    q:              Optional[str]   = Query(None),
    tenant_id:      Optional[str]   = Query(None),
    customer_id:    Optional[str]   = Query(None),
    status:         Optional[str]   = Query(None),
    category:       Optional[str]   = Query(None),
    service_id:     Optional[str]   = Query(None),
    city:           Optional[str]   = Query(None),
    state:          Optional[str]   = Query(None),
    district:       Optional[str]   = Query(None),
    zipcode:        Optional[str]   = Query(None),
    date_from:      Optional[str]   = Query(None),
    date_to:        Optional[str]   = Query(None),
    scheduled_from: Optional[str]   = Query(None),
    scheduled_to:   Optional[str]   = Query(None),
    amount_min:     Optional[float] = Query(None),
    amount_max:     Optional[float] = Query(None),
    sort_by:        str             = Query("created_at"),
    sort_dir:       str             = Query("desc"),
    page:           int             = Query(1,  ge=1),
    page_size:      int             = Query(25, ge=1, le=200),
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    conditions, params = _build_filters(
        q, tenant_id, customer_id, status, category, service_id,
        city, state, district, zipcode,
        date_from, date_to, scheduled_from, scheduled_to,
        amount_min, amount_max,
    )
    where  = _where(conditions)
    offset = (page - 1) * page_size

    # Validate sort params to prevent SQL injection
    col     = sort_by if sort_by in _VALID_SORT else "created_at"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    # Prefix with table alias for ambiguous cols
    _alias_map = {
        "provider_name": "t.business_name",
        "customer_name": "u.full_name",
        "city": "b.city",
        "estimated_amount": "b.quoted_price",
    }
    order_col = _alias_map.get(col, f"b.{col}")

    list_sql  = text(f"{_SELECT_COLS} {_JOINS} {where} ORDER BY {order_col} {direction} NULLS LAST LIMIT :limit OFFSET :offset")
    count_sql = text(f"SELECT COUNT(*) {_JOINS} {where}")

    rows  = (await db.execute(list_sql,  {**params, "limit": page_size, "offset": offset})).fetchall()
    total = (await db.execute(count_sql, params)).scalar() or 0

    return ok({
        "bookings": [_row_to_dict(r) for r in rows],
        "meta": {
            "page":        page,
            "page_size":   page_size,
            "total":       int(total),
            "total_pages": max(1, (int(total) + page_size - 1) // page_size),
        },
    }, _rid(r), "booking")


# ── Detail + sub-resources ────────────────────────────────────────────────────

@router.get("/{booking_id}/timeline")
async def get_booking_timeline(
    booking_id: str,
    r:  Request,
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    sql = text("""
        SELECT from_status, to_status, reason, created_at
        FROM booking_status_history
        WHERE booking_id = CAST(:bid AS uuid)
        ORDER BY created_at ASC
    """)
    rows = (await db.execute(sql, {"bid": booking_id})).fetchall()
    return ok({
        "timeline": [
            {
                "from_status": r.from_status,
                "to_status":   r.to_status,
                "reason":      r.reason,
                "occurred_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }, _rid(r), "booking")


@router.get("/{booking_id}/notes")
async def get_booking_notes(
    booking_id: str,
    r:  Request,
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    sql = text("""
        SELECT id, content, author_role, is_internal, created_at
        FROM booking_notes
        WHERE booking_id = CAST(:bid AS uuid)
        ORDER BY created_at ASC
    """)
    rows = (await db.execute(sql, {"bid": booking_id})).fetchall()
    return ok({
        "notes": [
            {
                "note_id":     str(r.id),
                "content":     r.content,
                "author_role": r.author_role,
                "is_internal": r.is_internal,
                "created_at":  r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }, _rid(r), "booking")


@router.get("/{booking_id}")
async def get_admin_booking(
    booking_id: str,
    r:  Request,
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    sql = text(f"""
        {_SELECT_COLS},
        b.customer_notes,
        b.internal_notes,
        b.cancellation_reason,
        b.blocking_reason,
        b.preflight_passed,
        b.address,
        b.converted_job_id,
        b.confirmed_at
        {_JOINS}
        WHERE b.id = CAST(:bid AS uuid)
    """)
    row = (await db.execute(sql, {"bid": booking_id})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")

    data = _row_to_dict(row)
    data.update({
        "customer_notes":      row.customer_notes,
        "internal_notes":      row.internal_notes,
        "cancellation_reason": row.cancellation_reason,
        "blocking_reason":     row.blocking_reason,
        "preflight_passed":    row.preflight_passed,
        "address":             row.address,
        "converted_job_id":    str(row.converted_job_id) if row.converted_job_id else None,
        "confirmed_at":        row.confirmed_at.isoformat() if row.confirmed_at else None,
    })
    return ok(data, _rid(r), "booking")


@router.post("/{booking_id}/cancel")
async def admin_cancel_booking(
    booking_id: str,
    r:  Request,
    body: dict      = Body(default={}),
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    reason = body.get("reason", "Cancelled by admin")
    check = await db.execute(text("SELECT id, status FROM bookings WHERE id = CAST(:bid AS uuid)"), {"bid": booking_id})
    row = check.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")
    if row.status in ("cancelled", "void", "completed"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a booking with status '{row.status}'")

    now = datetime.now(timezone.utc)
    await db.execute(text("""
        UPDATE bookings
        SET status = 'cancelled',
            cancellation_reason = :reason,
            cancelled_at = :now,
            cancelled_by_user_id = :uid
        WHERE id = CAST(:bid AS uuid)
    """), {"reason": reason, "now": now, "uid": u.user_id, "bid": booking_id})

    await db.execute(text("""
        INSERT INTO booking_status_history
            (id, booking_id, tenant_id, from_status, to_status, changed_by, changed_by_role, reason, created_at, updated_at)
        SELECT gen_random_uuid(), b.id, b.tenant_id, b.status, 'cancelled', CAST(:uid AS uuid), 'super_admin', :reason, :now, :now
        FROM bookings b WHERE b.id = CAST(:bid AS uuid)
    """), {"reason": reason, "now": now, "uid": str(u.user_id), "bid": booking_id})

    await db.commit()
    return ok({"cancelled": True}, _rid(r), "booking")


@router.post("/{booking_id}/void")
async def admin_void_booking(
    booking_id: str,
    r:  Request,
    body: dict      = Body(default={}),
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    reason = body.get("reason", "Voided by admin")
    check = await db.execute(text("SELECT id, status FROM bookings WHERE id = CAST(:bid AS uuid)"), {"bid": booking_id})
    row = check.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Booking not found")
    if row.status == "void":
        raise HTTPException(status_code=400, detail="Booking is already void")

    now = datetime.now(timezone.utc)
    await db.execute(text("""
        UPDATE bookings
        SET status = 'void',
            cancellation_reason = :reason,
            cancelled_at = :now
        WHERE id = CAST(:bid AS uuid)
    """), {"reason": reason, "now": now, "bid": booking_id})

    await db.execute(text("""
        INSERT INTO booking_status_history
            (id, booking_id, tenant_id, from_status, to_status, changed_by, changed_by_role, reason, created_at, updated_at)
        SELECT gen_random_uuid(), b.id, b.tenant_id, b.status, 'void', CAST(:uid AS uuid), 'super_admin', :reason, :now, :now
        FROM bookings b WHERE b.id = CAST(:bid AS uuid)
    """), {"reason": reason, "now": now, "uid": str(u.user_id), "bid": booking_id})

    await db.commit()
    return ok({"voided": True}, _rid(r), "booking")
