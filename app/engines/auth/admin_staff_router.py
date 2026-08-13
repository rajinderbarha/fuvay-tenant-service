"""Platform-wide admin staff management — no tenant required."""
from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from app.dependencies.db import get_db
from app.core.permissions import P, require_permission

router = APIRouter(prefix="/v1/admin/staff", tags=["Admin Staff"])

_ROLES_EXCLUDED = ("customer", "super_admin")

_ACTIVE_JOB_STATUSES = (
    "pending_assignment", "assigned", "accepted", "scheduled", "on_the_way",
    "reached_site", "inspection_started", "inspection_done", "quote_required",
    "service_started", "work_done", "customer_not_available",
)
_ACTIVE_JOB_STATUS_SQL = ",".join(f"'{status}'" for status in _ACTIVE_JOB_STATUSES)

_SELECT_COLS = """
    u.id                AS user_id,
    u.full_name,
    u.email,
    u.phone,
    u.role,
    u.is_active,
    u.is_verified,
    u.tenant_id,
    u.created_at,
    t.tenant_name,
    t.business_name,
    t.city             AS tenant_city,
    jb.total_jobs,
    jb.completed_jobs,
    jb.active_jobs,
    jb.last_job_at,
    jb.last_category,
    srs.average_rating,
    srs.total_reviews,
    CASE
        WHEN u.is_active = FALSE                         THEN 'inactive'
        WHEN COALESCE(jb.active_jobs, 0) > 0            THEN 'busy'
        ELSE                                                  'available'
    END                AS availability_status
"""

_JOINS = f"""
    FROM   users u
    LEFT   JOIN tenants t ON t.id = u.tenant_id
    LEFT   JOIN LATERAL (
        SELECT
            COUNT(*)                                         AS total_jobs,
            COUNT(*) FILTER (WHERE j.status = 'completed')  AS completed_jobs,
            COUNT(*) FILTER (WHERE j.status IN ({_ACTIVE_JOB_STATUS_SQL})) AS active_jobs,
            MAX(j.created_at)                                AS last_job_at,
            (SELECT COALESCE(ms2.service_name, 'Home Service')
             FROM   service_jobs j2
             LEFT JOIN master_services ms2 ON ms2.id = j2.offering_id
             WHERE  j2.assigned_staff_id = u.id
             ORDER  BY j2.created_at DESC LIMIT 1)          AS last_category
        FROM   service_jobs j
        WHERE  j.assigned_staff_id = u.id
    ) jb ON TRUE
    LEFT   JOIN LATERAL (
        SELECT average_rating, total_reviews
        FROM   staff_rating_summaries
        WHERE  staff_member_id = u.id
        ORDER  BY updated_at DESC LIMIT 1
    ) srs ON TRUE
"""


def _base_where() -> tuple[str, dict]:
    return (
        "u.role NOT IN ('customer', 'super_admin')\n  AND u.tenant_id IS NOT NULL",
        {},
    )


def _build_filters(
    q, tenant_id, role, availability_status, is_active, is_verified, city,
    job_count_min, job_count_max, rating_min, created_from, created_to,
) -> tuple[str, dict]:
    where, params = _base_where()

    if q:
        where += " AND (u.full_name ILIKE :q OR u.email ILIKE :q OR u.phone ILIKE :q)"
        params["q"] = f"%{q}%"
    if tenant_id:
        where += " AND u.tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    if role:
        where += " AND u.role = :role"
        params["role"] = role
    if is_active is not None:
        where += " AND u.is_active = :is_active"
        params["is_active"] = is_active
    if is_verified is not None:
        where += " AND u.is_verified = :is_verified"
        params["is_verified"] = is_verified
    if city:
        where += " AND t.city ILIKE :city"
        params["city"] = f"%{city}%"
    if availability_status == "inactive":
        where += " AND u.is_active = FALSE"
    elif availability_status in {"available", "busy"}:
        where += " AND u.is_active = TRUE"
        exists_sql = (
            "EXISTS (SELECT 1 FROM service_jobs af "
            f"WHERE af.assigned_staff_id = u.id AND af.status IN ({_ACTIVE_JOB_STATUS_SQL}))"
        )
        where += f" AND {exists_sql if availability_status == 'busy' else f'NOT {exists_sql}'}"
    if created_from:
        where += " AND u.created_at >= :created_from"
        params["created_from"] = created_from
    if created_to:
        where += " AND u.created_at <= :created_to"
        params["created_to"] = created_to
    if job_count_min is not None:
        where += " AND COALESCE(jb.total_jobs, 0) >= :job_count_min"
        params["job_count_min"] = job_count_min
    if job_count_max is not None:
        where += " AND COALESCE(jb.total_jobs, 0) <= :job_count_max"
        params["job_count_max"] = job_count_max
    if rating_min is not None:
        where += " AND COALESCE(srs.average_rating, 0) >= :rating_min"
        params["rating_min"] = rating_min

    return where, params


def _row_to_dict(row) -> dict:
    def _s(v):
        return str(v) if v is not None else None

    return {
        "user_id":             _s(row.user_id),
        "full_name":           row.full_name,
        "email":               row.email,
        "phone":               row.phone,
        "role":                row.role,
        "is_active":           row.is_active,
        "is_verified":         row.is_verified,
        "tenant_id":           _s(row.tenant_id),
        "tenant_name":         row.tenant_name,
        "business_name":       row.business_name,
        "tenant_city":         row.tenant_city,
        "total_jobs":          row.total_jobs or 0,
        "completed_jobs":      row.completed_jobs or 0,
        "active_jobs":         row.active_jobs or 0,
        "last_job_at":         row.last_job_at.isoformat() if row.last_job_at else None,
        "last_category":       row.last_category,
        "average_rating":      float(row.average_rating) if row.average_rating else None,
        "total_reviews":       row.total_reviews or 0,
        "availability_status": row.availability_status,
        "created_at":          row.created_at.isoformat() if row.created_at else None,
    }


# ── /filters ──────────────────────────────────────────────────────────────────

@router.get("/filters")
async def get_staff_filters(
    _admin=Depends(require_permission(P.STAFF_READ)),
    db=Depends(get_db),
):
    where, params = _base_where()
    sql = f"""
        SELECT
            COALESCE(array_agg(DISTINCT u.role ORDER BY u.role) FILTER (WHERE u.role IS NOT NULL), '{{}}') AS roles,
            COALESCE(array_agg(DISTINCT t.city ORDER BY t.city) FILTER (WHERE t.city IS NOT NULL), '{{}}') AS cities
        FROM   users u
        LEFT   JOIN tenants t ON t.id = u.tenant_id
        WHERE  {where}
    """
    row = (await db.execute(text(sql), params)).mappings().one()
    return {"data": {
        "roles":   [{"value": r, "label": r.replace("_", " ").title()} for r in (row["roles"] or [])],
        "cities":  [{"value": c, "label": c} for c in (row["cities"] or [])],
        "tenants": [dict(r) for r in (await db.execute(text("""
            SELECT id::text AS value, COALESCE(business_name, tenant_name) AS label
            FROM tenants WHERE COALESCE(business_name, tenant_name) IS NOT NULL
            ORDER BY COALESCE(business_name, tenant_name) LIMIT 500
        """))).mappings().all()],
    }}


# ── /summary ──────────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_staff_summary(
    _admin=Depends(require_permission(P.STAFF_READ)),
    db=Depends(get_db),
):
    where, params = _base_where()
    sql = f"""
        SELECT
            COUNT(*)                                                      AS total,
            COUNT(*) FILTER (WHERE u.is_active = TRUE)                    AS active,
            COUNT(*) FILTER (WHERE u.is_active = FALSE)                   AS inactive,
            COUNT(*) FILTER (WHERE u.is_verified = TRUE)                  AS verified,
            COUNT(*) FILTER (WHERE u.is_verified = FALSE)                 AS unverified,
            COUNT(*) FILTER (WHERE u.created_at >= NOW() - INTERVAL '7 days') AS new_this_week
        FROM   users u
        LEFT   JOIN tenants t ON t.id = u.tenant_id
        WHERE  {where}
    """
    row = (await db.execute(text(sql), params)).mappings().one()

    busy_sql = f"""
        SELECT COUNT(*) AS busy
        FROM   users u
        LEFT   JOIN tenants t ON t.id = u.tenant_id
        WHERE  {where}
        AND    EXISTS (
            SELECT 1 FROM service_jobs j
            WHERE  j.assigned_staff_id = u.id
            AND    j.status IN ({_ACTIVE_JOB_STATUS_SQL})
        )
    """
    busy_row = (await db.execute(text(busy_sql), params)).mappings().one()

    return {"data": {
        "total":         row["total"] or 0,
        "active":        row["active"] or 0,
        "inactive":      row["inactive"] or 0,
        "verified":      row["verified"] or 0,
        "unverified":    row["unverified"] or 0,
        "busy":          busy_row["busy"] or 0,
        "new_this_week": row["new_this_week"] or 0,
    }}


# ── /export ───────────────────────────────────────────────────────────────────

@router.get("/export")
async def export_staff(
    q: Optional[str]   = Query(None),
    tenant_id: Optional[str] = Query(None),
    role: Optional[str]      = Query(None),
    availability_status: Optional[str] = Query(None),
    is_active: Optional[bool]          = Query(None),
    is_verified: Optional[bool]        = Query(None),
    city: Optional[str]                = Query(None),
    job_count_min: Optional[int]       = Query(None, ge=0),
    job_count_max: Optional[int]       = Query(None, ge=0),
    rating_min: Optional[float]        = Query(None, ge=0, le=5),
    created_from: Optional[str]        = Query(None),
    created_to: Optional[str]          = Query(None),
    _admin=Depends(require_permission(P.STAFF_READ)),
    db=Depends(get_db),
):
    where, params = _build_filters(
        q, tenant_id, role, availability_status, is_active, is_verified, city,
        job_count_min, job_count_max, rating_min, created_from, created_to,
    )
    sql = f"""
        SELECT {_SELECT_COLS}
        {_JOINS}
        WHERE  {where}
        ORDER  BY u.full_name
        LIMIT  5000
    """
    rows = (await db.execute(text(sql), params)).mappings().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "User ID", "Full Name", "Email", "Phone", "Role", "Active", "Verified",
        "Tenant", "City", "Total Jobs", "Completed Jobs", "Active Jobs",
        "Avg Rating", "Reviews", "Availability", "Joined",
    ])
    for r in rows:
        writer.writerow([
            str(r["user_id"]), r["full_name"], r["email"], r["phone"] or "",
            r["role"], r["is_active"], r["is_verified"],
            r["tenant_name"] or "", r["tenant_city"] or "",
            r["total_jobs"] or 0, r["completed_jobs"] or 0, r["active_jobs"] or 0,
            float(r["average_rating"]) if r["average_rating"] else "",
            r["total_reviews"] or 0, r["availability_status"],
            r["created_at"].isoformat() if r["created_at"] else "",
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=staff_export.csv"},
    )


def _avail_case():
    return """CASE
        WHEN u.is_active = FALSE THEN 'inactive'
        WHEN COALESCE(jb.active_jobs, 0) > 0 THEN 'busy'
        ELSE 'available'
    END"""


# ── / (list) ──────────────────────────────────────────────────────────────────

_SORT_COLS = {
    "full_name": "u.full_name",
    "role": "u.role",
    "created_at": "u.created_at",
    "total_jobs": "jb.total_jobs",
    "average_rating": "srs.average_rating",
    "tenant_name": "t.tenant_name",
}

@router.get("")
async def list_staff(
    q: Optional[str]   = Query(None),
    tenant_id: Optional[str]          = Query(None),
    role: Optional[str]               = Query(None),
    availability_status: Optional[str]= Query(None),
    is_active: Optional[bool]         = Query(None),
    is_verified: Optional[bool]       = Query(None),
    city: Optional[str]               = Query(None),
    job_count_min: Optional[int]      = Query(None, ge=0),
    job_count_max: Optional[int]      = Query(None, ge=0),
    rating_min: Optional[float]       = Query(None, ge=0, le=5),
    created_from: Optional[str]       = Query(None),
    created_to: Optional[str]         = Query(None),
    sort_by: str   = Query("full_name", pattern="^(full_name|role|created_at|total_jobs|average_rating|tenant_name)$"),
    sort_dir: str  = Query("asc", pattern="^(asc|desc)$"),
    page: int      = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    _admin=Depends(require_permission(P.STAFF_READ)),
    db=Depends(get_db),
):
    where, params = _build_filters(
        q, tenant_id, role, availability_status, is_active, is_verified, city,
        job_count_min, job_count_max, rating_min, created_from, created_to,
    )

    sort_col = _SORT_COLS.get(sort_by, "u.full_name")
    sort_sql = f"{sort_col} {sort_dir.upper()} NULLS LAST"

    needs_enriched_count = job_count_min is not None or job_count_max is not None or rating_min is not None
    count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT u.id {_JOINS}
            WHERE  {where}
        ) _c
    """ if needs_enriched_count else f"""
        SELECT COUNT(*)
        FROM users u LEFT JOIN tenants t ON t.id = u.tenant_id
        WHERE {where}
    """
    total = (await db.execute(text(count_sql), params)).scalar() or 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    needs_enriched_list = needs_enriched_count or sort_by in {"total_jobs", "average_rating"}
    if needs_enriched_list:
        data_sql = f"""
            SELECT {_SELECT_COLS} {_JOINS}
            WHERE {where} ORDER BY {sort_sql}
            LIMIT :limit OFFSET :offset
        """
    else:
        paged_joins = _JOINS.replace("FROM   users u", "FROM base_ids base JOIN users u ON u.id = base.id", 1)
        data_sql = f"""
            WITH base_ids AS (
                SELECT u.id FROM users u LEFT JOIN tenants t ON t.id = u.tenant_id
                WHERE {where} ORDER BY {sort_sql}, u.id
                LIMIT :limit OFFSET :offset
            )
            SELECT {_SELECT_COLS} {paged_joins}
            WHERE {where} ORDER BY {sort_sql}
        """
    rows = (await db.execute(text(data_sql), params)).mappings().all()

    return {"data": {
        "staff": [_row_to_dict(r) for r in rows],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, -(-total // page_size)),
        },
    }}


# ── /{staff_id} ───────────────────────────────────────────────────────────────

@router.get("/{staff_id}")
async def get_staff_member(
    staff_id: str,
    _admin=Depends(require_permission(P.STAFF_READ)),
    db=Depends(get_db),
):
    where = "u.id = :uid AND u.role NOT IN ('customer', 'super_admin')"
    sql = f"SELECT {_SELECT_COLS} {_JOINS} WHERE {where}"
    row = (await db.execute(text(sql), {"uid": staff_id})).mappings().first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Staff member not found")
    return {"data": _row_to_dict(row)}


# ── /{staff_id}/jobs ──────────────────────────────────────────────────────────

@router.get("/{staff_id}/jobs")
async def get_staff_jobs(
    staff_id: str,
    status: Optional[str] = Query(None),
    page: int      = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin=Depends(require_permission(P.STAFF_READ)),
    db=Depends(get_db),
):
    where = "j.assigned_staff_id = :sid"
    params: dict = {"sid": staff_id}
    if status:
        where += " AND j.status = :status"
        params["status"] = status

    total = (await db.execute(text(f"SELECT COUNT(*) FROM service_jobs j WHERE {where}"), params)).scalar() or 0
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    sql = f"""
        SELECT
            j.id, j.job_number, b.booking_number, j.status,
            COALESCE(ms.service_name, b.issue_summary, 'Home Service') AS service_category,
            j.city, cr.staff_rating AS customer_rating,
            CASE WHEN j.status = 'completed' THEN j.updated_at ELSE NULL END AS completed_at,
            j.created_at,
            t.tenant_name
        FROM   service_jobs j
        LEFT   JOIN service_bookings b ON b.id = j.booking_id
        LEFT   JOIN master_services ms ON ms.id = j.offering_id
        LEFT   JOIN LATERAL (
            SELECT COALESCE(r.staff_rating, r.overall_rating) AS staff_rating
            FROM customer_reviews r
            WHERE r.staff_member_id = j.assigned_staff_id
              AND (r.job_id = j.id OR r.record_id = j.id)
            ORDER BY r.created_at DESC LIMIT 1
        ) cr ON TRUE
        LEFT   JOIN tenants t ON t.id = j.tenant_id
        WHERE  {where}
        ORDER  BY j.created_at DESC
        LIMIT  :limit OFFSET :offset
    """
    rows = (await db.execute(text(sql), params)).mappings().all()

    def _job(r):
        return {
            "id":              str(r["id"]),
            "job_number":      r["job_number"],
            "booking_number":  r["booking_number"],
            "status":          r["status"],
            "service_category":r["service_category"],
            "city":            r["city"],
            "customer_rating": r["customer_rating"],
            "completed_at":    r["completed_at"].isoformat() if r["completed_at"] else None,
            "created_at":      r["created_at"].isoformat() if r["created_at"] else None,
            "tenant_name":     r["tenant_name"],
        }

    return {"data": {
        "jobs": [_job(r) for r in rows],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, -(-total // page_size)),
        },
    }}
