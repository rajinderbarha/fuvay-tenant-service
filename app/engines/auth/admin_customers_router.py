"""Admin Customers Router — platform-wide customer management.

GET /v1/admin/customers/filters    — distinct cities/states for dropdowns
GET /v1/admin/customers/summary    — platform-wide counts + health bands
GET /v1/admin/customers/export     — CSV (same filters, no page cap)
GET /v1/admin/customers            — paginated customer list with rich filters
GET /v1/admin/customers/{id}       — enriched customer detail
GET /v1/admin/customers/{id}/bookings — customer booking history
"""
import csv
import io
from datetime import datetime
from typing import Optional

import uuid

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.engines.auth.admin_customers_service import CustomerAdminService
from app.schemas.base import ok

logger = structlog.get_logger("auth.admin_customers_router")
router = APIRouter(prefix="/v1/admin/customers", tags=["Admin Customers"])
# Customer/provider remedy case details are intentionally not mounted for
# platform admins. Aggregate risk counts remain available for account-health
# oversight without giving the platform an adjudication workspace.
retired_case_router = APIRouter(prefix="/v1/admin/customers", include_in_schema=False)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.CUSTOMERS_READ))) -> CustomerAdminService:
    return CustomerAdminService(db=db, request_id=_rid(r),
                                 actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                                 actor_role=u.role, actor_ip=r.client.host if r.client else None)


# ── Health band SQL expression ────────────────────────────────────────────────
# Computed from booking aggregates at query time; no stored health_band column needed.
_HEALTH_BAND_EXPR = """
CASE
  WHEN u.is_active = FALSE THEN 'blocked'
  WHEN bk.total_bookings IS NULL OR bk.total_bookings = 0 THEN 'new'
  WHEN cc.complaints_count > 0
       AND bk.last_booking_at >= NOW() - INTERVAL '90 days' THEN 'complaint_risk'
  WHEN bk.last_booking_at < NOW() - INTERVAL '120 days' THEN 'dormant'
  WHEN bk.last_booking_at < NOW() - INTERVAL '60 days' THEN 'at_risk'
  WHEN bk.total_bookings >= 3
       AND bk.last_booking_at >= NOW() - INTERVAL '60 days'
       AND COALESCE(bk.cancelled_bookings, 0) * 1.0 / GREATEST(bk.total_bookings, 1) < 0.4 THEN 'healthy'
  WHEN bk.total_bookings >= 1
       AND bk.last_booking_at >= NOW() - INTERVAL '60 days' THEN 'active'
  ELSE 'at_risk'
END
"""

_SELECT_COLS = f"""
SELECT
    u.id                                                           AS id,
    u.full_name,
    u.phone,
    u.email,
    u.is_active,
    u.account_status,
    u.created_at,
    COALESCE(ca.city, '')                                          AS city,
    COALESCE(ca.district, '')                                      AS district,
    COALESCE(ca.state, '')                                         AS state,
    COALESCE(ca.zipcode, '')                                       AS zipcode,
    COALESCE(bk.total_bookings, 0)                                 AS total_bookings,
    COALESCE(bk.completed_bookings, 0)                             AS completed_bookings,
    COALESCE(bk.cancelled_bookings, 0)                             AS cancelled_bookings,
    bk.last_booking_at,
    bk.last_tenant_id,
    COALESCE(bk.tenant_count, 0)                                   AS tenant_count,
    COALESCE(t.business_name, t.tenant_name, '')                   AS last_tenant_name,
    COALESCE(cc.complaints_count, 0)                               AS complaints_count,
    COALESCE(cr.reviews_count, 0)                                  AS reviews_count,
    cr.average_rating,
    {_HEALTH_BAND_EXPR}                                            AS health_band
"""

_JOINS = """
FROM users u
LEFT JOIN LATERAL (
    SELECT
        COUNT(*)                                                   AS total_bookings,
        COUNT(*) FILTER (WHERE b2.status = 'completed')            AS completed_bookings,
        COUNT(*) FILTER (WHERE b2.status = 'cancelled')            AS cancelled_bookings,
        MAX(b2.created_at)                                         AS last_booking_at,
        COUNT(DISTINCT b2.tenant_id)                               AS tenant_count,
        (ARRAY_AGG(b2.tenant_id ORDER BY b2.created_at DESC))[1]  AS last_tenant_id
    FROM service_bookings b2
    WHERE b2.customer_id = u.id
) bk ON TRUE
LEFT JOIN LATERAL (
    SELECT city, district, state, zipcode
    FROM customer_addresses
    WHERE customer_id = u.id
    ORDER BY created_at DESC
    LIMIT 1
) ca ON TRUE
LEFT JOIN tenants t ON t.id = bk.last_tenant_id
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS complaints_count
    FROM customer_complaints cc2
    WHERE cc2.customer_id = u.id
      AND cc2.status NOT IN ('closed', 'cancelled', 'rejected', 'resolved', 'settled')
) cc ON TRUE
LEFT JOIN LATERAL (
    SELECT
        COUNT(*)            AS reviews_count,
        AVG(cr2.overall_rating) AS average_rating
    FROM customer_reviews cr2
    WHERE cr2.customer_id = u.id
) cr ON TRUE
WHERE u.role = 'customer' AND u.deleted_at IS NULL
"""


def _build_filters(
    q: Optional[str],
    tenant_id: Optional[str],
    health_band: Optional[str],
    engagement_status: Optional[str],
    city: Optional[str],
    state: Optional[str],
    zipcode: Optional[str],
    has_complaints: Optional[bool],
    has_reviews: Optional[bool],
    booking_count_min: Optional[int],
    booking_count_max: Optional[int],
    last_booking_from: Optional[str],
    last_booking_to: Optional[str],
    created_from: Optional[str],
    created_to: Optional[str],
) -> tuple[list[str], dict]:
    conditions: list[str] = []
    params: dict = {}

    if q:
        conditions.append(
            "(u.full_name ILIKE :q_like OR u.phone ILIKE :q_like OR u.email ILIKE :q_like)"
        )
        params["q_like"] = f"%{q}%"

    if tenant_id:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM service_bookings bfilt
                WHERE bfilt.customer_id = u.id
                  AND bfilt.tenant_id = :tenant_id ::uuid
            )
        """)
        params["tenant_id"] = tenant_id

    if city:
        conditions.append("ca.city ILIKE :city_like")
        params["city_like"] = f"%{city}%"

    if state:
        conditions.append("ca.state ILIKE :state_like")
        params["state_like"] = f"%{state}%"

    if zipcode:
        conditions.append("ca.zipcode = :zipcode")
        params["zipcode"] = zipcode

    if has_complaints is True:
        conditions.append("cc.complaints_count > 0")
    elif has_complaints is False:
        conditions.append("cc.complaints_count = 0")

    if has_reviews is True:
        conditions.append("cr.reviews_count > 0")

    if booking_count_min is not None:
        conditions.append("COALESCE(bk.total_bookings, 0) >= :bk_min")
        params["bk_min"] = booking_count_min

    if booking_count_max is not None:
        conditions.append("COALESCE(bk.total_bookings, 0) <= :bk_max")
        params["bk_max"] = booking_count_max

    if last_booking_from:
        try:
            params["lb_from"] = datetime.fromisoformat(last_booking_from)
            conditions.append("bk.last_booking_at >= :lb_from")
        except ValueError:
            pass

    if last_booking_to:
        try:
            params["lb_to"] = datetime.fromisoformat(last_booking_to)
            conditions.append("bk.last_booking_at <= :lb_to")
        except ValueError:
            pass

    if created_from:
        try:
            params["created_from"] = datetime.fromisoformat(created_from)
            conditions.append("u.created_at >= :created_from")
        except ValueError:
            pass

    if created_to:
        try:
            params["created_to"] = datetime.fromisoformat(created_to)
            conditions.append("u.created_at <= :created_to")
        except ValueError:
            pass

    # health_band and engagement_status applied as HAVING-like filter on the outer query
    return conditions, params


def _where_clause(conditions: list[str]) -> str:
    if not conditions:
        return ""
    return "AND " + " AND ".join(conditions)


def _row_to_dict(row) -> dict:
    return {
        "id":                 str(row.id),
        "full_name":          row.full_name or "",
        "phone":              row.phone or "",
        "email":              row.email or "",
        "is_active":          row.is_active,
        "account_status":     row.account_status or ("active" if row.is_active else "disabled"),
        "city":               row.city or "",
        "district":           row.district or "",
        "state":              row.state or "",
        "zipcode":            row.zipcode or "",
        "health_band":        row.health_band or "new",
        "total_bookings":     int(row.total_bookings),
        "completed_bookings": int(row.completed_bookings),
        "cancelled_bookings": int(row.cancelled_bookings),
        "complaints_count":   int(row.complaints_count),
        "reviews_count":      int(row.reviews_count),
        "average_rating":     float(row.average_rating) if row.average_rating else None,
        "tenant_count":       int(row.tenant_count),
        "last_tenant_name":   row.last_tenant_name or "",
        "last_booking_at":    row.last_booking_at.isoformat() if row.last_booking_at else None,
        "created_at":         row.created_at.isoformat() if row.created_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/filters")
async def customer_filter_options(
    r: Request,
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    city_sql = text("""
        SELECT DISTINCT city AS name
        FROM customer_addresses
        WHERE city IS NOT NULL AND city <> ''
        ORDER BY city LIMIT 200
    """)
    state_sql = text("""
        SELECT DISTINCT state AS name
        FROM customer_addresses
        WHERE state IS NOT NULL AND state <> ''
        ORDER BY state LIMIT 100
    """)
    cities  = (await db.execute(city_sql)).fetchall()
    states  = (await db.execute(state_sql)).fetchall()
    tenants = (await db.execute(text("""
        SELECT id, COALESCE(business_name, tenant_name) AS name
        FROM tenants
        WHERE COALESCE(business_name, tenant_name) IS NOT NULL
        ORDER BY COALESCE(business_name, tenant_name)
        LIMIT 500
    """))).fetchall()
    return ok({
        "cities":  [{"value": row.name, "label": row.name} for row in cities],
        "states":  [{"value": row.name, "label": row.name} for row in states],
        "tenants": [{"value": str(row.id), "label": row.name} for row in tenants],
    }, _rid(r), "customers")


@router.get("/summary")
async def customer_summary(
    r: Request,
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    sql = text(f"""
        SELECT
            COUNT(*)                                                          AS total,
            COUNT(*) FILTER (WHERE DATE(u.created_at AT TIME ZONE 'UTC') = CURRENT_DATE) AS today,
            COUNT(*) FILTER (WHERE ({_HEALTH_BAND_EXPR}) IN ('healthy','active'))         AS active,
            COUNT(*) FILTER (WHERE COALESCE(bk.total_bookings,0) >= 2)                   AS repeat_customers,
            COUNT(*) FILTER (WHERE ({_HEALTH_BAND_EXPR}) = 'at_risk')                    AS at_risk,
            COUNT(*) FILTER (WHERE ({_HEALTH_BAND_EXPR}) = 'dormant')                    AS dormant,
            COUNT(*) FILTER (WHERE cc.complaints_count > 0)                              AS has_complaints,
            AVG(cr.average_rating)                                                        AS avg_rating,
            COUNT(*) FILTER (WHERE ({_HEALTH_BAND_EXPR}) = 'new')                        AS new_customers,
            COUNT(*) FILTER (WHERE u.is_active = FALSE)                                  AS blocked
        {_JOINS}
    """)
    row = (await db.execute(sql)).one()
    total = int(row.total) or 1
    total_bk_sql = text("SELECT SUM(bk2.cnt) FROM (SELECT COUNT(*) AS cnt FROM service_bookings GROUP BY customer_id) bk2")
    total_bk = (await db.execute(total_bk_sql)).scalar() or 0
    return ok({
        "total":            int(row.total),
        "today":            int(row.today),
        "active":           int(row.active),
        "repeat_customers": int(row.repeat_customers),
        "at_risk":          int(row.at_risk),
        "dormant":          int(row.dormant),
        "has_complaints":   int(row.has_complaints),
        "new_customers":    int(row.new_customers),
        "blocked":          int(row.blocked),
        "avg_rating":       round(float(row.avg_rating), 2) if row.avg_rating else None,
        "bookings_per_customer": round(int(total_bk) / total, 1),
    }, _rid(r), "customers")


@router.get("/export")
async def export_customers(
    r: Request,
    q:                 Optional[str]  = Query(None),
    tenant_id:         Optional[str]  = Query(None),
    health_band:       Optional[str]  = Query(None),
    engagement_status: Optional[str]  = Query(None),
    city:              Optional[str]  = Query(None),
    state:             Optional[str]  = Query(None),
    zipcode:           Optional[str]  = Query(None),
    has_complaints:    Optional[bool] = Query(None),
    has_reviews:       Optional[bool] = Query(None),
    booking_count_min: Optional[int]  = Query(None),
    booking_count_max: Optional[int]  = Query(None),
    last_booking_from: Optional[str]  = Query(None),
    last_booking_to:   Optional[str]  = Query(None),
    created_from:      Optional[str]  = Query(None),
    created_to:        Optional[str]  = Query(None),
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    conditions, params = _build_filters(
        q, tenant_id, health_band, engagement_status, city, state, zipcode,
        has_complaints, has_reviews, booking_count_min, booking_count_max,
        last_booking_from, last_booking_to, created_from, created_to,
    )
    outer_conditions: list[str] = []
    if health_band:
        outer_conditions.append("sq.health_band = :health_band")
    if engagement_status == "active":
        outer_conditions.append("sq.health_band IN ('healthy', 'active')")
    hb_cond = "AND " + " AND ".join(outer_conditions) if outer_conditions else ""
    where = _where_clause(conditions)
    if health_band:
        params["health_band"] = health_band
    params["limit"] = 5000

    sql = text(f"""
        SELECT * FROM ({_SELECT_COLS} {_JOINS} {where}) sq
        WHERE TRUE {hb_cond}
        ORDER BY sq.last_booking_at DESC NULLS LAST, sq.created_at DESC
        LIMIT :limit
    """)
    rows = (await db.execute(sql, params)).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Phone", "Email", "City", "State", "Zipcode",
        "Health Band", "Total Bookings", "Completed", "Cancelled",
        "Complaints", "Reviews", "Avg Rating", "Last Booking", "Created",
    ])
    for row in rows:
        writer.writerow([
            row.full_name, row.phone or "", row.email or "",
            row.city or "", row.state or "", row.zipcode or "",
            row.health_band,
            int(row.total_bookings), int(row.completed_bookings), int(row.cancelled_bookings),
            int(row.complaints_count), int(row.reviews_count),
            round(float(row.average_rating), 2) if row.average_rating else "",
            row.last_booking_at.isoformat() if row.last_booking_at else "",
            row.created_at.isoformat() if row.created_at else "",
        ])

    fname = f"customers-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("")
async def list_admin_customers(
    r: Request,
    q:                 Optional[str]  = Query(None),
    tenant_id:         Optional[str]  = Query(None),
    health_band:       Optional[str]  = Query(None),
    engagement_status: Optional[str]  = Query(None),
    city:              Optional[str]  = Query(None),
    state:             Optional[str]  = Query(None),
    zipcode:           Optional[str]  = Query(None),
    has_complaints:    Optional[bool] = Query(None),
    has_reviews:       Optional[bool] = Query(None),
    booking_count_min: Optional[int]  = Query(None),
    booking_count_max: Optional[int]  = Query(None),
    last_booking_from: Optional[str]  = Query(None),
    last_booking_to:   Optional[str]  = Query(None),
    created_from:      Optional[str]  = Query(None),
    created_to:        Optional[str]  = Query(None),
    sort_by:   str = Query("created_at", pattern="^(created_at|last_booking_at|total_bookings|full_name)$"),
    sort_dir:  str = Query("desc", pattern="^(asc|desc)$"),
    page:      int = Query(1,  ge=1),
    page_size: int = Query(25, ge=1, le=200),
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    conditions, params = _build_filters(
        q, tenant_id, health_band, engagement_status, city, state, zipcode,
        has_complaints, has_reviews, booking_count_min, booking_count_max,
        last_booking_from, last_booking_to, created_from, created_to,
    )
    outer_conditions: list[str] = []
    if health_band:
        outer_conditions.append("sq.health_band = :health_band")
    if engagement_status == "active":
        outer_conditions.append("sq.health_band IN ('healthy', 'active')")
    hb_cond = "AND " + " AND ".join(outer_conditions) if outer_conditions else ""
    where = _where_clause(conditions)
    if health_band:
        params["health_band"] = health_band

    # sort_by maps to column in outer sq
    sort_col_map = {
        "created_at": "sq.created_at",
        "last_booking_at": "sq.last_booking_at",
        "total_bookings": "sq.total_bookings",
        "full_name": "sq.full_name",
    }
    sort_col = sort_col_map.get(sort_by, "sq.created_at")
    order = f"{sort_col} {'ASC' if sort_dir == 'asc' else 'DESC'} NULLS LAST"

    offset = (page - 1) * page_size

    # The common directory query (search/provider/date only) must not execute
    # four per-customer aggregate laterals merely to obtain a total count.
    # Enriched counts are reserved for filters that actually depend on them.
    needs_enriched_count = any((
        health_band, engagement_status, city, state, zipcode,
        has_complaints is not None, has_reviews is not None,
        booking_count_min is not None, booking_count_max is not None,
        last_booking_from, last_booking_to,
    ))
    needs_enriched_list = needs_enriched_count or sort_by in {"last_booking_at", "total_bookings"}
    if needs_enriched_list:
        list_sql = text(f"""
            SELECT * FROM ({_SELECT_COLS} {_JOINS} {where}) sq
            WHERE TRUE {hb_cond}
            ORDER BY {order}
            LIMIT :limit OFFSET :offset
        """)
    else:
        # Page indexed user IDs first, then enrich only the bounded page.
        # This avoids executing activity/review/complaint aggregates for every
        # customer in a million-row directory on the normal browse path.
        base_order = "u.full_name ASC, u.id ASC" if sort_by == "full_name" and sort_dir == "asc" else \
                     "u.full_name DESC, u.id DESC" if sort_by == "full_name" else \
                     f"u.created_at {'ASC' if sort_dir == 'asc' else 'DESC'}, u.id {'ASC' if sort_dir == 'asc' else 'DESC'}"
        paged_joins = _JOINS.replace("FROM users u", "FROM base_ids base JOIN users u ON u.id = base.id", 1)
        list_sql = text(f"""
            WITH base_ids AS (
                SELECT u.id FROM users u
                WHERE u.role = 'customer' AND u.deleted_at IS NULL {where}
                ORDER BY {base_order}
                LIMIT :limit OFFSET :offset
            )
            SELECT * FROM ({_SELECT_COLS} {paged_joins}) sq
            ORDER BY {order}
        """)
    count_sql = text(f"""
        SELECT COUNT(*) FROM (
            SELECT sq.id FROM ({_SELECT_COLS} {_JOINS} {where}) sq
            WHERE TRUE {hb_cond}
        ) counted
    """) if needs_enriched_count else text(f"""
        SELECT COUNT(*)
        FROM users u
        WHERE u.role = 'customer' AND u.deleted_at IS NULL {where}
    """)

    rows  = (await db.execute(list_sql,  {**params, "limit": page_size, "offset": offset})).fetchall()
    total = (await db.execute(count_sql, params)).scalar() or 0

    return ok({
        "customers": [_row_to_dict(row) for row in rows],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "total_pages": max(1, (int(total) + page_size - 1) // page_size),
        },
    }, _rid(r), "customers")


@router.get("/{customer_id}/bookings")
async def customer_booking_history(
    customer_id: str,
    r: Request,
    tenant_id:  Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    date_from:  Optional[str] = Query(None),
    date_to:    Optional[str] = Query(None),
    page:       int           = Query(1,  ge=1),
    page_size:  int           = Query(20, ge=1, le=100),
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    conds = ["b.customer_id = :cid ::uuid"]
    params: dict = {"cid": customer_id}

    if tenant_id:
        conds.append("b.tenant_id = :tenant_id ::uuid")
        params["tenant_id"] = tenant_id
    if status:
        conds.append("b.status = :status")
        params["status"] = status
    if date_from:
        try:
            params["date_from"] = datetime.fromisoformat(date_from)
            conds.append("b.created_at >= :date_from")
        except ValueError:
            pass
    if date_to:
        try:
            params["date_to"] = datetime.fromisoformat(date_to)
            conds.append("b.created_at <= :date_to")
        except ValueError:
            pass

    where = " AND ".join(conds)
    offset = (page - 1) * page_size

    sql = text(f"""
        SELECT
            b.id, b.booking_number, b.status,
            COALESCE(ms.service_name, b.issue_summary, 'Home Service') AS category_name,
            COALESCE(
                NULLIF(b.price_snapshot->>'estimated_total', '')::numeric,
                NULLIF(b.price_snapshot->>'max_price', '')::numeric,
                NULLIF(b.price_snapshot->>'visit_fee', '')::numeric
            ) AS amount,
            b.city, b.created_at, sj.scheduled_date, b.preferred_date,
            COALESCE(t.business_name, t.tenant_name, '') AS tenant_name,
            b.tenant_id, sj.id AS job_id
        FROM service_bookings b
        LEFT JOIN tenants t ON t.id = b.tenant_id
        LEFT JOIN master_services ms ON ms.id = b.offering_id
        LEFT JOIN service_jobs sj ON sj.booking_id = b.id
        WHERE {where}
        ORDER BY b.created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    count_sql = text(f"SELECT COUNT(*) FROM service_bookings b WHERE {where}")

    rows  = (await db.execute(sql, {**params, "limit": page_size, "offset": offset})).fetchall()
    total = (await db.execute(count_sql, params)).scalar() or 0

    return ok({
        "bookings": [{
            "id":            str(row.id),
            "booking_number": row.booking_number,
            "tenant_name":   row.tenant_name,
            "tenant_id":     str(row.tenant_id),
            "job_id":        str(row.job_id) if row.job_id else None,
            "category_name": row.category_name or "",
            "status":        row.status,
            "amount":        float(row.amount) if row.amount else None,
            "city":          row.city or "",
            "created_at":    row.created_at.isoformat() if row.created_at else None,
            "scheduled_at":  row.scheduled_date.isoformat() if row.scheduled_date else (row.preferred_date.isoformat() if row.preferred_date else None),
        } for row in rows],
        "meta": {
            "page": page, "page_size": page_size,
            "total": int(total),
            "total_pages": max(1, (int(total) + page_size - 1) // page_size),
        },
    }, _rid(r), "customers")


@router.get("/{customer_id}")
async def get_admin_customer(
    customer_id: str,
    r: Request,
    u:  UserContext  = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    sql = text(f"""
        SELECT * FROM ({_SELECT_COLS} {_JOINS} AND u.id = :cid ::uuid) sq
    """)
    row = (await db.execute(sql, {"cid": customer_id})).fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Customer not found")
    return ok(_row_to_dict(row), _rid(r), "customers")


# ═══════════════════════════════════════════════════════════════
# Customer Users Enterprise Upgrade — detail-tab sub-resources
# ═══════════════════════════════════════════════════════════════

@retired_case_router.get("/{customer_id}/complaints", response_model=None)
async def customer_complaints(r: Request, customer_id: uuid.UUID,
                               status: Optional[str] = Query(None),
                               u: UserContext = Depends(require_permission(P.CUSTOMERS_VIEW_DETAIL)),
                               s: CustomerAdminService = Depends(_svc)):
    return ok(await s.list_complaints(customer_id, status), _rid(r), "customers")


@retired_case_router.get("/{customer_id}/service-credits", response_model=None)
async def customer_service_credits(r: Request, customer_id: uuid.UUID,
                                    status: Optional[str] = Query(None),
                                    u: UserContext = Depends(require_permission(P.CUSTOMERS_SERVICE_CREDITS_READ)),
                                    s: CustomerAdminService = Depends(_svc)):
    return ok(await s.list_service_credits(customer_id, status), _rid(r), "customers")


class IssueCreditBody(BaseModel):
    amount: float
    credit_type: str = "platform_goodwill"
    issued_reason: str
    customer_message: Optional[str] = None
    validity_days: Optional[int] = None


@retired_case_router.post("/{customer_id}/service-credits", response_model=None)
async def issue_customer_service_credit(r: Request, customer_id: uuid.UUID, body: IssueCreditBody,
                                         u: UserContext = Depends(require_permission(P.CUSTOMERS_SERVICE_CREDITS_CREATE)),
                                         s: CustomerAdminService = Depends(_svc)):
    data = body.model_dump(exclude_none=True)
    return ok(await s.issue_service_credit(customer_id, data), _rid(r), "customers")


@router.get("/{customer_id}/addresses", response_model=None, summary="Customer addresses")
async def customer_addresses(r: Request, customer_id: uuid.UUID,
                              u: UserContext = Depends(require_permission(P.CUSTOMERS_ADDRESSES_READ)),
                              s: CustomerAdminService = Depends(_svc)):
    return ok(await s.list_addresses(customer_id), _rid(r), "customers")


@router.get("/{customer_id}/sessions", response_model=None, summary="Customer active sessions")
async def customer_sessions(r: Request, customer_id: uuid.UUID,
                             u: UserContext = Depends(require_permission(P.CUSTOMERS_SESSIONS_READ)),
                             s: CustomerAdminService = Depends(_svc)):
    return ok(await s.list_sessions(customer_id), _rid(r), "customers")


@router.get("/{customer_id}/login-history", response_model=None, summary="Customer login history")
async def customer_login_history(r: Request, customer_id: uuid.UUID,
                                  u: UserContext = Depends(require_permission(P.CUSTOMERS_LOGIN_HISTORY_READ)),
                                  s: CustomerAdminService = Depends(_svc)):
    return ok(await s.list_login_history(customer_id), _rid(r), "customers")


@router.get("/{customer_id}/privacy-requests", response_model=None, summary="Customer DPDP/privacy requests")
async def customer_privacy_requests(r: Request, customer_id: uuid.UUID,
                                     u: UserContext = Depends(require_permission(P.CUSTOMERS_PRIVACY_READ)),
                                     s: CustomerAdminService = Depends(_svc)):
    return ok(await s.list_privacy_requests(customer_id), _rid(r), "customers")


@router.get("/{customer_id}/audit-logs", response_model=None, summary="Customer audit logs")
async def customer_audit_logs(r: Request, customer_id: uuid.UUID,
                               u: UserContext = Depends(require_permission(P.CUSTOMERS_AUDIT_READ)),
                               s: CustomerAdminService = Depends(_svc)):
    return ok(await s.list_audit_logs(customer_id), _rid(r), "customers")


class ReasonBody(BaseModel):
    reason: str


@router.post("/{customer_id}/block", response_model=None, summary="Block customer")
async def block_customer(r: Request, customer_id: uuid.UUID, body: ReasonBody,
                          u: UserContext = Depends(require_permission(P.CUSTOMERS_BLOCK)),
                          s: CustomerAdminService = Depends(_svc)):
    return ok(await s.block_customer(customer_id, body.reason), _rid(r), "customers")


@router.post("/{customer_id}/unblock", response_model=None, summary="Unblock customer")
async def unblock_customer(r: Request, customer_id: uuid.UUID, body: ReasonBody,
                            u: UserContext = Depends(require_permission(P.CUSTOMERS_BLOCK)),
                            s: CustomerAdminService = Depends(_svc)):
    return ok(await s.unblock_customer(customer_id, body.reason), _rid(r), "customers")


@router.post("/{customer_id}/suspend", response_model=None, summary="Suspend customer")
async def suspend_customer(r: Request, customer_id: uuid.UUID, body: ReasonBody,
                            u: UserContext = Depends(require_permission(P.CUSTOMERS_SUSPEND)),
                            s: CustomerAdminService = Depends(_svc)):
    return ok(await s.suspend_customer(customer_id, body.reason), _rid(r), "customers")


@router.post("/{customer_id}/reactivate", response_model=None, summary="Reactivate customer")
async def reactivate_customer(r: Request, customer_id: uuid.UUID, body: ReasonBody,
                               u: UserContext = Depends(require_permission(P.CUSTOMERS_REACTIVATE)),
                               s: CustomerAdminService = Depends(_svc)):
    return ok(await s.reactivate_customer(customer_id, body.reason), _rid(r), "customers")


@router.post("/{customer_id}/sessions/revoke-all", response_model=None, summary="Force logout customer")
async def customer_revoke_all_sessions(r: Request, customer_id: uuid.UUID, body: ReasonBody,
                                        u: UserContext = Depends(require_permission(P.CUSTOMERS_SESSIONS_REVOKE)),
                                        s: CustomerAdminService = Depends(_svc)):
    return ok(await s.revoke_all_sessions(customer_id, body.reason), _rid(r), "customers")
