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
        "SELECT * FROM provider_team_members WHERE id=:sid AND tenant_id=:tid AND deleted_at IS NULL"
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
    return "available"


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
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rows = (await db.execute(text(
        "SELECT * FROM provider_team_members WHERE tenant_id=:tid AND deleted_at IS NULL "
        "ORDER BY full_name ASC"
    ), {"tid": str(tid)})).fetchall()
    members = [dict(r._mapping) for r in rows]

    staff_out = []
    for m in members:
        readiness_result = await compute_member_readiness(db, tid, m)
        jobs_today = await _jobs_today_rows(db, tid, m)
        conflicts = _conflict_count(jobs_today)
        avail = _availability_status(m)
        capacity = _capacity(m, len(jobs_today))
        capacity_state = _capacity_state(readiness_result["status"], capacity, conflicts)

        if search:
            s = search.lower()
            hay = " ".join(filter(None, [m.get("full_name"), m.get("phone"), m.get("email"),
                                          m.get("designation")])).lower()
            if s not in hay:
                continue
        if role and (m.get("member_type") or "").lower() != role.lower():
            continue
        if status and (m.get("status") or "").lower() != status.lower():
            continue
        if availability and avail != availability:
            continue
        if readiness and readiness_result["status"] != readiness:
            continue
        if capability and capability not in (m.get("supported_offering_ids") or []):
            continue

        staff_out.append({
            "staff_id": str(m["id"]),
            "user_id": str(m["user_id"]) if m.get("user_id") else None,
            "name": m["full_name"],
            "photo": m.get("profile_photo_url"),
            "role": m.get("member_type"),
            "employment_status": m.get("status"),
            "verification_status": "verified" if m.get("user_id") else "no_login_configured",
            "availability_status": avail,
            "readiness": readiness_result["status"],
            "readiness_missing": readiness_result["missing"],
            "jobs_today": len(jobs_today),
            **capacity,
            "capacity_state": capacity_state,
            "conflict_count": conflicts,
            "available_actions": ["view", "edit"] + (["deactivate"] if m["status"] == "active" else ["activate"]),
            "version": m["updated_at"].isoformat() if m.get("updated_at") else None,
        })

    total_team = len(staff_out)
    active = sum(1 for s in staff_out if s["employment_status"] == "active")
    technicians = sum(1 for s in staff_out if s["role"] == "technician")
    available_now = sum(1 for s in staff_out if s["availability_status"] == "available")
    setup_incomplete = sum(1 for s in staff_out if s["readiness"] != "ready")
    schedule_conflicts = sum(1 for s in staff_out if s["conflict_count"] > 0)

    page = staff_out[cursor:cursor + limit]
    next_cursor = cursor + limit if cursor + limit < len(staff_out) else None

    return ok({
        "summary": {
            "total_team": total_team, "active": active, "technicians": technicians,
            "available_now": available_now, "setup_incomplete": setup_incomplete,
            "schedule_conflicts": schedule_conflicts,
        },
        "staff": page,
        "pagination": {"cursor": cursor, "limit": limit, "next_cursor": next_cursor, "total": total_team},
        "available_filters": {
            "role": ["technician", "staff", "manager"],
            "status": ["active", "inactive"],
            "availability": ["available", "unavailable"],
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
        "availability_status": _availability_status(m),
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
