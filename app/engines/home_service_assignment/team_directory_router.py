"""Team Directory — Staff & Technicians directory + 360 profile projections.

Reuses the SAME canonical records every other real path already reads:
- ProviderTeamMember (home_service_assignment/staff_model.py) is the roster
  -- now backfilled (migration 197) from real technician/staff Users, so it
  is genuinely populated instead of the empty shadow table it used to be.
- team_readiness_service.compute_member_readiness is the ONE readiness
  authority (also used by onboarding's Staff & Technicians step) -- this
  router never recomputes readiness independently.
- service_jobs / service_job_assignments are the live job/assignment data
  dispatch itself uses.

No new staff, permission, availability or capability engine is introduced.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.home_service_assignment.team_readiness_service import compute_member_readiness
from app.engines.home_service_assignment.team_readiness_service import compute_members_readiness

router = APIRouter(prefix="/v1/tenant/home-services/team", tags=["Tenant Home Services Team"])


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        from fastapi import HTTPException
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


async def _load_member(db: AsyncSession, tid: uuid.UUID, staff_id: uuid.UUID):
    row = (await db.execute(text(
        "SELECT * FROM provider_team_members WHERE tenant_id=:tid AND deleted_at IS NULL AND id=:sid"
    ), {"sid": str(staff_id), "tid": str(tid)})).fetchone()
    if not row:
        raise ServiceOSException("STAFF_NOT_FOUND", "Team member not found.", status_code=404)
    return dict(row._mapping)


async def _jobs_today_rows(db: AsyncSession, tid: uuid.UUID, member: dict) -> list[dict]:
    """Matches assigned_staff_id against EITHER this member's own id or its
    linked user_id -- real service_jobs rows have historically been assigned
    to either id space (see home_service_assignment/service.py::_load_staff),
    so matching only one would silently undercount a technician's jobs."""
    ids = [str(member["id"])]
    if member.get("user_id"):
        ids.append(str(member["user_id"]))
    rows = (await db.execute(text(
        "SELECT id, job_number, status, scheduled_date, scheduled_time_window, offering_id, customer_id "
        "FROM service_jobs WHERE tenant_id=:tid AND assigned_staff_id = ANY(:ids) "
        "AND scheduled_date = CURRENT_DATE AND status NOT IN ('cancelled')"
    ), {"tid": str(tid), "ids": ids})).fetchall()
    return [dict(r._mapping) for r in rows]


def _conflict_count(jobs_today: list[dict]) -> int:
    windows: dict[str, int] = {}
    for j in jobs_today:
        w = j.get("scheduled_time_window")
        if w:
            windows[w] = windows.get(w, 0) + 1
    return sum(1 for c in windows.values() if c > 1)


def _availability_status(member: dict) -> str:
    if member["status"] != "active":
        return "unavailable"
    if not member.get("can_receive_assignment", True):
        return "unavailable"
    return member.get("availability_state") or "available"


def _capacity(member: dict, jobs_today_count: int) -> dict:
    limit = member.get("max_concurrent_jobs") or 4
    used = jobs_today_count
    percentage = round(min(used, limit) / limit * 100) if limit > 0 else 0
    return {"capacity_used": used, "capacity_limit": limit, "capacity_percentage": percentage}


def _capacity_state(readiness_status: str, capacity: dict, conflicts: int) -> str:
    if readiness_status != "ready":
        return "incomplete"
    if conflicts > 0 or capacity["capacity_used"] >= capacity["capacity_limit"]:
        return "at_risk"
    return "ready"


async def _resolved_offering_names(db: AsyncSession, tid: uuid.UUID, offering_ids: list[str]) -> list[dict]:
    if not offering_ids:
        return []
    rows = (await db.execute(text(
        "SELECT ts.id::text AS id, COALESCE(ts.tenant_display_name, ms.service_name) AS name "
        "FROM tenant_services ts JOIN master_services ms ON ms.id = ts.master_service_id "
        "WHERE ts.tenant_id=:tid AND ts.id = ANY(:ids)"
    ), {"tid": str(tid), "ids": offering_ids})).fetchall()
    return [{"id": r.id, "name": r.name} for r in rows]


@router.get("")
async def list_team(
    request: Request,
    search: str | None = Query(None),
    role: str | None = Query(None),
    status: str | None = Query(None),
    availability: str | None = Query(None),
    readiness: str | None = Query(None),
    capability: str | None = Query(None),
    cursor: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    params: dict = {"tid": str(tid), "limit": limit, "cursor": cursor}
    where = ["ptm.tenant_id=:tid", "ptm.deleted_at IS NULL"]
    if search and search.strip():
        params["search"] = f"%{search.strip().lower()}%"
        where.append("(lower(ptm.full_name) LIKE :search OR lower(COALESCE(ptm.email,'')) LIKE :search "
                     "OR lower(COALESCE(ptm.phone,'')) LIKE :search OR lower(COALESCE(ptm.designation,'')) LIKE :search)")
    if role:
        params["role"] = role.lower()
        where.append("lower(ptm.member_type)=:role")
    if status:
        params["status"] = status.lower()
        where.append("lower(ptm.status)=:status")
    if availability:
        if availability == "available":
            where.append("ptm.status='active' AND ptm.can_receive_assignment=true "
                         "AND ptm.availability_state='available' AND NOT EXISTS ("
                         "SELECT 1 FROM staff_time_off sto WHERE sto.tenant_id=ptm.tenant_id "
                         "AND sto.staff_member_id=ptm.id AND sto.status='approved' "
                         "AND CURRENT_DATE BETWEEN sto.start_date AND sto.end_date)")
        elif availability in {"busy", "offline"}:
            params["availability"] = availability
            where.append("ptm.availability_state=:availability")
        elif availability == "unavailable":
            where.append("(ptm.status<>'active' OR ptm.can_receive_assignment=false "
                         "OR ptm.availability_state<>'available' OR EXISTS ("
                         "SELECT 1 FROM staff_time_off sto WHERE sto.tenant_id=ptm.tenant_id "
                         "AND sto.staff_member_id=ptm.id AND sto.status='approved' "
                         "AND CURRENT_DATE BETWEEN sto.start_date AND sto.end_date))")
    if capability:
        params["capability"] = str(capability)
        where.append("COALESCE(ptm.supported_offering_ids, '[]'::jsonb) ? :capability")

    # Readiness is kept server-side so a filtered result remains correctly
    # paginated.  The same facts are resolved by compute_members_readiness
    # for the returned page; these predicates only select the requested set.
    ready_sql = (
        "ptm.status='active' AND NULLIF(trim(ptm.full_name),'') IS NOT NULL "
        "AND (NULLIF(trim(COALESCE(ptm.phone,'')),'') IS NOT NULL OR NULLIF(trim(COALESCE(ptm.email,'')),'') IS NOT NULL) "
        "AND lower(ptm.member_type) IN ('technician','staff','manager') "
        "AND (lower(ptm.member_type)<>'technician' OR ("
        "EXISTS (SELECT 1 FROM tenant_services ts WHERE ts.tenant_id=ptm.tenant_id AND ts.is_enabled=true "
        "AND ts.deleted_at IS NULL AND COALESCE(ptm.supported_offering_ids,'[]'::jsonb) ? ts.id::text) "
        "AND EXISTS (SELECT 1 FROM provider_availability_rules par WHERE par.tenant_id=ptm.tenant_id "
        "AND par.scope_type='staff_member' AND par.scope_id=ptm.id AND par.is_active=true))) "
        "AND (ptm.user_id IS NULL OR COALESCE(u.is_active,true)=true)"
    )
    if readiness:
        if readiness == "ready": where.append(f"({ready_sql})")
        elif readiness == "access_disabled": where.append("ptm.status='inactive'")
        elif readiness == "invitation_pending": where.append("ptm.user_id IS NOT NULL AND COALESCE(u.is_active,false)=false")
        else: where.append(f"NOT ({ready_sql})")

    where_sql = " AND ".join(where)
    count_row = (await db.execute(text(
        f"SELECT count(*) FROM provider_team_members ptm LEFT JOIN users u ON u.id=ptm.user_id WHERE {where_sql}"
    ), params)).scalar()
    total = int(count_row or 0)
    rows = (await db.execute(text(
        f"SELECT ptm.* FROM provider_team_members ptm LEFT JOIN users u ON u.id=ptm.user_id "
        f"WHERE {where_sql} ORDER BY lower(ptm.full_name), ptm.id LIMIT :limit OFFSET :cursor"
    ), params)).fetchall()
    members = [dict(r._mapping) for r in rows]
    readiness_by_member = await compute_members_readiness(db, tid, members)

    member_ids = [str(m["id"]) for m in members]
    jobs_by_member: dict[str, list[dict]] = {mid: [] for mid in member_ids}
    on_leave_ids: set[str] = set()
    if members:
        on_leave_ids = {str(row[0]) for row in (await db.execute(text(
            "SELECT staff_member_id FROM staff_time_off WHERE tenant_id=:tid "
            "AND staff_member_id=ANY(CAST(:ids AS uuid[])) AND status='approved' "
            "AND CURRENT_DATE BETWEEN start_date AND end_date"
        ), {"tid": str(tid), "ids": member_ids})).fetchall()}
        assignment_owner: dict[str, str] = {}
        for m in members:
            assignment_owner[str(m["id"])] = str(m["id"])
            if m.get("user_id"): assignment_owner[str(m["user_id"])] = str(m["id"])
        job_rows = (await db.execute(text(
            "SELECT id, job_number, status, scheduled_time_window, assigned_staff_id::text AS assigned_staff_id "
            "FROM service_jobs WHERE tenant_id=:tid AND scheduled_date=CURRENT_DATE "
            "AND status<>'cancelled' AND assigned_staff_id=ANY(CAST(:ids AS uuid[]))"
        ), {"tid": str(tid), "ids": list(assignment_owner)})).fetchall()
        for row in job_rows:
            owner = assignment_owner.get(row.assigned_staff_id)
            if owner: jobs_by_member[owner].append(dict(row._mapping))

    staff_out = []
    for m in members:
        readiness_result = readiness_by_member[str(m["id"])]
        jobs_today = jobs_by_member[str(m["id"])]
        conflicts = _conflict_count(jobs_today)
        on_leave = str(m["id"]) in on_leave_ids
        presence = m.get("availability_state") or "available"
        avail = "unavailable" if m["status"] != "active" or not m.get("can_receive_assignment", True) or on_leave else presence
        capacity = _capacity(m, len(jobs_today))
        capacity_state = _capacity_state(readiness_result["status"], capacity, conflicts)
        staff_out.append({
            "staff_id": str(m["id"]),
            "user_id": str(m["user_id"]) if m.get("user_id") else None,
            "name": m["full_name"],
            "photo": m.get("profile_photo_url"),
            "role": m.get("member_type"),
            "employment_status": m.get("status"),
            "verification_status": "verified" if m.get("user_id") else "no_login_configured",
            "availability_status": avail,
            "on_leave": on_leave,
            "readiness": readiness_result["status"],
            "readiness_missing": readiness_result["missing"],
            "jobs_today": len(jobs_today),
            **capacity,
            "capacity_state": capacity_state,
            "conflict_count": conflicts,
            "available_actions": ["view", "edit"] + (["deactivate"] if m["status"] == "active" else ["activate"]),
            "version": m["updated_at"].isoformat() if m.get("updated_at") else None,
        })

    summary = (await db.execute(text(f"""
        SELECT count(*) AS total_team,
               count(*) FILTER (WHERE ptm.status='active') AS active,
               count(*) FILTER (WHERE lower(ptm.member_type)='technician') AS technicians,
               count(*) FILTER (WHERE ptm.status='active' AND ptm.can_receive_assignment=true
                 AND ptm.availability_state='available' AND NOT EXISTS (
                   SELECT 1 FROM staff_time_off sto WHERE sto.tenant_id=ptm.tenant_id
                   AND sto.staff_member_id=ptm.id AND sto.status='approved'
                   AND CURRENT_DATE BETWEEN sto.start_date AND sto.end_date)) AS available_now,
               count(*) FILTER (WHERE NOT ({ready_sql})) AS setup_incomplete
        FROM provider_team_members ptm LEFT JOIN users u ON u.id=ptm.user_id
        WHERE ptm.tenant_id=:tid AND ptm.deleted_at IS NULL
    """), {"tid": str(tid)})).one()
    conflict_total = int((await db.execute(text("""
        SELECT count(DISTINCT assigned_staff_id) FROM (
          SELECT assigned_staff_id, scheduled_time_window FROM service_jobs
          WHERE tenant_id=:tid AND scheduled_date=CURRENT_DATE AND assigned_staff_id IS NOT NULL
            AND scheduled_time_window IS NOT NULL AND status<>'cancelled'
          GROUP BY assigned_staff_id, scheduled_time_window HAVING count(*) > 1
        ) conflicts
    """), {"tid": str(tid)})).scalar() or 0)
    next_cursor = cursor + limit if cursor + limit < total else None

    return ok({
        "summary": {
            "total_team": int(summary.total_team), "active": int(summary.active),
            "technicians": int(summary.technicians), "available_now": int(summary.available_now),
            "setup_incomplete": int(summary.setup_incomplete), "schedule_conflicts": conflict_total,
        },
        "staff": staff_out,
        "pagination": {"cursor": cursor, "limit": limit, "next_cursor": next_cursor,
                       "previous_cursor": max(0, cursor - limit) if cursor > 0 else None, "total": total},
        "available_filters": {
            "role": ["technician", "staff", "manager"],
            "status": ["active", "inactive"],
            "availability": ["available", "busy", "offline", "unavailable"],
            "readiness": ["ready", "needs_identity", "needs_role", "needs_service_assignment",
                          "needs_availability", "access_disabled", "offboarded"],
        },
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }, request_id=_rid(request))


@router.get("/{staff_id}/overview")
async def get_overview(
    staff_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    m = await _load_member(db, tid, staff_id)
    readiness_result = await compute_member_readiness(db, tid, m)
    jobs_today = await _jobs_today_rows(db, tid, m)
    conflicts = _conflict_count(jobs_today)

    ids = [str(m["id"])] + ([str(m["user_id"])] if m.get("user_id") else [])
    next_job = (await db.execute(text(
        "SELECT id, job_number, status, scheduled_date, scheduled_time_window, offering_id "
        "FROM service_jobs WHERE tenant_id=:tid AND assigned_staff_id = ANY(:ids) "
        "AND status NOT IN ('cancelled', 'completed') "
        "AND (scheduled_date > CURRENT_DATE OR (scheduled_date = CURRENT_DATE)) "
        "ORDER BY scheduled_date ASC NULLS LAST LIMIT 1"
    ), {"tid": str(tid), "ids": ids})).fetchone()

    login_active = None
    if m.get("user_id"):
        u = (await db.execute(text("SELECT is_active FROM users WHERE id=:uid"),
                               {"uid": str(m["user_id"])})).fetchone()
        login_active = bool(u and u.is_active)

    offerings = await _resolved_offering_names(db, tid, m.get("supported_offering_ids") or [])
    on_leave = bool((await db.execute(text(
        "SELECT 1 FROM staff_time_off WHERE tenant_id=:tid AND staff_member_id=:sid "
        "AND status='approved' AND CURRENT_DATE BETWEEN start_date AND end_date LIMIT 1"
    ), {"tid": str(tid), "sid": str(staff_id)})).first())

    checklist = {
        "identity_verified": "identity" not in readiness_result["missing"],
        "employment_active": m["status"] == "active",
        "capabilities_configured": "service_assignment" not in readiness_result["missing"],
        "availability_configured": "availability" not in readiness_result["missing"],
    }

    return ok({
        "identity": {
            "staff_id": str(m["id"]), "name": m["full_name"], "photo": m.get("profile_photo_url"),
            "role": m.get("member_type"), "designation": m.get("designation"),
            "phone": m.get("phone"), "email": m.get("email"),
        },
        "employment_status": m["status"],
        "login_active": login_active,
        "verification_status": "verified" if m.get("user_id") else "no_login_configured",
        "availability_status": "on_leave" if on_leave else _availability_status(m),
        "on_leave": on_leave,
        "joined_at": m["created_at"].isoformat() if m.get("created_at") else None,
        "readiness": {"status": readiness_result["status"], "missing": readiness_result["missing"],
                      "checklist": checklist},
        "today": {
            **_capacity(m, len(jobs_today)),
            "schedule": [{"job_id": str(j["id"]), "job_number": j["job_number"], "status": j["status"],
                          "time_window": j["scheduled_time_window"]} for j in jobs_today],
        },
        "next_assignment": ({"job_id": str(next_job.id), "job_number": next_job.job_number,
                              "scheduled_date": next_job.scheduled_date.isoformat() if next_job.scheduled_date else None,
                              "time_window": next_job.scheduled_time_window} if next_job else None),
        "schedule_conflicts": conflicts,
        "supported_services": offerings,
    }, request_id=_rid(request))


@router.get("/{staff_id}/capabilities")
async def get_capabilities(
    staff_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    m = await _load_member(db, tid, staff_id)
    offering_ids = m.get("supported_offering_ids") or []
    type_ids = set(m.get("supported_type_ids") or [])
    brand_ids = set(m.get("supported_brand_ids") or [])

    services = []
    if offering_ids:
        rows = (await db.execute(text(
            "SELECT ts.id::text AS offering_id, COALESCE(ts.tenant_display_name, ms.service_name) AS service_name, "
            "ms.is_type_required AS requires_type, ms.is_brand_required AS requires_brand, "
            "sg.name AS service_group_name, sc.name AS category_name "
            "FROM tenant_services ts "
            "JOIN master_services ms ON ms.id = ts.master_service_id "
            "LEFT JOIN service_groups sg ON sg.id = ms.service_group_id "
            "LEFT JOIN service_categories sc ON sc.id = ts.category_id "
            "WHERE ts.tenant_id=:tid AND ts.id = ANY(:ids)"
        ), {"tid": str(tid), "ids": offering_ids})).fetchall()

        for r in rows:
            types = (await db.execute(text(
                "SELECT tst.id::text AS id, st.name AS name FROM tenant_service_types tst "
                "JOIN service_types st ON st.id = tst.service_type_id "
                "WHERE tst.tenant_service_id=:oid AND tst.is_enabled=true"
            ), {"oid": r.offering_id})).fetchall()
            brands = (await db.execute(text(
                "SELECT tsb.id::text AS id, b.name AS name FROM tenant_service_brands tsb "
                "JOIN brands b ON b.id = tsb.brand_id "
                "WHERE tsb.tenant_service_id=:oid AND tsb.is_enabled=true"
            ), {"oid": r.offering_id})).fetchall()

            services.append({
                "vertical": "home_services",
                "service_group": r.service_group_name,
                "category": r.category_name,
                "master_service": r.service_name,
                "offering_id": r.offering_id,
                "requires_type": r.requires_type,
                "requires_brand": r.requires_brand,
                "types": [{"id": t.id, "name": t.name, "supported": (not r.requires_type) or t.id in type_ids}
                          for t in types],
                "brands": [{"id": b.id, "name": b.name, "supported": (not r.requires_brand) or b.id in brand_ids}
                           for b in brands],
            })

    return ok({
        "staff_id": str(m["id"]),
        "role": m.get("member_type"),
        "services": services,
        "raw": {
            "supported_offering_ids": offering_ids,
            "supported_type_ids": list(type_ids),
            "supported_brand_ids": list(brand_ids),
        },
    }, request_id=_rid(request))


@router.get("/{staff_id}/availability")
async def get_staff_availability(
    staff_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    """One staff member's canonical weekly pattern and dated exceptions."""
    tid = _tid(user)
    m = await _load_member(db, tid, staff_id)
    weekly = (await db.execute(text(
        "SELECT id, day_of_week, start_time, end_time, slot_duration_minutes, "
        "max_jobs_per_day, timezone, emergency_available, is_active "
        "FROM provider_availability_rules WHERE tenant_id=:tid AND scope_type='staff_member' "
        "AND scope_id=:sid ORDER BY day_of_week, start_time"
    ), {"tid": str(tid), "sid": str(staff_id)})).fetchall()
    time_off = (await db.execute(text(
        "SELECT id, start_date, end_date, all_day, start_time, end_time, reason, status "
        "FROM staff_time_off WHERE tenant_id=:tid AND staff_member_id=:sid "
        "AND status<>'cancelled' AND end_date>=CURRENT_DATE ORDER BY start_date LIMIT 100"
    ), {"tid": str(tid), "sid": str(staff_id)})).fetchall()
    overrides = (await db.execute(text(
        "SELECT id, override_date, start_time, end_time, full_day_closed, reason "
        "FROM staff_availability_overrides WHERE tenant_id=:tid AND staff_member_id=:sid "
        "AND override_date>=CURRENT_DATE ORDER BY override_date LIMIT 100"
    ), {"tid": str(tid), "sid": str(staff_id)})).fetchall()
    return ok({
        "staff_id": str(staff_id),
        "presence": m.get("availability_state") or "available",
        "presence_updated_at": m.get("availability_updated_at"),
        "can_receive_assignment": bool(m.get("can_receive_assignment")),
        "weekly_rules": [dict(row._mapping) for row in weekly],
        "time_off": [dict(row._mapping) for row in time_off],
        "overrides": [dict(row._mapping) for row in overrides],
    }, request_id=_rid(request))


@router.get("/{staff_id}/jobs")
async def get_staff_jobs(
    staff_id: uuid.UUID, request: Request,
    status: str | None = Query(None),
    search: str | None = Query(None),
    cursor: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    """Paged jobs assigned to the member in either historical id space."""
    tid = _tid(user)
    m = await _load_member(db, tid, staff_id)
    ids = [str(m["id"])] + ([str(m["user_id"])] if m.get("user_id") else [])
    params: dict = {"tid": str(tid), "ids": ids, "cursor": cursor, "limit": limit}
    where = ["sj.tenant_id=:tid", "sj.assigned_staff_id=ANY(CAST(:ids AS uuid[]))"]
    if status:
        params["status"] = status
        where.append("sj.status=:status")
    if search and search.strip():
        params["search"] = f"%{search.strip().lower()}%"
        where.append("(lower(sj.job_number) LIKE :search OR lower(COALESCE(ms.service_name,'')) LIKE :search)")
    where_sql = " AND ".join(where)
    total = int((await db.execute(text(
        f"SELECT count(*) FROM service_jobs sj LEFT JOIN tenant_services ts ON ts.id=sj.offering_id "
        f"LEFT JOIN master_services ms ON ms.id=ts.master_service_id WHERE {where_sql}"
    ), params)).scalar() or 0)
    rows = (await db.execute(text(
        f"SELECT sj.id, sj.job_number, sj.status, sj.assignment_status, sj.scheduled_date, "
        f"sj.scheduled_time_window, sj.city, sj.is_emergency, sj.created_at, "
        f"COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS service_name "
        f"FROM service_jobs sj LEFT JOIN tenant_services ts ON ts.id=sj.offering_id "
        f"LEFT JOIN master_services ms ON ms.id=ts.master_service_id WHERE {where_sql} "
        f"ORDER BY sj.scheduled_date DESC NULLS LAST, sj.created_at DESC, sj.id DESC "
        f"LIMIT :limit OFFSET :cursor"
    ), params)).fetchall()
    return ok({
        "items": [dict(row._mapping) for row in rows],
        "pagination": {"total": total, "cursor": cursor, "limit": limit,
                       "next_cursor": cursor + limit if cursor + limit < total else None,
                       "previous_cursor": max(0, cursor - limit) if cursor else None},
        "available_statuses": ["pending_assignment", "assigned", "accepted", "in_progress", "completed", "cancelled"],
    }, request_id=_rid(request))


@router.get("/{staff_id}/performance")
async def get_staff_performance(
    staff_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    """Operational and customer-rating KPIs from completed service records."""
    tid = _tid(user)
    m = await _load_member(db, tid, staff_id)
    ids = [str(m["id"])] + ([str(m["user_id"])] if m.get("user_id") else [])
    metrics = (await db.execute(text("""
        SELECT count(*) AS total_jobs,
               count(*) FILTER (WHERE status='completed') AS completed_jobs,
               count(*) FILTER (WHERE status='cancelled') AS cancelled_jobs,
               count(*) FILTER (WHERE status='completed' AND updated_at>=now()-interval '30 days') AS completed_last_30_days,
               count(*) FILTER (WHERE is_emergency) AS emergency_jobs,
               max(updated_at) FILTER (WHERE status='completed') AS last_completed_at
        FROM service_jobs WHERE tenant_id=:tid AND assigned_staff_id=ANY(CAST(:ids AS uuid[]))
    """), {"tid": str(tid), "ids": ids})).one()
    rating = (await db.execute(text(
        "SELECT total_reviews, average_rating, communication_average_rating, "
        "punctuality_average_rating, quality_average_rating, last_review_at "
        "FROM staff_rating_summaries WHERE tenant_id=:tid "
        "AND staff_member_id=ANY(CAST(:ids AS uuid[])) ORDER BY total_reviews DESC LIMIT 1"
    ), {"tid": str(tid), "ids": ids})).first()
    completed = int(metrics.completed_jobs or 0)
    total_jobs = int(metrics.total_jobs or 0)
    return ok({
        "staff_id": str(staff_id), "total_jobs": total_jobs, "completed_jobs": completed,
        "cancelled_jobs": int(metrics.cancelled_jobs or 0),
        "completed_last_30_days": int(metrics.completed_last_30_days or 0),
        "emergency_jobs": int(metrics.emergency_jobs or 0),
        "completion_rate": round(completed / total_jobs * 100, 1) if total_jobs else 0,
        "last_completed_at": metrics.last_completed_at,
        "ratings": dict(rating._mapping) if rating else {
            "total_reviews": 0, "average_rating": 0, "communication_average_rating": 0,
            "punctuality_average_rating": 0, "quality_average_rating": 0, "last_review_at": None,
        },
    }, request_id=_rid(request))


@router.get("/{staff_id}/documents")
async def get_staff_documents(
    staff_id: uuid.UUID, request: Request,
    status: str | None = Query(None), doc_type: str | None = Query(None), search: str | None = Query(None),
    cursor: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    await _load_member(db, tid, staff_id)
    params = {"tid": str(tid), "sid": str(staff_id), "cursor": cursor, "limit": limit}
    where = ["tenant_id=:tid", "staff_member_id=:sid", "is_current=true"]
    if status:
        params["status"] = status
        where.append("status=:status")
    if doc_type:
        params["doc_type"] = doc_type
        where.append("doc_type=:doc_type")
    if search and search.strip():
        params["search"] = f"%{search.strip().lower()}%"
        where.append("(lower(COALESCE(label,'')) LIKE :search OR lower(doc_type) LIKE :search)")
    where_sql = " AND ".join(where)
    total = int((await db.execute(text(
        f"SELECT count(*) FROM tenant_documents WHERE {where_sql}"
    ), params)).scalar() or 0)
    rows = (await db.execute(text(
        "SELECT id, doc_type, label, file_url, status, expiry_date, verified_at, rejection_reason, created_at "
        f"FROM tenant_documents WHERE {where_sql} "
        "ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :cursor"
    ), params)).fetchall()
    return ok({"items": [dict(row._mapping) for row in rows],
               "pagination": {"total": total, "cursor": cursor, "limit": limit,
                              "next_cursor": cursor + limit if cursor + limit < total else None}},
              request_id=_rid(request))


@router.get("/{staff_id}/activity")
async def get_staff_activity(
    staff_id: uuid.UUID, request: Request,
    search: str | None = Query(None),
    cursor: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    m = await _load_member(db, tid, staff_id)
    entity_ids = [str(staff_id)] + ([str(m["user_id"])] if m.get("user_id") else [])
    params = {"tid": str(tid), "ids": entity_ids, "cursor": cursor, "limit": limit}
    where = ["tenant_id=:tid", "entity_id=ANY(:ids)"]
    if search and search.strip():
        params["search"] = f"%{search.strip().lower()}%"
        where.append("(lower(operation) LIKE :search OR lower(engine_id) LIKE :search OR lower(COALESCE(actor_role,'')) LIKE :search)")
    where_sql = " AND ".join(where)
    total = int((await db.execute(text(
        f"SELECT count(*) FROM platform_audit_logs WHERE {where_sql}"
    ), params)).scalar() or 0)
    rows = (await db.execute(text(
        "SELECT id, operation, engine_id, entity_type, entity_id, actor_role, is_high_risk, created_at "
        f"FROM platform_audit_logs WHERE {where_sql} "
        "ORDER BY created_at DESC, id DESC LIMIT :limit OFFSET :cursor"
    ), params)).fetchall()
    return ok({"items": [dict(row._mapping) for row in rows],
               "pagination": {"total": total, "cursor": cursor, "limit": limit,
                              "next_cursor": cursor + limit if cursor + limit < total else None}},
              request_id=_rid(request))
