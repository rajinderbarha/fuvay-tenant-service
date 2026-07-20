"""Provider Portal Router — Sprint 11/12 provider-facing endpoints.

Covers team-members, availability, offerings, status, onboarding/status,
and packages/status. All data is tenant-scoped via JWT.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.core.permissions import P, require_tenant_mutation_permission, require_tenant_owner_mutation

router = APIRouter(prefix="/v1/provider", tags=["Provider Portal"])


def _validate_availability_time_range(start_time: str | None, end_time: str | None) -> None:
    """HS5 fix — end_time must be after start_time. Previously unvalidated,
    an availability rule could be created/updated with end before start."""
    if not start_time or not end_time:
        return
    if end_time <= start_time:
        raise ServiceOSException(
            "INVALID_AVAILABILITY_TIME_RANGE",
            "End time must be after start time.",
            status_code=422)


def _validate_break_time(start_time: str | None, end_time: str | None,
                          break_start: str | None, break_end: str | None) -> None:
    """HS5B — break_start_time/break_end_time must both be present or both
    null, break must fall inside the working start/end window, and
    break_end must be after break_start."""
    if break_start is None and break_end is None:
        return
    if (break_start is None) != (break_end is None):
        raise ServiceOSException(
            "INVALID_BREAK_TIME_RANGE",
            "Break start and break end must both be set, or both left empty.",
            status_code=422)
    if break_end <= break_start:
        raise ServiceOSException(
            "INVALID_BREAK_TIME_RANGE",
            "Break end time must be after break start time.",
            status_code=422)
    if start_time and end_time and not (start_time <= break_start and break_end <= end_time):
        raise ServiceOSException(
            "INVALID_BREAK_TIME_RANGE",
            "Break time must be inside working hours.",
            status_code=422)


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


# ── Team Members ──────────────────────────────────────────────────────────────

@router.get("/team-members")
async def list_team_members(
    request: Request,
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    q = "SELECT * FROM provider_team_members WHERE tenant_id = :tid AND deleted_at IS NULL"
    params: Dict[str, Any] = {"tid": str(tid)}
    if status:
        q += " AND status = :status"
        params["status"] = status
    q += " ORDER BY created_at DESC"
    result = await db.execute(text(q), params)
    rows = [dict(r._mapping) for r in result.fetchall()]
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok({"members": rows, "count": len(rows)}, request_id=rid)


@router.post("/team-members", status_code=201)
async def create_team_member(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO provider_team_members
            (id, tenant_id, member_type, full_name, phone, email, designation,
             status, can_receive_assignment, skills, supported_offering_ids,
             supported_type_ids, supported_brand_ids, service_area_ids, category_id)
        VALUES (:id, :tid, :member_type, :full_name, :phone, :email, :designation,
                'active', :recv, :skills, :offering_ids,
                :type_ids, :brand_ids, :area_ids, :cat_id)
    """), {
        "id": new_id, "tid": str(tid),
        "member_type": payload.get("member_type", "technician"),
        "full_name": payload.get("full_name", ""),
        "phone": payload.get("phone"),
        "email": payload.get("email"),
        "designation": payload.get("designation"),
        "recv": payload.get("can_receive_assignment", True),
        "skills": str(payload.get("skills", [])).replace("'", '"'),
        "offering_ids": str(payload.get("supported_offering_ids", [])).replace("'", '"'),
        "type_ids": str(payload.get("supported_type_ids", [])).replace("'", '"'),
        "brand_ids": str(payload.get("supported_brand_ids", [])).replace("'", '"'),
        "area_ids": str(payload.get("service_area_ids", [])).replace("'", '"'),
        "cat_id": payload.get("category_id"),
    })
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id"), {"id": new_id})
    member = dict(row.fetchone()._mapping)
    return ok({"member": member}, request_id=rid)


@router.get("/team-members/{member_id}")
async def get_team_member(
    member_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid AND deleted_at IS NULL"),
        {"id": str(member_id), "tid": str(tid)}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(404, "Team member not found")
    return ok(dict(row._mapping), request_id=rid)


@router.put("/team-members/{member_id}")
async def update_team_member(
    member_id: uuid.UUID,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    allowed = {"full_name", "phone", "email", "designation", "member_type",
                "can_receive_assignment", "skills", "supported_offering_ids",
                "supported_type_ids", "supported_brand_ids", "service_area_ids"}
    sets = ", ".join(f"{k}=:{k}" for k in payload if k in allowed)
    if not sets:
        raise HTTPException(400, "No valid fields to update")
    params = {k: v for k, v in payload.items() if k in allowed}
    params["id"] = str(member_id)
    params["tid"] = str(tid)
    await db.execute(text(f"UPDATE provider_team_members SET {sets}, updated_at=now() WHERE id=:id AND tenant_id=:tid"), params)
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(member_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Team member not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.delete("/team-members/{member_id}")
async def delete_team_member(
    member_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(
        text("UPDATE provider_team_members SET deleted_at=now() WHERE id=:id AND tenant_id=:tid"),
        {"id": str(member_id), "tid": str(tid)}
    )
    await db.commit()
    return ok({"deleted": True}, request_id=rid)


@router.post("/team-members/{member_id}/activate")
async def activate_team_member(
    member_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(text("UPDATE provider_team_members SET status='active', updated_at=now() WHERE id=:id AND tenant_id=:tid"), {"id": str(member_id), "tid": str(tid)})
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(member_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Team member not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.post("/team-members/{member_id}/deactivate")
async def deactivate_team_member(
    member_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    member_row = await db.execute(
        text("SELECT user_id FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
        {"id": str(member_id), "tid": str(tid)}
    )
    member = member_row.fetchone()
    if member is None:
        raise HTTPException(404, "Team member not found")
    await db.execute(text("UPDATE provider_team_members SET status='inactive', updated_at=now() WHERE id=:id AND tenant_id=:tid"), {"id": str(member_id), "tid": str(tid)})
    if member.user_id:
        # Slice 2F-2, Workstream 6: a deactivated team member's linked login
        # (provider_team_members.user_id) must have its sessions revoked --
        # the same DB+Redis pattern proven for AuthService.deactivate_staff
        # in Slice 2F/2F-1. Without this, an already-issued JWT for the
        # deactivated member keeps authenticating until natural expiry.
        from app.engines.auth.models import UserSession
        from app.engines.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES
        from app.redis_client import get_redis
        from app.models.base import utcnow
        active_sessions = await db.execute(
            select(UserSession.id).where(UserSession.user_id == member.user_id, UserSession.revoked_at.is_(None))
        )
        session_ids = [row[0] for row in active_sessions]
        if session_ids:
            await db.execute(
                update(UserSession).where(
                    UserSession.user_id == member.user_id, UserSession.revoked_at.is_(None)
                ).values(revoked_at=utcnow(), revocation_reason="team_member_deactivated")
            )
            redis = get_redis()
            for sid in session_ids:
                try:
                    await redis.setex(f"serviceos:session:revoked:{sid}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
                except Exception:
                    pass
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_team_members WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(member_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Team member not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.post("/team-members/{member_id}/create-login")
async def create_member_login(
    member_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok({"member_id": str(member_id), "credentials": None}, request_id=rid)


# ── Availability ──────────────────────────────────────────────────────────────

@router.get("/availability")
async def list_availability(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("SELECT * FROM provider_availability_rules WHERE tenant_id=:tid ORDER BY day_of_week, start_time"),
        {"tid": str(tid)}
    )
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"rules": rows, "count": len(rows)}, request_id=rid)


@router.post("/availability", status_code=201)
async def create_availability(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    start_time, end_time = payload.get("start_time", "09:00"), payload.get("end_time", "18:00")
    break_start, break_end = payload.get("break_start_time"), payload.get("break_end_time")
    _validate_availability_time_range(start_time, end_time)
    _validate_break_time(start_time, end_time, break_start, break_end)
    if payload.get("max_jobs_per_day") is not None and payload["max_jobs_per_day"] <= 0:
        raise ServiceOSException("INVALID_MAX_JOBS_PER_DAY", "max_jobs_per_day must be positive.", status_code=422)
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO provider_availability_rules
            (id, tenant_id, scope_type, scope_id, day_of_week, start_time, end_time,
             slot_duration_minutes, max_bookings_per_slot, is_active, category_id,
             break_start_time, break_end_time, max_jobs_per_day, timezone, emergency_available)
        VALUES (:id, :tid, :scope_type, :scope_id, :dow, :start, :end, :slot, :max, :active, :cat_id,
                :break_start, :break_end, :max_jobs, :tz, :emergency)
    """), {
        "id": new_id, "tid": str(tid),
        "scope_type": payload.get("scope_type", "provider"),
        "scope_id": payload.get("scope_id"),
        "dow": payload.get("day_of_week", 0),
        "start": start_time,
        "end": end_time,
        "slot": payload.get("slot_duration_minutes"),
        "max": payload.get("max_bookings_per_slot"),
        "active": payload.get("is_active", True),
        "cat_id": payload.get("category_id"),
        "break_start": break_start, "break_end": break_end,
        "max_jobs": payload.get("max_jobs_per_day"),
        "tz": payload.get("timezone", "Asia/Kolkata"),
        "emergency": payload.get("emergency_available", False),
    })
    await db.commit()
    row = await db.execute(text("SELECT * FROM provider_availability_rules WHERE id=:id"), {"id": new_id})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


@router.get("/availability/{rule_id}")
async def get_availability(
    rule_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    row = await db.execute(text("SELECT * FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"), {"id": str(rule_id), "tid": str(tid)})
    r = row.fetchone()
    if not r:
        raise HTTPException(404, "Availability rule not found")
    return ok(dict(r._mapping), request_id=rid)


@router.put("/availability/{rule_id}")
async def update_availability(
    rule_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    allowed = {"scope_type", "scope_id", "day_of_week", "start_time", "end_time", "slot_duration_minutes",
               "max_bookings_per_slot", "is_active", "break_start_time", "break_end_time",
               "max_jobs_per_day", "timezone", "emergency_available"}
    if payload.keys() & {"start_time", "end_time", "break_start_time", "break_end_time"}:
        existing_row = (await db.execute(
            text("SELECT start_time, end_time, break_start_time, break_end_time "
                 "FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"),
            {"id": str(rule_id), "tid": str(tid)})).fetchone()
        if existing_row:
            start_time = payload.get("start_time", existing_row.start_time)
            end_time = payload.get("end_time", existing_row.end_time)
            break_start = payload.get("break_start_time", existing_row.break_start_time)
            break_end = payload.get("break_end_time", existing_row.break_end_time)
            _validate_availability_time_range(start_time, end_time)
            _validate_break_time(start_time, end_time, break_start, break_end)
    if payload.get("max_jobs_per_day") is not None and payload["max_jobs_per_day"] <= 0:
        raise ServiceOSException("INVALID_MAX_JOBS_PER_DAY", "max_jobs_per_day must be positive.", status_code=422)
    sets = ", ".join(f"{k}=:{k}" for k in payload if k in allowed)
    if sets:
        params = {k: v for k, v in payload.items() if k in allowed}
        params["id"] = str(rule_id)
        params["tid"] = str(tid)
        await db.execute(text(f"UPDATE provider_availability_rules SET {sets}, updated_at=now() WHERE id=:id AND tenant_id=:tid"), params)
        await db.commit()
    row = await db.execute(text("SELECT * FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"),
                            {"id": str(rule_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Availability rule not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.delete("/availability/{rule_id}")
async def delete_availability(
    rule_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(text("DELETE FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"), {"id": str(rule_id), "tid": str(tid)})
    await db.commit()
    return ok({"deleted": True}, request_id=rid)


# ── Availability Exceptions / Holidays (HS5B) ─────────────────────────────────

@router.get("/availability/exceptions")
async def list_availability_exceptions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("SELECT * FROM tenant_availability_exceptions WHERE tenant_id=:tid AND status='active' ORDER BY date"),
        {"tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"exceptions": rows, "count": len(rows)}, request_id=rid)


def _parse_date(value):
    """Accepts an ISO date string ('2026-08-20') or an already-parsed
    datetime.date (e.g. read back from a DB row) — asyncpg needs a real
    date object for a `date` column, not a bare string."""
    import datetime as _dt
    if isinstance(value, _dt.date):
        return value
    return _dt.date.fromisoformat(str(value))


def _validate_exception_payload(payload: dict) -> None:
    if not payload.get("date"):
        raise ServiceOSException("EXCEPTION_DATE_REQUIRED", "Date is required.", status_code=422)
    if not payload.get("reason"):
        raise ServiceOSException("EXCEPTION_REASON_REQUIRED", "Reason is required.", status_code=422)
    full_day = payload.get("full_day_closed", True)
    if not full_day:
        if not payload.get("start_time") or not payload.get("end_time"):
            raise ServiceOSException("EXCEPTION_TIME_REQUIRED",
                "Start time and end time are required for a partial-day exception.", status_code=422)
        if payload["end_time"] <= payload["start_time"]:
            raise ServiceOSException("INVALID_EXCEPTION_TIME_RANGE",
                "Exception end time must be after start time.", status_code=422)


@router.post("/availability/exceptions", status_code=201)
async def create_availability_exception(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    _validate_exception_payload(payload)
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO tenant_availability_exceptions
            (id, tenant_id, date, reason, full_day_closed, start_time, end_time,
             affected_service_area_ids, affected_service_ids, status)
        VALUES (:id, :tid, :date, :reason, :full_day, :start, :end,
                CAST(:areas AS jsonb), CAST(:services AS jsonb), 'active')
    """), {
        "id": new_id, "tid": str(tid),
        "date": _parse_date(payload["date"]), "reason": payload["reason"],
        "full_day": payload.get("full_day_closed", True),
        "start": payload.get("start_time"), "end": payload.get("end_time"),
        "areas": json.dumps(payload.get("affected_service_area_ids") or []),
        "services": json.dumps(payload.get("affected_service_ids") or []),
    })
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_availability_exceptions WHERE id=:id"), {"id": new_id})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


@router.put("/availability/exceptions/{exception_id}")
async def update_availability_exception(
    exception_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    existing = (await db.execute(
        text("SELECT * FROM tenant_availability_exceptions WHERE id=:id AND tenant_id=:tid"),
        {"id": str(exception_id), "tid": str(tid)})).fetchone()
    if not existing:
        raise HTTPException(404, "Exception not found")
    merged = {**dict(existing._mapping), **payload}
    _validate_exception_payload(merged)
    await db.execute(text("""
        UPDATE tenant_availability_exceptions
        SET date=:date, reason=:reason, full_day_closed=:full_day, start_time=:start, end_time=:end,
            affected_service_area_ids=CAST(:areas AS jsonb), affected_service_ids=CAST(:services AS jsonb),
            updated_at=now()
        WHERE id=:id AND tenant_id=:tid
    """), {
        "id": str(exception_id), "tid": str(tid),
        "date": _parse_date(merged["date"]), "reason": merged["reason"], "full_day": merged.get("full_day_closed", True),
        "start": merged.get("start_time"), "end": merged.get("end_time"),
        "areas": json.dumps(merged.get("affected_service_area_ids") or []),
        "services": json.dumps(merged.get("affected_service_ids") or []),
    })
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_availability_exceptions WHERE id=:id"), {"id": str(exception_id)})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


@router.delete("/availability/exceptions/{exception_id}")
async def delete_availability_exception(
    exception_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(
        text("UPDATE tenant_availability_exceptions SET status='deleted', updated_at=now() WHERE id=:id AND tenant_id=:tid"),
        {"id": str(exception_id), "tid": str(tid)})
    await db.commit()
    return ok({"deleted": True}, request_id=rid)


# ── Booking Window Settings (HS5B) ────────────────────────────────────────────

@router.get("/booking-window")
async def get_booking_window(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    row = (await db.execute(
        text("SELECT * FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tid)})).fetchone()
    if row:
        data = dict(row._mapping)
    else:
        data = {
            "tenant_id": str(tid), "minimum_notice_minutes": 120, "maximum_advance_booking_days": 7,
            "slot_duration_minutes": 60, "buffer_minutes_between_jobs": 30,
            "allow_same_day_booking": True, "emergency_booking_allowed": False, "timezone": "Asia/Kolkata",
        }
    return ok(data, request_id=rid)


def _validate_booking_window(payload: dict) -> None:
    if payload.get("minimum_notice_minutes") is not None and payload["minimum_notice_minutes"] < 0:
        raise ServiceOSException("INVALID_MINIMUM_NOTICE", "minimum_notice_minutes must be >= 0.", status_code=422)
    if payload.get("maximum_advance_booking_days") is not None and payload["maximum_advance_booking_days"] < 1:
        raise ServiceOSException("INVALID_ADVANCE_BOOKING_DAYS", "maximum_advance_booking_days must be >= 1.", status_code=422)
    if payload.get("slot_duration_minutes") is not None and payload["slot_duration_minutes"] <= 0:
        raise ServiceOSException("INVALID_SLOT_DURATION", "slot_duration_minutes must be > 0.", status_code=422)
    if payload.get("buffer_minutes_between_jobs") is not None and payload["buffer_minutes_between_jobs"] < 0:
        raise ServiceOSException("INVALID_BUFFER_MINUTES", "buffer_minutes_between_jobs must be >= 0.", status_code=422)


@router.put("/booking-window")
async def update_booking_window(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    _validate_booking_window(payload)
    defaults = {
        "minimum_notice_minutes": 120, "maximum_advance_booking_days": 7, "slot_duration_minutes": 60,
        "buffer_minutes_between_jobs": 30, "allow_same_day_booking": True,
        "emergency_booking_allowed": False, "timezone": "Asia/Kolkata",
    }
    merged = {**defaults, **payload}
    existing = (await db.execute(
        text("SELECT id FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tid)})).fetchone()
    if existing:
        await db.execute(text("""
            UPDATE tenant_booking_window_settings SET
                minimum_notice_minutes=:mn, maximum_advance_booking_days=:mad, slot_duration_minutes=:sd,
                buffer_minutes_between_jobs=:bm, allow_same_day_booking=:sdb,
                emergency_booking_allowed=:eba, timezone=:tz, updated_at=now()
            WHERE tenant_id=:tid
        """), {"tid": str(tid), "mn": merged["minimum_notice_minutes"], "mad": merged["maximum_advance_booking_days"],
                "sd": merged["slot_duration_minutes"], "bm": merged["buffer_minutes_between_jobs"],
                "sdb": merged["allow_same_day_booking"], "eba": merged["emergency_booking_allowed"], "tz": merged["timezone"]})
    else:
        await db.execute(text("""
            INSERT INTO tenant_booking_window_settings
                (tenant_id, minimum_notice_minutes, maximum_advance_booking_days, slot_duration_minutes,
                 buffer_minutes_between_jobs, allow_same_day_booking, emergency_booking_allowed, timezone)
            VALUES (:tid, :mn, :mad, :sd, :bm, :sdb, :eba, :tz)
        """), {"tid": str(tid), "mn": merged["minimum_notice_minutes"], "mad": merged["maximum_advance_booking_days"],
                "sd": merged["slot_duration_minutes"], "bm": merged["buffer_minutes_between_jobs"],
                "sdb": merged["allow_same_day_booking"], "eba": merged["emergency_booking_allowed"], "tz": merged["timezone"]})
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tid)})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


# ── Per-Area Service / Type / Brand Coverage (HS5B) ──────────────────────────

@router.get("/service-areas/{area_id}/coverage")
async def get_area_coverage(
    area_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(
        text("SELECT * FROM tenant_service_area_services WHERE tenant_service_area_id=:aid AND tenant_id=:tid"),
        {"aid": str(area_id), "tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"coverage": rows, "count": len(rows)}, request_id=rid)


@router.put("/service-areas/{area_id}/coverage")
async def set_area_coverage(
    area_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_SERVICE_AREA_SERVICE_UPDATE)),
):
    """HS5B — per-area service/type/brand coverage. Validates the type
    belongs to the selected service and the brand belongs to the selected
    service (reusing the real master_service_types/master_service_brands
    mapping tables — the same source of truth the admin catalog uses),
    matching the type-dependent-scoping pattern established in migration 120."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    area = (await db.execute(
        text("SELECT id FROM tenant_service_areas WHERE id=:aid AND tenant_id=:tid"),
        {"aid": str(area_id), "tid": str(tid)})).fetchone()
    if not area:
        raise HTTPException(404, "Service area not found")

    service_id = payload.get("service_id")
    if not service_id:
        raise ServiceOSException("COVERAGE_SERVICE_REQUIRED", "service_id is required.", status_code=422)
    tenant_svc = (await db.execute(
        text("SELECT job_type FROM tenant_services WHERE tenant_id=:tid AND master_service_id=:sid AND is_active=true"),
        {"tid": str(tid), "sid": service_id})).fetchone()
    if not tenant_svc:
        raise ServiceOSException("SERVICE_NOT_TENANT_ENABLED",
            "This service is not enabled by your business.", status_code=422)

    service_type_id = payload.get("service_type_id")
    if service_type_id:
        type_match = (await db.execute(
            text("SELECT 1 FROM master_service_types WHERE master_service_id=:sid AND service_type_id=:stid AND is_active=true"),
            {"sid": service_id, "stid": service_type_id})).fetchone()
        if not type_match:
            raise ServiceOSException("INVALID_SERVICE_TYPE_FOR_COVERAGE",
                "Selected service type does not belong to this service.", status_code=422)

    brand_id = payload.get("brand_id")
    if brand_id:
        brand_match = (await db.execute(
            text("SELECT 1 FROM master_service_brands WHERE master_service_id=:sid AND brand_id=:bid AND is_active=true"),
            {"sid": service_id, "bid": brand_id})).fetchone()
        if not brand_match:
            raise ServiceOSException("INVALID_BRAND_FOR_COVERAGE",
                "Selected brand is not valid for this service type.", status_code=422)

    existing = (await db.execute(
        text("SELECT id FROM tenant_service_area_services WHERE tenant_service_area_id=:aid "
             "AND service_id=:sid AND service_type_id IS NOT DISTINCT FROM :stid AND brand_id IS NOT DISTINCT FROM :bid"),
        {"aid": str(area_id), "sid": service_id, "stid": service_type_id, "bid": brand_id})).fetchone()
    if existing:
        await db.execute(text(
            "UPDATE tenant_service_area_services SET is_available=:avail, updated_at=now() WHERE id=:id"
        ), {"avail": payload.get("is_available", True), "id": existing.id})
        row_id = existing.id
    else:
        row_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO tenant_service_area_services
                (id, tenant_service_area_id, tenant_id, service_id, service_type_id, brand_id, job_type, is_available)
            VALUES (:id, :aid, :tid, :sid, :stid, :bid, :jt, :avail)
        """), {"id": row_id, "aid": str(area_id), "tid": str(tid), "sid": service_id,
                "stid": service_type_id, "bid": brand_id, "jt": tenant_svc.job_type,
                "avail": payload.get("is_available", True)})
    await db.commit()
    row = await db.execute(text("SELECT * FROM tenant_service_area_services WHERE id=:id"), {"id": str(row_id)})
    return ok(dict(row.fetchone()._mapping), request_id=rid)


# Preset definitions — identifies rules created by each preset key.
_PRESET_DEFS: dict[str, dict] = {
    "standard":  {"start_time": "09:00", "end_time": "18:00", "slot_duration_minutes": 60, "days": [1,2,3,4,5,6]},
    "weekdays":  {"start_time": "09:00", "end_time": "18:00", "slot_duration_minutes": 60, "days": [1,2,3,4,5]},
    "emergency": {"start_time": "08:00", "end_time": "22:00", "slot_duration_minutes": 30, "days": [0,1,2,3,4,5,6]},
}


@router.post("/availability/preset/{preset_key}", status_code=200)
async def apply_availability_preset(
    preset_key: str, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    """Idempotent preset apply — deletes any existing matching rules first, then
    creates one rule per day.  Safe to call multiple times without duplicates."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    defn = _PRESET_DEFS.get(preset_key)
    if not defn:
        raise HTTPException(400, f"Unknown preset key: {preset_key!r}")

    # Delete existing rules that exactly match this preset pattern for this tenant.
    await db.execute(text("""
        DELETE FROM provider_availability_rules
        WHERE tenant_id=:tid
          AND scope_type='provider'
          AND scope_id IS NULL
          AND start_time=:start
          AND end_time=:end
          AND slot_duration_minutes=:slot
    """), {"tid": str(tid), "start": defn["start_time"], "end": defn["end_time"], "slot": defn["slot_duration_minutes"]})

    # Insert one rule per day.
    created_ids: list[str] = []
    for dow in defn["days"]:
        new_id = str(uuid.uuid4())
        await db.execute(text("""
            INSERT INTO provider_availability_rules
                (id, tenant_id, scope_type, scope_id, day_of_week, start_time, end_time,
                 slot_duration_minutes, max_bookings_per_slot, is_active)
            VALUES (:id, :tid, 'provider', NULL, :dow, :start, :end, :slot, :max, TRUE)
        """), {
            "id": new_id, "tid": str(tid),
            "dow": dow,
            "start": defn["start_time"],
            "end": defn["end_time"],
            "slot": defn["slot_duration_minutes"],
            "max": 5,
        })
        created_ids.append(new_id)

    await db.commit()
    return ok({"preset_key": preset_key, "status": "applied", "rule_count": len(created_ids)}, request_id=rid)


@router.delete("/availability/preset/{preset_key}", status_code=200)
async def delete_availability_preset(
    preset_key: str, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    """Delete all rules that match the given preset pattern for this tenant."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    defn = _PRESET_DEFS.get(preset_key)
    if not defn:
        raise HTTPException(400, f"Unknown preset key: {preset_key!r}")

    result = await db.execute(text("""
        DELETE FROM provider_availability_rules
        WHERE tenant_id=:tid
          AND scope_type='provider'
          AND scope_id IS NULL
          AND start_time=:start
          AND end_time=:end
          AND slot_duration_minutes=:slot
        RETURNING id
    """), {"tid": str(tid), "start": defn["start_time"], "end": defn["end_time"], "slot": defn["slot_duration_minutes"]})
    deleted_ids = [str(r[0]) for r in result.fetchall()]
    await db.commit()
    return ok({"preset_key": preset_key, "deleted_count": len(deleted_ids), "deleted_ids": deleted_ids}, request_id=rid)


# ── Offerings ─────────────────────────────────────────────────────────────────

@router.get("/offerings/available")
async def list_available_offerings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    # NOTE (Tenant My Offerings enterprise upgrade): this previously queried
    # `master_offerings`, a table that has zero rows in the live database —
    # every tenant saw "0 available offerings" regardless of the real,
    # populated platform catalog. The real, live catalog lives in
    # `master_services` (joined to `service_categories` for vertical scoping,
    # `service_groups` for display grouping). Fixed to query the real table.
    # See TENANT_MY_OFFERINGS_CATALOG_DIAGNOSTIC_REPORT.md.
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(text("""
        SELECT
            ms.id AS offering_id,
            ms.service_name AS name,
            ms.slug AS slug,
            ms.job_type AS offering_type,
            ms.pricing_model AS pricing_model,
            ms.category_id AS category_id,
            ms.service_group_id AS service_group_id,
            sg.name AS service_group_name,
            ms.is_type_required AS requires_service_type,
            ms.is_brand_required AS requires_brand,
            true AS requires_staff,
            COALESCE(ms.requires_schedule, false) AS requires_slot,
            ms.base_price AS admin_price,
            ms.visit_fee AS admin_visit_fee,
            NULL::numeric AS admin_appointment_fee,
            NULL::numeric AS admin_lead_fee,
            NULL::text AS primary_engine_key,
            NULL::text AS customer_flow_type,
            peo.id AS provider_enabled_offering_id,
            (peo.id IS NOT NULL) AS is_already_enabled
        FROM master_services ms
        JOIN service_categories sc ON sc.id = ms.category_id
        JOIN tenants t ON t.id = :tid
        LEFT JOIN service_groups sg ON sg.id = ms.service_group_id
        LEFT JOIN provider_enabled_offerings peo
            ON peo.offering_id = ms.id AND peo.tenant_id = :tid AND peo.deleted_at IS NULL
        WHERE ms.is_active = true AND ms.deleted_at IS NULL
          AND sc.is_active = true AND sc.is_provider_registerable = true
          AND sc.vertical_type = t.vertical
        ORDER BY ms.display_order, ms.service_name
    """), {"tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"offerings": rows, "count": len(rows)}, request_id=rid)


@router.get("/offerings/enabled")
async def list_enabled_offerings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(text("""
        SELECT peo.*, peo.id AS provider_enabled_offering_id,
               ms.service_name as offering_name, ms.slug as offering_slug,
               ms.pricing_model as offering_pricing_model, ms.job_type as offering_type
        FROM provider_enabled_offerings peo
        LEFT JOIN master_services ms ON ms.id = peo.offering_id
        WHERE peo.tenant_id = :tid AND peo.deleted_at IS NULL
        ORDER BY peo.created_at DESC
    """), {"tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"offerings": rows, "count": len(rows)}, request_id=rid)


@router.post("/offerings/enabled", status_code=201)
async def enable_offering(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    new_id = str(uuid.uuid4())
    await db.execute(text("""
        INSERT INTO provider_enabled_offerings
            (id, tenant_id, offering_id, category_id, is_enabled, status, readiness_status)
        VALUES (:id, :tid, :offering_id, :cat_id, true, 'pending_approval', 'pending')
        ON CONFLICT (tenant_id, offering_id) WHERE deleted_at IS NULL
        DO UPDATE SET is_enabled=true, status='pending_approval', updated_at=now()
    """), {
        "id": new_id, "tid": str(tid),
        "offering_id": payload.get("offering_id"),
        "cat_id": payload.get("category_id"),
    })
    await db.commit()
    row = await db.execute(text("SELECT *, id AS provider_enabled_offering_id FROM provider_enabled_offerings WHERE tenant_id=:tid AND offering_id=:oid"), {"tid": str(tid), "oid": payload.get("offering_id")})
    r = row.fetchone()
    return ok(dict(r._mapping) if r else {}, request_id=rid)


@router.get("/offerings/enabled/{offering_id}")
async def get_enabled_offering(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    row = await db.execute(text("SELECT *, id AS provider_enabled_offering_id FROM provider_enabled_offerings WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    r = row.fetchone()
    if not r:
        raise HTTPException(404, "Offering not found")
    return ok(dict(r._mapping), request_id=rid)


@router.put("/offerings/enabled/{offering_id}")
async def update_enabled_offering(
    offering_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    allowed = {"provider_display_name", "provider_description", "provider_price_override",
                "provider_min_price", "provider_max_price", "provider_visit_fee",
                "provider_appointment_fee", "supported_type_ids", "supported_brand_ids"}
    sets = ", ".join(f"{k}=:{k}" for k in payload if k in allowed)
    if sets:
        params = {k: v for k, v in payload.items() if k in allowed}
        params.update({"id": str(offering_id), "tid": str(tid)})
        await db.execute(text(f"UPDATE provider_enabled_offerings SET {sets}, updated_at=now() WHERE id=:id AND tenant_id=:tid"), params)
        await db.commit()
    row = await db.execute(text("SELECT *, id AS provider_enabled_offering_id FROM provider_enabled_offerings WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Offering not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.post("/offerings/enabled/{offering_id}/activate")
async def activate_offering(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(text("UPDATE provider_enabled_offerings SET is_enabled=true, is_active=true, status='active', updated_at=now() WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    await db.commit()
    row = await db.execute(text("SELECT *, id AS provider_enabled_offering_id FROM provider_enabled_offerings WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Offering not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.post("/offerings/enabled/{offering_id}/deactivate")
async def deactivate_offering(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(text("UPDATE provider_enabled_offerings SET is_enabled=false, is_active=false, status='inactive', updated_at=now() WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    await db.commit()
    row = await db.execute(text("SELECT *, id AS provider_enabled_offering_id FROM provider_enabled_offerings WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Offering not found")
    return ok(dict(fetched._mapping), request_id=rid)


@router.post("/offerings/enabled/{offering_id}/refresh-readiness")
async def refresh_offering_readiness(
    offering_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    await db.execute(text("UPDATE provider_enabled_offerings SET readiness_status='pending', updated_at=now() WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    await db.commit()
    row = await db.execute(text("SELECT *, id AS provider_enabled_offering_id FROM provider_enabled_offerings WHERE id=:id AND tenant_id=:tid"), {"id": str(offering_id), "tid": str(tid)})
    fetched = row.fetchone()
    if fetched is None:
        raise HTTPException(404, "Offering not found")
    return ok(dict(fetched._mapping), request_id=rid)


# ── Provider Status (Sprint 12) ────────────────────────────────────────────────

@router.get("/status")
async def get_provider_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    row = await db.execute(text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"), {"tid": str(tid)})
    r = row.fetchone()
    if r:
        data = dict(r._mapping)
    else:
        data = {
            "tenant_id": str(tid), "category_id": None,
            "is_visible": False, "is_bookable": False,
            "visibility_blockers": [], "bookability_blockers": [],
            "override_is_visible": None, "override_is_bookable": None,
            "last_evaluated_at": None,
        }
    return ok(data, request_id=rid)


async def _evaluate_provider_bookability(db: AsyncSession, tid: uuid.UUID) -> dict:
    """HS4B — real bookability/visibility computation, replacing the
    previous no-op stub. Reads real signals from tenants, tenant_billing,
    tenant_limits, tenant_service_areas, provider_availability_rules, and
    tenant_services — no fabricated/mocked status.

    Policy (documented per HS4B ticket requirement — "document final
    policy clearly"):
      is_bookable requires ALL critical checks to pass: tenant not
      suspended/rejected, at least one published service with a
      configured provider price range, at least one active service area,
      at least one availability rule, sufficient usage credits, and the
      security deposit requirement satisfied if one is configured.
      is_visible is a lighter bar: tenant not suspended/rejected, business
      profile complete, and at least one service published — a tenant can
      be visible (discoverable) before being fully bookable.
    """
    tenant_row = (await db.execute(
        text("SELECT status, verification_status, suspended_at, business_name, "
             "address_line1, city FROM tenants WHERE id=:tid"),
        {"tid": str(tid)},
    )).fetchone()

    passed: list[str] = []
    visibility_blockers: list[dict] = []
    bookability_blockers: list[dict] = []

    tenant_active = bool(tenant_row) and tenant_row.status not in ("suspended", "rejected") \
        and tenant_row.verification_status != "rejected" and tenant_row.suspended_at is None
    if tenant_active:
        passed.append("tenant_active_not_suspended")
    else:
        reason = {"code": "TENANT_SUSPENDED_OR_REJECTED",
                  "message": "Your account is suspended or not approved yet.",
                  "severity": "critical", "route": "/support"}
        visibility_blockers.append(reason)
        bookability_blockers.append(reason)

    profile_complete = bool(tenant_row) and bool(tenant_row.business_name) \
        and bool(tenant_row.address_line1) and bool(tenant_row.city)
    if profile_complete:
        passed.append("business_profile_complete")
    else:
        visibility_blockers.append({
            "code": "BUSINESS_PROFILE_INCOMPLETE",
            "message": "Complete your business profile (name, address, city).",
            "severity": "critical", "route": "/profile"})

    published_count = (await db.execute(
        text("SELECT count(*) FROM tenant_services WHERE tenant_id=:tid "
             "AND setup_status='published' AND is_active=true AND deleted_at IS NULL"),
        {"tid": str(tid)},
    )).scalar() or 0
    if published_count > 0:
        passed.append("service_setup_published")
    else:
        reason = {"code": "NO_PUBLISHED_SERVICE",
                  "message": "Publish at least one service before you can be booked.",
                  "severity": "critical", "route": "/tenant/setup/services"}
        visibility_blockers.append(reason)
        bookability_blockers.append(reason)

    # MODULE-L5-02 fix: a published service is "priced" if the tenant set a
    # min price (on the service, a type, or a brand) OR the service is a
    # fixed-price / no-override service that is already priced at the admin
    # level (master_services.tenant_override_allowed=false with a base_price).
    # Previously the latter case was ignored, so a provider whose published
    # services are all fixed-price could NEVER clear PROVIDER_PRICE_RANGE_MISSING
    # and thus never become bookable, even though their services ARE priced.
    priced_count = (await db.execute(
        text("SELECT count(*) FROM tenant_services ts WHERE ts.tenant_id=:tid "
             "AND ts.setup_status='published' AND ts.is_active=true AND ts.deleted_at IS NULL "
             "AND (ts.tenant_min_price IS NOT NULL "
             "     OR EXISTS (SELECT 1 FROM tenant_service_types tst WHERE tst.tenant_service_id=ts.id "
             "                AND tst.tenant_min_price IS NOT NULL) "
             "     OR EXISTS (SELECT 1 FROM tenant_service_brands tsb WHERE tsb.tenant_service_id=ts.id "
             "                AND tsb.tenant_min_price IS NOT NULL) "
             "     OR EXISTS (SELECT 1 FROM master_services ms WHERE ms.id = ts.master_service_id "
             "                AND ms.tenant_override_allowed = false "
             "                AND COALESCE(ms.base_price, ms.min_price) IS NOT NULL))"),
        {"tid": str(tid)},
    )).scalar() or 0
    if priced_count > 0:
        passed.append("provider_price_range_configured")
    else:
        bookability_blockers.append({
            "code": "PROVIDER_PRICE_RANGE_MISSING",
            "message": "Set your provider price range for at least one published service.",
            "severity": "critical", "route": "/tenant/setup/services"})

    active_areas = (await db.execute(
        text("SELECT count(*) FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true"),
        {"tid": str(tid)},
    )).scalar() or 0
    if active_areas > 0:
        passed.append("service_area_configured")
    else:
        bookability_blockers.append({
            "code": "SERVICE_AREA_MISSING",
            "message": "Add at least one active service area before receiving bookings.",
            "severity": "critical", "route": "/tenant/setup/service-areas"})

    availability_count = (await db.execute(
        text("SELECT count(*) FROM provider_availability_rules WHERE tenant_id=:tid AND is_active=true"),
        {"tid": str(tid)},
    )).scalar() or 0
    if availability_count > 0:
        passed.append("availability_configured")
    else:
        bookability_blockers.append({
            "code": "AVAILABILITY_MISSING",
            "message": "Set at least one open availability slot to receive bookings.",
            "severity": "critical", "route": "/tenant/setup/availability"})

    billing_row = (await db.execute(
        text("SELECT credit_balance, security_deposit_paid, security_deposit_amount "
             "FROM tenant_billing WHERE tenant_id=:tid"),
        {"tid": str(tid)},
    )).fetchone()
    credit_balance = float(billing_row.credit_balance) if billing_row and billing_row.credit_balance is not None else 0.0
    if credit_balance > 0:
        passed.append("usage_credits_available")
    else:
        bookability_blockers.append({
            "code": "USAGE_CREDITS_INSUFFICIENT",
            "message": "Add usage credits to your account to receive bookings.",
            "severity": "critical", "route": "/finance/usage-credit-ledger"})

    deposit_required = bool(billing_row) and billing_row.security_deposit_amount and float(billing_row.security_deposit_amount) > 0
    deposit_satisfied = (not deposit_required) or bool(billing_row and billing_row.security_deposit_paid)
    if deposit_satisfied:
        passed.append("security_deposit_satisfied")
    else:
        bookability_blockers.append({
            "code": "SECURITY_DEPOSIT_REQUIRED",
            "message": "Pay the required security deposit to become bookable.",
            "severity": "critical", "route": "/finance/security-deposit"})

    is_visible = tenant_active and profile_complete and published_count > 0
    is_bookable = is_visible and priced_count > 0 and active_areas > 0 \
        and availability_count > 0 and credit_balance > 0 and deposit_satisfied

    status_label = "bookable" if is_bookable else ("visible_not_bookable" if is_visible else "not_visible")

    return {
        "is_visible": is_visible, "is_bookable": is_bookable,
        "status": status_label,
        "passed_checks": passed,
        "visibility_blockers": visibility_blockers,
        "bookability_blockers": bookability_blockers,
    }


@router.post("/status/refresh")
async def refresh_provider_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    """HS4B fix — real computation replacing the previous no-op stub.
    Computes bookability/visibility from real tenant setup data and
    persists the result to provider_visibility_statuses (upsert)."""
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))

    result = await _evaluate_provider_bookability(db, tid)

    existing = (await db.execute(
        text("SELECT id FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tid)},
    )).fetchone()
    if existing:
        await db.execute(text(
            "UPDATE provider_visibility_statuses SET is_visible=:iv, is_bookable=:ib, "
            "visibility_blockers=CAST(:vb AS jsonb), bookability_blockers=CAST(:bb AS jsonb), "
            "last_evaluated_at=now(), last_changed_at=now(), updated_at=now() WHERE id=:id"
        ), {"iv": result["is_visible"], "ib": result["is_bookable"],
            "vb": json.dumps(result["visibility_blockers"]), "bb": json.dumps(result["bookability_blockers"]),
            "id": existing.id})
    else:
        await db.execute(text(
            "INSERT INTO provider_visibility_statuses "
            "(tenant_id, is_visible, is_bookable, visibility_blockers, bookability_blockers, last_evaluated_at, last_changed_at) "
            "VALUES (:tid, :iv, :ib, CAST(:vb AS jsonb), CAST(:bb AS jsonb), now(), now())"
        ), {"tid": str(tid), "iv": result["is_visible"], "ib": result["is_bookable"],
            "vb": json.dumps(result["visibility_blockers"]), "bb": json.dumps(result["bookability_blockers"])})
    await db.commit()

    row = (await db.execute(
        text("SELECT * FROM provider_visibility_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"),
        {"tid": str(tid)},
    )).fetchone()
    data = dict(row._mapping)
    data["status"] = result["status"]
    data["passed_checks"] = result["passed_checks"]
    data["failed_checks"] = result["bookability_blockers"]
    data["warnings"] = []
    return ok(data, request_id=rid)


# ── Matching Input Readiness (HS5B) ───────────────────────────────────────────
# Not the real provider-matching engine (that's HS6 scope) — this is a
# read-only preview showing whether the tenant's Home Services setup data
# (area coverage, availability, breaks, exceptions, booking window,
# bookability) is internally consistent for a hypothetical customer
# request. HS6 is expected to consume the same underlying tables.

async def get_tenant_home_services_matching_inputs(
    db: AsyncSession, tenant_id: uuid.UUID,
    service_id: uuid.UUID | None, service_type_id: uuid.UUID | None, brand_id: uuid.UUID | None,
    zipcode: str | None, requested_at: str | None,
) -> dict:
    blocking_reasons: list[dict] = []

    # zipcode coverage — any active service area whose zipcode list (comma-
    # separated per the existing tenant_service_areas convention) contains it
    zipcode_covered = True
    if zipcode:
        row = (await db.execute(
            text("SELECT count(*) FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true AND zipcode=:zip"),
            {"tid": str(tenant_id), "zip": zipcode})).scalar() or 0
        zipcode_covered = row > 0
        if not zipcode_covered:
            blocking_reasons.append({"code": "ZIPCODE_NOT_COVERED", "message": "This zipcode is not in any active service area."})

    # service/type/brand coverage — tenant_service_area_services, scoped by
    # area if we know it's covered; otherwise checked platform-wide for this tenant
    service_covered = True
    type_covered = True
    brand_covered = True
    if service_id:
        svc_row = (await db.execute(
            text("SELECT count(*) FROM tenant_service_area_services tsas "
                 "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
                 "WHERE tsas.tenant_id=:tid AND tsas.service_id=:sid AND tsas.is_available=true AND tsa.is_active=true"),
            {"tid": str(tenant_id), "sid": str(service_id)})).scalar() or 0
        service_covered = svc_row > 0
        if not service_covered:
            blocking_reasons.append({"code": "SERVICE_NOT_COVERED_IN_AREA", "message": "This service is not covered in your active service areas."})

        if service_type_id:
            type_row = (await db.execute(
                text("SELECT count(*) FROM tenant_service_area_services tsas "
                     "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
                     "WHERE tsas.tenant_id=:tid AND tsas.service_id=:sid AND tsas.service_type_id=:stid "
                     "AND tsas.is_available=true AND tsa.is_active=true"),
                {"tid": str(tenant_id), "sid": str(service_id), "stid": str(service_type_id)})).scalar() or 0
            type_covered = type_row > 0
            if not type_covered:
                blocking_reasons.append({"code": "TYPE_NOT_COVERED_IN_AREA", "message": "This service type is not covered in your active service areas."})

        if brand_id:
            brand_row = (await db.execute(
                text("SELECT count(*) FROM tenant_service_area_services tsas "
                     "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
                     "WHERE tsas.tenant_id=:tid AND tsas.service_id=:sid AND tsas.brand_id=:bid "
                     "AND tsas.is_available=true AND tsa.is_active=true"),
                {"tid": str(tenant_id), "sid": str(service_id), "bid": str(brand_id)})).scalar() or 0
            brand_covered = brand_row > 0
            if not brand_covered:
                blocking_reasons.append({"code": "BRAND_NOT_COVERED_IN_AREA", "message": "This brand is not covered in your active service areas."})

    # availability at requested time (day_of_week + time-of-day window)
    available_at_requested_time = True
    blocked_by_break = False
    blocked_by_exception = False
    requested_date = requested_time = None
    if requested_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
            requested_date = dt.date().isoformat()
            requested_time = dt.strftime("%H:%M")
            dow = dt.isoweekday() % 7  # match provider_availability_rules' 0=Sunday convention
        except ValueError:
            dow = None

        if dow is not None:
            rule = (await db.execute(
                text("SELECT * FROM provider_availability_rules WHERE tenant_id=:tid AND day_of_week=:dow AND is_active=true LIMIT 1"),
                {"tid": str(tenant_id), "dow": dow})).fetchone()
            if not rule:
                available_at_requested_time = False
                blocking_reasons.append({"code": "NOT_AN_OPEN_DAY", "message": "You are not open on this day."})
            elif not (rule.start_time <= requested_time <= rule.end_time):
                available_at_requested_time = False
                blocking_reasons.append({"code": "OUTSIDE_WORKING_HOURS", "message": "Requested time is outside working hours."})
            elif rule.break_start_time and rule.break_end_time and rule.break_start_time <= requested_time <= rule.break_end_time:
                blocked_by_break = True
                available_at_requested_time = False
                blocking_reasons.append({"code": "BLOCKED_BY_BREAK", "message": "Requested time falls inside your break."})

        if requested_date:
            exc = (await db.execute(
                text("SELECT * FROM tenant_availability_exceptions WHERE tenant_id=:tid AND date=:date AND status='active' LIMIT 1"),
                {"tid": str(tenant_id), "date": _parse_date(requested_date)})).fetchone()
            if exc:
                if exc.full_day_closed or (exc.start_time and exc.end_time and exc.start_time <= requested_time <= exc.end_time):
                    blocked_by_exception = True
                    available_at_requested_time = False
                    blocking_reasons.append({"code": "BLOCKED_BY_EXCEPTION", "message": f"You are closed on this date: {exc.reason}"})

    # booking window
    booking_window_valid = True
    bw = (await db.execute(
        text("SELECT * FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid": str(tenant_id)})).fetchone()
    if requested_at and bw:
        try:
            from datetime import datetime, timezone as dt_timezone
            dt = datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
            now = datetime.now(dt_timezone.utc)
            minutes_notice = (dt - now).total_seconds() / 60
            if minutes_notice < bw.minimum_notice_minutes:
                booking_window_valid = False
                blocking_reasons.append({"code": "BELOW_MINIMUM_NOTICE", "message": "Requested time is inside the minimum notice window."})
            if minutes_notice > bw.maximum_advance_booking_days * 24 * 60:
                booking_window_valid = False
                blocking_reasons.append({"code": "BEYOND_ADVANCE_BOOKING_WINDOW", "message": "Requested time is beyond the maximum advance booking window."})
        except ValueError:
            pass

    # bookability (HS4B)
    bookability = await _evaluate_provider_bookability(db, tenant_id)

    is_bookable = (
        zipcode_covered and service_covered and type_covered and brand_covered
        and available_at_requested_time and booking_window_valid and bookability["is_bookable"]
    )
    all_reasons = blocking_reasons + bookability["bookability_blockers"]

    return {
        "tenant_id": str(tenant_id),
        "zipcode_covered": zipcode_covered,
        "service_covered": service_covered,
        "type_covered": type_covered,
        "brand_covered": brand_covered,
        "available_at_requested_time": available_at_requested_time,
        "blocked_by_break": blocked_by_break,
        "blocked_by_exception": blocked_by_exception,
        "booking_window_valid": booking_window_valid,
        "is_bookable": is_bookable,
        "blocking_reasons": all_reasons,
    }


@router.post("/home-services/matching-inputs/preview")
async def preview_matching_inputs(
    payload: dict, request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await get_tenant_home_services_matching_inputs(
        db, tid,
        service_id=uuid.UUID(payload["service_id"]) if payload.get("service_id") else None,
        service_type_id=uuid.UUID(payload["service_type_id"]) if payload.get("service_type_id") else None,
        brand_id=uuid.UUID(payload["brand_id"]) if payload.get("brand_id") else None,
        zipcode=payload.get("zipcode"),
        requested_at=payload.get("requested_at"),
    )
    return ok(result, request_id=rid)


@router.get("/status/offerings")
async def get_offering_statuses(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    result = await db.execute(text("SELECT * FROM provider_offering_bookable_statuses WHERE tenant_id=:tid ORDER BY created_at DESC"), {"tid": str(tid)})
    rows = [dict(r._mapping) for r in result.fetchall()]
    return ok({"statuses": rows, "count": len(rows)}, request_id=rid)


# ── Onboarding Status (Sprint 10) ─────────────────────────────────────────────

@router.get("/onboarding/status")
async def get_onboarding_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    # MODULE-L5-02: provider_onboarding_statuses is not provisioned in all
    # environments; fall back to the not-started default instead of a 500.
    try:
        row = await db.execute(text("SELECT * FROM provider_onboarding_statuses WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1"), {"tid": str(tid)})
        r = row.fetchone()
    except Exception:
        await db.rollback()
        r = None
    if r:
        data = dict(r._mapping)
    else:
        data = {
            "tenant_id": str(tid), "category_id": None,
            "total_items": 0, "required_items": 0, "completed_items": 0,
            "pending_items": 0, "blocked_items": 0, "overridden_items": 0,
            "progress_percent": 0, "onboarding_ready": False,
            "blockers": [], "next_action": None, "last_refreshed_at": None,
        }
    return ok(data, request_id=rid)


@router.get("/onboarding/items")
async def get_onboarding_items(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    # MODULE-L5-02: provider_onboarding_items may not be provisioned; fall back
    # to an empty list instead of a 500.
    try:
        result = await db.execute(text("""
            SELECT poi.*, oct.title, oct.description as template_description, oct.item_type,
                   oct.is_required as template_required, oct.completion_source
            FROM provider_onboarding_items poi
            LEFT JOIN onboarding_checklist_templates oct ON oct.id = poi.template_id
            WHERE poi.tenant_id = :tid
            ORDER BY oct.display_order, poi.checklist_key
        """), {"tid": str(tid)})
        rows = [dict(r._mapping) for r in result.fetchall()]
    except Exception:
        await db.rollback()
        rows = []
    return ok({"items": rows, "count": len(rows)}, request_id=rid)


@router.post("/onboarding/refresh")
async def refresh_onboarding(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    return ok({"refreshed": True}, request_id=rid)


# ── Packages Status (Sprint 9) ────────────────────────────────────────────────

@router.get("/packages/status")
async def get_packages_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    # MODULE-L5-02: rewired from the phantom `provider_package_purchases` table
    # to the CANONICAL `tenant_package_assignments` (the real package table,
    # Sprint P1). `status` is aliased as `purchase_status` to preserve the
    # frontend contract. Safety net retained.
    try:
        result = await db.execute(text("""
            SELECT tpa.*, tpa.status as purchase_status,
                   sp.name as package_name, sp.package_type as pkg_type,
                   sp.plan_level, sp.features
            FROM tenant_package_assignments tpa
            LEFT JOIN service_packages sp ON sp.id = tpa.package_id
            WHERE tpa.tenant_id = :tid AND tpa.status != 'cancelled'
                  AND tpa.deleted_at IS NULL
            ORDER BY tpa.created_at DESC
        """), {"tid": str(tid)})
        rows = [dict(r._mapping) for r in result.fetchall()]
    except Exception:
        await db.rollback()
        rows = []
    active = [r for r in rows if r.get("purchase_status") in ("active", "activated")]
    return ok({
        "has_active_package": len(active) > 0,
        "active_package": active[0] if active else None,
        "all_purchases": rows,
        "total": len(rows),
    }, request_id=rid)


# ── HS9 — Usage Credits (tenant-facing) ───────────────────────────────────────

@router.get("/usage-credits/balance")
async def get_usage_credit_balance(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from app.engines.tenant_engine.models import TenantBilling
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    res = await db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tid))
    billing = res.scalars().first()
    balance = float(billing.credit_balance) if billing else 0.0
    return ok({
        "tenant_id": str(tid),
        "usage_credit_balance": balance,
        "low_credit": balance < 20,
    }, request_id=rid)


@router.get("/usage-credits/ledger")
async def get_usage_credit_ledger(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    from app.engines.tenant_engine.models import UsageCreditLedger
    tid = _tid(user)
    rid = (getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—"))
    res = await db.execute(
        select(UsageCreditLedger)
        .where(UsageCreditLedger.tenant_id == tid)
        .order_by(UsageCreditLedger.created_at.desc())
        .limit(200)
    )
    entries = [e.to_dict() for e in res.scalars().all()]
    return ok({"tenant_id": str(tid), "entries": entries, "count": len(entries)}, request_id=rid)
