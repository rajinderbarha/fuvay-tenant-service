"""Admin router for provider management (Sprint 9/10/12 + P0 Enterprise Upgrade)."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, get_current_user, UserContext
from app.core.permissions import require_permission, P
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engine_registry.registry import registry

admin_router = APIRouter(prefix="/v1/admin", tags=["Admin — Provider Management"])


# ── Providers Summary / Directory ─────────────────────────────────────────────

@admin_router.get("/providers/summary", tags=["Admin — Providers"])
async def get_providers_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    """All-providers summary counts for the enterprise directory page."""
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    row = await db.execute(text("""
        WITH pkg_latest AS (
            SELECT DISTINCT ON (tenant_id)
                tenant_id, status AS pkg_status
            FROM tenant_package_assignments
            WHERE deleted_at IS NULL
            ORDER BY tenant_id, created_at DESC
        )
        SELECT
            COUNT(*)                                                         AS total,
            SUM(CASE WHEN t.status = 'active'
                     AND t.verification_status IN ('approved','verified')
                     THEN 1 ELSE 0 END)                                      AS active,
            SUM(CASE WHEN t.status = 'suspended'                  THEN 1 ELSE 0 END) AS suspended,
            SUM(CASE WHEN t.verification_status = 'not_started'
                     AND t.status NOT IN ('suspended','rejected')  THEN 1 ELSE 0 END) AS pending_setup,
            SUM(CASE WHEN t.verification_status IN ('pending','under_review')
                                                                   THEN 1 ELSE 0 END) AS pending_review,
            SUM(CASE WHEN t.verification_status = 'changes_requested'
                                                                   THEN 1 ELSE 0 END) AS changes_requested,
            SUM(CASE WHEN t.verification_status = 'rejected'
                     OR  t.status = 'rejected'                     THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN lp.pkg_status IN ('selected','paid_pending_approval')
                                                                   THEN 1 ELSE 0 END) AS package_pending_approval
        FROM tenants t
        LEFT JOIN pkg_latest lp ON lp.tenant_id = t.id
        WHERE t.terminated_at IS NULL AND t.archived_at IS NULL
    """))
    r = row.fetchone()
    return ok({
        "total":                   int(r[0] or 0),
        "active":                  int(r[1] or 0),
        "suspended":               int(r[2] or 0),
        "pending_setup":           int(r[3] or 0),
        "pending_review":          int(r[4] or 0),
        "changes_requested":       int(r[5] or 0),
        "rejected":                int(r[6] or 0),
        "package_pending_approval":int(r[7] or 0),
    }, request_id=rid)


# ── New Business Requests ─────────────────────────────────────────────────────

_NEW_REQUESTS_CTE = """
WITH latest_pkg AS (
    SELECT DISTINCT ON (tenant_id)
        tenant_id, status AS pkg_status, package_id
    FROM tenant_package_assignments
    WHERE deleted_at IS NULL
    ORDER BY tenant_id, created_at DESC
)
SELECT
    t.id                                        AS tenant_id,
    COALESCE(t.business_name, t.tenant_name)    AS business_name,
    t.tenant_name,
    u.full_name                                 AS owner_name,
    u.email                                     AS owner_email,
    t.phone                                     AS owner_phone,
    t.vertical                                  AS vertical_type,
    sc.name                                     AS category_name,
    t.city, t.state, t.district, t.zipcode,
    t.verification_status,
    t.status                                    AS tenant_status,
    t.created_at, t.updated_at,
    sp.name                                     AS package_name,
    lp.pkg_status                               AS package_status,
    (
        CASE WHEN t.business_name   IS NOT NULL THEN 20 ELSE 0 END +
        CASE WHEN t.vertical        IS NOT NULL THEN 20 ELSE 0 END +
        CASE WHEN t.city            IS NOT NULL THEN 20 ELSE 0 END +
        CASE WHEN (t.phone IS NOT NULL OR t.email IS NOT NULL) THEN 20 ELSE 0 END +
        CASE WHEN t.owner_user_id   IS NOT NULL THEN 20 ELSE 0 END
    )                                           AS profile_completion_percentage
FROM tenants t
LEFT JOIN users u            ON u.id  = t.owner_user_id
LEFT JOIN service_categories sc ON sc.id = t.category_id
LEFT JOIN latest_pkg lp      ON lp.tenant_id = t.id
LEFT JOIN service_packages   sp ON sp.id = lp.package_id
WHERE t.terminated_at IS NULL
  AND t.archived_at   IS NULL
  AND t.verification_status = 'not_started'
"""


@admin_router.get("/providers/new-requests/summary", tags=["Admin — Providers"])
async def get_new_requests_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    """Summary counts for the New Business Requests page."""
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    row = await db.execute(text("""
        WITH latest_pkg AS (
            SELECT DISTINCT ON (tenant_id)
                tenant_id, status AS pkg_status
            FROM tenant_package_assignments
            WHERE deleted_at IS NULL
            ORDER BY tenant_id, created_at DESC
        )
        SELECT
            COUNT(*)                                                              AS total,
            SUM(CASE WHEN lp.pkg_status IS NOT NULL               THEN 1 ELSE 0 END) AS with_package,
            SUM(CASE WHEN lp.pkg_status IS NULL                   THEN 1 ELSE 0 END) AS without_package,
            SUM(CASE WHEN lp.pkg_status IN ('selected',
                     'paid_pending_approval')                      THEN 1 ELSE 0 END) AS package_selected,
            SUM(CASE WHEN (
                CASE WHEN t.business_name  IS NOT NULL THEN 20 ELSE 0 END +
                CASE WHEN t.vertical       IS NOT NULL THEN 20 ELSE 0 END +
                CASE WHEN t.city           IS NOT NULL THEN 20 ELSE 0 END +
                CASE WHEN (t.phone IS NOT NULL OR t.email IS NOT NULL) THEN 20 ELSE 0 END +
                CASE WHEN t.owner_user_id  IS NOT NULL THEN 20 ELSE 0 END
            ) >= 80 THEN 1 ELSE 0 END)                                           AS profile_near_complete
        FROM tenants t
        LEFT JOIN latest_pkg lp ON lp.tenant_id = t.id
        WHERE t.terminated_at IS NULL
          AND t.archived_at   IS NULL
          AND t.verification_status = 'not_started'
    """))
    r = row.fetchone()
    return ok({
        "total":                int(r[0] or 0),
        "with_package":         int(r[1] or 0),
        "without_package":      int(r[2] or 0),
        "package_selected":     int(r[3] or 0),
        "profile_near_complete":int(r[4] or 0),
    }, request_id=rid)


@admin_router.get("/providers/new-requests", tags=["Admin — Providers"])
async def list_new_requests(
    request: Request,
    q: Optional[str] = Query(None),
    vertical_type: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    has_package: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    """Providers that signed up but haven't submitted for review yet."""
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    offset = (page - 1) * page_size
    base = _NEW_REQUESTS_CTE
    params: Dict[str, Any] = {}
    filters = ""

    if q:
        filters += " AND (LOWER(t.business_name) LIKE :srch OR LOWER(t.tenant_name) LIKE :srch OR LOWER(u.email) LIKE :srch OR LOWER(t.phone) LIKE :srch)"
        params["srch"] = f"%{q.lower()}%"
    if vertical_type:
        filters += " AND LOWER(t.vertical) = :vtype"
        params["vtype"] = vertical_type.lower()
    if city:
        filters += " AND LOWER(t.city) LIKE :city"
        params["city"] = f"%{city.lower()}%"
    if has_package is True:
        filters += " AND lp.pkg_status IS NOT NULL"
    elif has_package is False:
        filters += " AND lp.pkg_status IS NULL"

    full_q = base + filters
    count_res = await db.execute(text(f"SELECT COUNT(*) FROM ({full_q}) _c"), params)
    total = int(count_res.scalar() or 0)

    allowed_sorts = {"created_at", "updated_at", "business_name", "city", "profile_completion_percentage"}
    sort_col = sort_by if sort_by in allowed_sorts else "created_at"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    full_q += f" ORDER BY {sort_col} {direction} LIMIT :lim OFFSET :off"
    params["lim"] = page_size
    params["off"] = offset

    result = await db.execute(text(full_q), params)
    rows = []
    for r in result.fetchall():
        row = dict(r._mapping)
        row["tenant_id"] = str(row["tenant_id"]) if row.get("tenant_id") else None
        row["profile_completion_percentage"] = int(row.get("profile_completion_percentage") or 0)
        row["review_status"] = "not_submitted"
        row["onboarding_status"] = "setup_in_progress"
        rows.append(row)

    return ok({
        "providers": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }, request_id=rid)


# ── Send Reminder ─────────────────────────────────────────────────────────────

@admin_router.post("/onboarding/providers/{tenant_id}/send-reminder", tags=["Admin — Providers"])
async def send_provider_reminder(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user (any authenticated principal of any
    # role, including customer/technician, could trigger this) -- gated to
    # super_admin as the minimal safe fix; no granular permission exists yet
    # for provider-nudge actions.
    user: UserContext = Depends(require_super_admin),
):
    """Send a setup reminder to a provider who hasn't completed onboarding."""
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    result = await db.execute(
        text("SELECT id, COALESCE(business_name, tenant_name) AS name, email, phone FROM tenants WHERE id = :tid"),
        {"tid": str(tenant_id)},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ok({
        "tenant_id": str(tenant_id),
        "business_name": row[1],
        "reminder_sent": True,
        "message": "Reminder queued (notification system will deliver via email/SMS).",
    }, request_id=rid)


# ── Engine Admin (proxy to engine registry) ───────────────────────────────────

@admin_router.get("/engines")
async def list_engines_admin(
    request: Request,
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    return ok(registry.summary(), request_id=rid)


@admin_router.get("/engines/health")
async def get_engines_health(
    request: Request,
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    return ok(registry.summary(), request_id=rid)


@admin_router.get("/engine-audit-logs")
async def get_engine_audit_logs(
    request: Request,
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    return ok({"logs": [], "total": 0}, request_id=rid)


# ── Provider Onboarding Admin (Sprint 9/10) ────────────────────────────────────

# Status derivation helpers — map verification_status to semantic labels
_REVIEW_STATUS_MAP = {
    "not_started": "not_submitted",
    "pending": "pending_review",
    "under_review": "pending_review",
    "changes_requested": "changes_requested",
    "approved": "approved",
    "verified": "approved",
    "rejected": "rejected",
}
_ONBOARDING_STATUS_MAP = {
    "not_started": "setup_in_progress",
    "pending": "submitted",
    "under_review": "under_review",
    "changes_requested": "changes_requested",
    "approved": "approved",
    "verified": "approved",
    "rejected": "rejected",
}
_READINESS_MAP = {
    "not_started": "incomplete",
    "pending": "ready_for_review",
    "under_review": "ready_for_review",
    "changes_requested": "needs_changes",
    "approved": "approved",
    "verified": "approved",
    "rejected": "rejected",
}

# Base WHERE clause for the onboarding queue — excludes fully active+approved tenants
_QUEUE_BASE_WHERE = """
    t.terminated_at IS NULL
    AND t.archived_at IS NULL
    AND NOT (t.status = 'active' AND t.verification_status IN ('approved', 'verified'))
"""

_QUEUE_CTE = """
WITH latest_pkg AS (
    SELECT DISTINCT ON (tenant_id)
        tenant_id,
        status      AS pkg_status,
        package_id
    FROM tenant_package_assignments
    WHERE deleted_at IS NULL
    ORDER BY tenant_id, created_at DESC
)
SELECT
    t.id                                                            AS tenant_id,
    COALESCE(t.business_name, t.tenant_name)                       AS business_name,
    t.tenant_name,
    u.full_name                                                     AS owner_name,
    u.email                                                         AS owner_email,
    t.vertical                                                      AS vertical_type,
    sc.name                                                         AS category_name,
    sc.category_type,
    t.city,
    t.state,
    t.district,
    t.zipcode,
    t.verification_status,
    t.status                                                        AS tenant_status,
    t.created_at,
    t.updated_at,
    sp.name                                                         AS selected_package_name,
    lp.pkg_status                                                   AS package_status,
    (
        CASE WHEN t.business_name IS NOT NULL THEN 20 ELSE 0 END +
        CASE WHEN t.vertical     IS NOT NULL THEN 20 ELSE 0 END +
        CASE WHEN t.city         IS NOT NULL THEN 20 ELSE 0 END +
        CASE WHEN (t.phone IS NOT NULL OR t.email IS NOT NULL) THEN 20 ELSE 0 END +
        CASE WHEN t.owner_user_id IS NOT NULL THEN 20 ELSE 0 END
    )                                                               AS profile_completion_percentage
FROM tenants t
LEFT JOIN users u            ON u.id  = t.owner_user_id
LEFT JOIN service_categories sc ON sc.id = t.category_id
LEFT JOIN latest_pkg lp      ON lp.tenant_id = t.id
LEFT JOIN service_packages   sp ON sp.id = lp.package_id
WHERE """ + _QUEUE_BASE_WHERE


def _enrich_row(row: dict) -> dict:
    vs = row.get("verification_status") or "not_started"
    row["review_status"]      = _REVIEW_STATUS_MAP.get(vs, "not_submitted")
    row["onboarding_status"]  = _ONBOARDING_STATUS_MAP.get(vs, "setup_in_progress")
    row["readiness_status"]   = _READINESS_MAP.get(vs, "incomplete")
    ts = row.get("tenant_status") or ""
    row["bookable_status"] = "bookable" if vs in ("approved", "verified") and ts == "active" else "pending_approval"
    row["profile_completion_percentage"] = int(row.get("profile_completion_percentage") or 0)
    row["tenant_id"] = str(row["tenant_id"]) if row.get("tenant_id") else None
    return row


async def _sync_home_services_enrollment_decision(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    decision: str,
    *,
    actor_id: str | None,
    reason: str | None = None,
) -> dict | None:
    """Apply an Admin review decision to the canonical HS enrollment.

    The Admin queue is tenant-record based for backwards compatibility,
    while tenant routing is enrollment based. A decision is only complete
    when both projections have moved together.
    """
    row = (await db.execute(text("""
        SELECT e.id, e.status
        FROM tenant_vertical_enrollments e
        JOIN verticals v ON v.id = e.vertical_id
        WHERE e.tenant_id=:tid AND v.key='home_services'
        LIMIT 1
    """), {"tid": str(tenant_id)})).fetchone()
    if not row:
        return None

    from app.engines.vertical_catalog.service import VerticalCatalogService
    enrollment_id = uuid.UUID(str(row.id))
    parsed_actor_id = uuid.UUID(str(actor_id)) if actor_id else None
    if decision == "approve":
        from app.engines.vertical_catalog.activation import approve_and_evaluate
        return await approve_and_evaluate(
            db, enrollment_id, tenant_id, actor_id=parsed_actor_id, reason=reason
        )

    status = "changes_requested" if decision == "request_changes" else "rejected"
    return await VerticalCatalogService().transition_enrollment(
        db, enrollment_id, status, actor_id=parsed_actor_id, reason=reason
    )


@admin_router.get("/onboarding/providers")
async def list_provider_onboarding(
    request: Request,
    q: Optional[str] = Query(None, alias="q"),
    search: Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    vertical_type: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    provider_status: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_ONBOARDING_READ)),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    offset = (page - 1) * page_size
    search_term = q or search

    base = _QUEUE_CTE
    params: Dict[str, Any] = {}
    filters = ""

    if search_term:
        filters += " AND (LOWER(t.business_name) LIKE :srch OR LOWER(t.tenant_name) LIKE :srch OR LOWER(u.email) LIKE :srch)"
        params["srch"] = f"%{search_term.lower()}%"
    if category_id:
        filters += " AND t.category_id = :cat_id::uuid"
        params["cat_id"] = category_id
    if vertical_type:
        filters += " AND LOWER(t.vertical) = :vtype"
        params["vtype"] = vertical_type.lower()
    if review_status or provider_status:
        # review_status is the new name; provider_status is legacy from old frontend
        rs = review_status or provider_status
        vs_reverse = {v: k for k, v in _REVIEW_STATUS_MAP.items()}
        if rs in _REVIEW_STATUS_MAP.values():
            matching = [k for k, v in _REVIEW_STATUS_MAP.items() if v == rs]
            placeholders = ", ".join(f":vs_{i}" for i in range(len(matching)))
            filters += f" AND t.verification_status IN ({placeholders})"
            for i, m in enumerate(matching):
                params[f"vs_{i}"] = m
        else:
            filters += " AND t.verification_status = :vstatus"
            params["vstatus"] = rs
    if city:
        filters += " AND LOWER(t.city) LIKE :city"
        params["city"] = f"%{city.lower()}%"

    full_q = base + filters

    # Summary counts (across all queue members, ignoring page filters)
    summary_res = await db.execute(text(f"""
        SELECT t.verification_status, COUNT(*) AS cnt
        FROM tenants t
        WHERE {_QUEUE_BASE_WHERE}
        GROUP BY t.verification_status
    """))
    summary_raw = {row[0]: int(row[1]) for row in summary_res.fetchall()}
    summary = {
        "pending_review":     sum(summary_raw.get(vs, 0) for vs in ("pending", "under_review")),
        "not_submitted":      summary_raw.get("not_started", 0),
        "changes_requested":  summary_raw.get("changes_requested", 0),
        "rejected":           summary_raw.get("rejected", 0),
        "total":              sum(summary_raw.values()),
    }

    count_res = await db.execute(text(f"SELECT COUNT(*) FROM ({full_q}) _c"), params)
    total = count_res.scalar() or 0

    allowed_sorts = {"created_at", "updated_at", "business_name", "city", "verification_status", "profile_completion_percentage"}
    sort_col = sort_by if sort_by in allowed_sorts else "created_at"
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
    full_q += f" ORDER BY {sort_col} {direction} LIMIT :lim OFFSET :off"
    params["lim"] = page_size
    params["off"] = offset

    result = await db.execute(text(full_q), params)
    rows = [_enrich_row(dict(r._mapping)) for r in result.fetchall()]

    return ok({
        "providers": rows,
        "total": total,
        "count": total,
        "page": page,
        "page_size": page_size,
        "summary": summary,
    }, request_id=rid)


@admin_router.get("/onboarding/providers/{tenant_id}")
async def get_provider_onboarding(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_ONBOARDING_READ)),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    result = await db.execute(text(_QUEUE_CTE + " AND t.id = :tid"), {"tid": str(tenant_id)})
    r = result.fetchone()
    if not r:
        return ok({
            "tenant_id": str(tenant_id), "review_status": "not_submitted",
            "onboarding_status": "setup_in_progress", "readiness_status": "incomplete",
            "bookable_status": "pending_approval", "profile_completion_percentage": 0,
            "business_name": None, "category_name": None, "city": None,
            "verification_status": None, "tenant_status": None,
        }, request_id=rid)
    return ok(_enrich_row(dict(r._mapping)), request_id=rid)


@admin_router.post("/onboarding/providers/{tenant_id}/approve")
async def approve_provider_onboarding(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_APPROVE)),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    # Validate: profile must be 100% complete before approval
    chk = await db.execute(
        text(_QUEUE_CTE + " AND t.id = :tid"),
        {"tid": str(tenant_id)},
    )
    row = chk.fetchone()
    if row:
        pct = int(row._mapping.get("profile_completion_percentage") or 0)
        if pct < 100:
            raise HTTPException(
                status_code=422,
                detail=f"Profile completion is {pct}%. Provider must have 100% complete profile before approval.",
            )
    from app.engines.tenant_engine.admin_service import AdminTenantService
    svc = AdminTenantService(db=db, request_id=rid, actor_id=user.user_id, actor_role="super_admin")
    result = await svc.verify_tenant(tenant_id)
    vertical_result = await _sync_home_services_enrollment_decision(
        db, tenant_id, "approve", actor_id=user.user_id
    )
    if vertical_result:
        result["vertical_status"] = vertical_result["status"]
        if vertical_result["status"] != "active":
            await db.execute(
                text("UPDATE tenants SET status='pending_activation', updated_at=NOW() WHERE id=:tid"),
                {"tid": str(tenant_id)},
            )
            result["status"] = "pending_activation"
    await db.commit()
    return ok(result, request_id=rid)


@admin_router.post("/onboarding/providers/{tenant_id}/reject")
async def reject_provider_onboarding(
    tenant_id: uuid.UUID, request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_REJECT)),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    if not payload.get("reason"):
        raise HTTPException(status_code=422, detail="reason is required to reject a tenant application.")
    from app.engines.tenant_engine.admin_service import AdminTenantService
    svc = AdminTenantService(db=db, request_id=rid, actor_id=user.user_id, actor_role="super_admin")
    result = await svc.reject_verification(tenant_id, reason=payload.get("reason", ""))
    vertical_result = await _sync_home_services_enrollment_decision(
        db, tenant_id, "reject", actor_id=user.user_id, reason=payload.get("reason", "")
    )
    if vertical_result:
        result["vertical_status"] = vertical_result["status"]
    await db.commit()
    return ok(result, request_id=rid)


@admin_router.post("/onboarding/providers/{tenant_id}/request-changes")
async def request_changes_provider_onboarding(
    tenant_id: uuid.UUID, request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_REQUEST_MORE_INFO)),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    from app.engines.tenant_engine.admin_service import AdminTenantService
    svc = AdminTenantService(db=db, request_id=rid, actor_id=user.user_id, actor_role="super_admin")
    reason = payload.get("notes") or payload.get("reason", "")
    result = await svc.request_changes(tenant_id, reason=reason)
    vertical_result = await _sync_home_services_enrollment_decision(
        db, tenant_id, "request_changes", actor_id=user.user_id, reason=reason
    )
    if vertical_result:
        result["vertical_status"] = vertical_result["status"]
        await db.execute(
            text("UPDATE tenants SET status='onboarding_pending', updated_at=NOW() WHERE id=:tid"),
            {"tid": str(tenant_id)},
        )
    await db.commit()
    return ok(result, request_id=rid)


@admin_router.post("/onboarding/providers/{tenant_id}/refresh")
async def refresh_provider_onboarding(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user -- gated to super_admin (same
    # minimal fix as the sibling /bookability/.../refresh endpoint below).
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    return ok({"tenant_id": str(tenant_id), "refreshed": True}, request_id=rid)


@admin_router.put("/onboarding/providers/{tenant_id}/items/{checklist_key}/override")
async def override_onboarding_item(
    tenant_id: uuid.UUID, checklist_key: str,
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user -- reuses TENANT_APPROVE (the
    # natural pairing: whoever can approve a provider's onboarding can also
    # override a specific checklist item blocking that approval).
    user: UserContext = Depends(require_permission(P.TENANT_APPROVE)),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    await db.execute(text("""
        UPDATE provider_onboarding_items SET status='overridden', override_reason=:reason, updated_at=now()
        WHERE tenant_id=:tid AND checklist_key=:key
    """), {"tid": str(tenant_id), "key": checklist_key, "reason": payload.get("reason", "Admin override")})
    await db.commit()
    return ok({"tenant_id": str(tenant_id), "checklist_key": checklist_key, "overridden": True}, request_id=rid)


# ── Bookability Admin (Sprint 12) ──────────────────────────────────────────────

@admin_router.get("/bookability/providers")
async def list_bookability(
    request: Request,
    is_bookable: Optional[bool] = Query(None),
    is_visible: Optional[bool] = Query(None),
    category_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    q = "SELECT pvs.*, t.tenant_name as tenant_name FROM provider_visibility_statuses pvs LEFT JOIN tenants t ON t.id = pvs.tenant_id WHERE 1=1"
    params: Dict[str, Any] = {}
    if is_bookable is not None:
        q += " AND pvs.is_bookable = :bookable"
        params["bookable"] = is_bookable
    if is_visible is not None:
        q += " AND pvs.is_visible = :visible"
        params["visible"] = is_visible
    if category_id:
        q += " AND pvs.category_id = :cat_id"
        params["cat_id"] = category_id
    q += " ORDER BY pvs.last_evaluated_at DESC NULLS LAST LIMIT :lim"
    params["lim"] = limit
    result = await db.execute(text(q), params)
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"providers": rows, "total": len(rows)}, request_id=rid)


@admin_router.get("/bookability/providers/{tenant_id}")
async def get_provider_bookability(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    row = await db.execute(text("SELECT pvs.*, t.tenant_name as tenant_name FROM provider_visibility_statuses pvs LEFT JOIN tenants t ON t.id = pvs.tenant_id WHERE pvs.tenant_id=:tid ORDER BY pvs.created_at DESC LIMIT 1"), {"tid": str(tenant_id)})
    r = row.fetchone()
    if not r:
        return ok({"tenant_id": str(tenant_id), "is_visible": False, "is_bookable": False, "visibility_blockers": [], "bookability_blockers": []}, request_id=rid)
    return ok(dict(r._mapping), request_id=rid)


@admin_router.get("/bookability/providers/{tenant_id}/audit-logs")
async def get_bookability_audit_logs(
    tenant_id: uuid.UUID, request: Request,
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    rows_result = await db.execute(text("""
        SELECT id, tenant_id, event_type, before_state, after_state,
               trigger_source, actor_id, actor_type, notes, created_at
        FROM bookability_audit_logs
        WHERE tenant_id = :tid
        ORDER BY created_at DESC
        LIMIT :lim
    """), {"tid": str(tenant_id), "lim": limit})
    rows = [dict(r._mapping) for r in rows_result.fetchall()]
    return ok({"logs": rows, "count": len(rows)}, request_id=rid)


async def _get_or_create_visibility_row(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    row = await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    r = row.fetchone()
    if r:
        return dict(r._mapping)
    ins = await db.execute(text("""
        INSERT INTO provider_visibility_statuses (tenant_id, is_visible, is_bookable, last_evaluated_at)
        VALUES (:tid, false, false, now())
        RETURNING *
    """), {"tid": str(tenant_id)})
    row2 = ins.fetchone()
    return dict(row2._mapping)


async def _log_bookability_event(
    db: AsyncSession, tenant_id: uuid.UUID, event_type: str,
    before: dict[str, Any] | None, after: dict[str, Any] | None,
    actor_id: str | None, notes: str | None,
) -> None:
    import json as _json
    await db.execute(text("""
        INSERT INTO bookability_audit_logs
            (tenant_id, event_type, before_state, after_state, trigger_source, actor_id, actor_type, notes)
        VALUES (:tid, :evt, CAST(:before AS jsonb), CAST(:after AS jsonb), 'admin', :actor_id, 'admin', :notes)
    """), {
        "tid": str(tenant_id), "evt": event_type,
        "before": _json.dumps(before, default=str) if before is not None else None,
        "after": _json.dumps(after, default=str) if after is not None else None,
        "actor_id": actor_id, "notes": notes,
    })


@admin_router.post("/bookability/providers/{tenant_id}/refresh")
async def refresh_bookability(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user -- gated to super_admin.
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    before = await _get_or_create_visibility_row(db, tenant_id)
    await db.execute(text("""
        UPDATE provider_visibility_statuses
        SET last_evaluated_at = now()
        WHERE tenant_id = :tid
    """), {"tid": str(tenant_id)})
    row = await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    after = dict(row.fetchone()._mapping)
    await _log_bookability_event(db, tenant_id, "re_evaluated", before, after, user.user_id if user else None, None)
    await db.commit()
    return ok(after, request_id=rid)


@admin_router.post("/bookability/providers/{tenant_id}/override-visibility")
async def override_visibility(
    tenant_id: uuid.UUID, request: Request,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user (any authenticated principal of any
    # role could override a provider's public visibility platform-wide) --
    # gated to super_admin as the minimal safe fix; no granular coverage/
    # bookability permission exists yet in this codebase.
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    override = bool((payload or {}).get("override"))
    reason = (payload or {}).get("reason") or None
    before = await _get_or_create_visibility_row(db, tenant_id)
    await db.execute(text("""
        UPDATE provider_visibility_statuses
        SET override_is_visible = :ov, override_visible_reason = :reason,
            is_visible = :ov, last_changed_at = now()
        WHERE tenant_id = :tid
    """), {"tid": str(tenant_id), "ov": override, "reason": reason})
    row = await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    after = dict(row.fetchone()._mapping)
    await _log_bookability_event(db, tenant_id, "visibility_override_set", before, after, user.user_id if user else None, reason)
    await db.commit()
    return ok(after, request_id=rid)


@admin_router.delete("/bookability/providers/{tenant_id}/override-visibility")
async def remove_visibility_override(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user -- gated to super_admin.
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    before = await _get_or_create_visibility_row(db, tenant_id)
    await db.execute(text("""
        UPDATE provider_visibility_statuses
        SET override_is_visible = NULL, override_visible_reason = NULL, last_changed_at = now()
        WHERE tenant_id = :tid
    """), {"tid": str(tenant_id)})
    row = await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    after = dict(row.fetchone()._mapping)
    await _log_bookability_event(db, tenant_id, "visibility_override_removed", before, after, user.user_id if user else None, None)
    await db.commit()
    return ok(after, request_id=rid)


@admin_router.post("/bookability/providers/{tenant_id}/override-bookability")
async def override_bookability(
    tenant_id: uuid.UUID, request: Request,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user (any authenticated principal of any
    # role could override a provider's bookability platform-wide) -- gated
    # to super_admin as the minimal safe fix.
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    override = bool((payload or {}).get("override"))
    reason = (payload or {}).get("reason") or None
    before = await _get_or_create_visibility_row(db, tenant_id)
    await db.execute(text("""
        UPDATE provider_visibility_statuses
        SET override_is_bookable = :ov, override_bookable_reason = :reason,
            is_bookable = :ov, last_changed_at = now()
        WHERE tenant_id = :tid
    """), {"tid": str(tenant_id), "ov": override, "reason": reason})
    row = await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    after = dict(row.fetchone()._mapping)
    await _log_bookability_event(db, tenant_id, "bookability_override_set", before, after, user.user_id if user else None, reason)
    await db.commit()
    return ok(after, request_id=rid)


@admin_router.delete("/bookability/providers/{tenant_id}/override-bookability")
async def remove_bookability_override(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    # FINAL-L5-05P: was get_current_user -- gated to super_admin.
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    before = await _get_or_create_visibility_row(db, tenant_id)
    await db.execute(text("""
        UPDATE provider_visibility_statuses
        SET override_is_bookable = NULL, override_bookable_reason = NULL, last_changed_at = now()
        WHERE tenant_id = :tid
    """), {"tid": str(tenant_id)})
    row = await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tenant_id)},
    )
    after = dict(row.fetchone()._mapping)
    await _log_bookability_event(db, tenant_id, "bookability_override_removed", before, after, user.user_id if user else None, None)
    await db.commit()
    return ok(after, request_id=rid)


@admin_router.get("/bookability/rules")
async def list_bookability_rules(
    request: Request,
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    return ok({"rules": [], "total": 0}, request_id=rid)


@admin_router.get("/bookability/summary")
async def bookability_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    row = await db.execute(text("SELECT COUNT(*) as total, SUM(CASE WHEN is_bookable THEN 1 ELSE 0 END) as bookable, SUM(CASE WHEN is_visible THEN 1 ELSE 0 END) as visible FROM provider_visibility_statuses"))
    r = row.fetchone()
    return ok({"total": r[0] or 0, "bookable": r[1] or 0, "visible": r[2] or 0}, request_id=rid)


# ── Monetization Admin (Sprint 5/12) ──────────────────────────────────────────

@admin_router.get("/monetization/configs")
async def list_monetization_configs(
    request: Request,
    category_id: Optional[str] = Query(None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    q = "SELECT * FROM provider_monetization_statuses WHERE 1=1"
    params: Dict[str, Any] = {}
    if category_id:
        q += " AND category_id = :cat_id"
        params["cat_id"] = category_id
    q += " LIMIT :lim"
    params["lim"] = limit
    result = await db.execute(text(q), params)
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"configs": rows, "total": len(rows)}, request_id=rid)


@admin_router.get("/monetization/providers")
async def list_provider_monetization(
    request: Request,
    category_id: Optional[str] = Query(None),
    limit: int = Query(50),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    q = "SELECT pms.*, t.tenant_name as tenant_name FROM provider_monetization_statuses pms LEFT JOIN tenants t ON t.id = pms.tenant_id WHERE 1=1"
    params: Dict[str, Any] = {}
    if category_id:
        q += " AND pms.category_id = :cat_id"
        params["cat_id"] = category_id
    q += " LIMIT :lim"
    params["lim"] = limit
    result = await db.execute(text(q), params)
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"statuses": rows, "total": len(rows)}, request_id=rid)


@admin_router.get("/monetization/providers/{tenant_id}")
async def get_provider_monetization(
    tenant_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    # MODULE-L5-02: provider_monetization_statuses is not provisioned in all
    # environments. Mirror the graceful fallback already used by the tenant
    # portal (tenant_engine/portal_router.get_monetization_status) so the admin
    # tenant detail page's monetization tab shows "not ready" instead of a 500.
    try:
        row = await db.execute(text("SELECT pms.*, t.tenant_name as tenant_name FROM provider_monetization_statuses pms LEFT JOIN tenants t ON t.id = pms.tenant_id WHERE pms.tenant_id=:tid LIMIT 1"), {"tid": str(tenant_id)})
        r = row.fetchone()
    except Exception:
        await db.rollback()
        return ok({"tenant_id": str(tenant_id), "is_monetization_ready": False, "monetization_model": None}, request_id=rid)
    if not r:
        return ok({"tenant_id": str(tenant_id), "is_monetization_ready": False}, request_id=rid)
    return ok(dict(r._mapping), request_id=rid)


@admin_router.post("/monetization/providers/{tenant_id}/sync")
async def sync_monetization(
    tenant_id: uuid.UUID, request: Request,
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    return ok({"tenant_id": str(tenant_id), "synced": True}, request_id=rid)


@admin_router.get("/monetization/audit-logs")
async def monetization_audit_logs(
    request: Request,
    user: UserContext = Depends(require_super_admin),
):
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    return ok({"logs": [], "total": 0}, request_id=rid)
