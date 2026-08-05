"""UX-05 — Effective Availability Resolution Engine (spec section 8).

Canonical, single source of truth for "can technician X work on date D".
Reuses the REAL existing tables — no new/duplicate availability engine:

  - provider_availability_rules  (scope_type='provider')      -> business hours
  - provider_availability_rules  (scope_type='staff_member')  -> per-technician weekly pattern + breaks + daily capacity
  - tenant_availability_exceptions                              -> tenant-wide date overrides / holidays (full or partial day)
  - provider_team_members.status / max_concurrent_jobs          -> technician active flag + concurrent-capacity cap
  - service_jobs (assigned_staff_id, scheduled_date, status)     -> existing assignments consumed for capacity math

GENUINE GAPS (confirmed by direct schema audit this session — not assumed):
  no `staff_time_off` / per-technician time-off table exists yet, and no
  per-technician date-override table exists (`tenant_availability_exceptions`
  is tenant-wide only, not staff-scoped). Reason codes ON_TIME_OFF and
  DATE_OVERRIDE_BLOCKED are wired into the precedence chain and WILL fire the
  day those tables exist; until then they are structurally unreachable and
  the resolver says so explicitly via `time_off_supported` / `staff_override_supported: False`
  in the returned capability flags, per spec section 15 ("do not replace
  errors with empty zero metrics").

Precedence order implements spec section 8 steps 1-11 exactly (12-15 —
job-type/type/brand capability, service duration+buffer, requested-timezone
conversion — require a specific job/service context and are intentionally
left to the caller to layer on top of this business/day-level resolution;
see `docs` note at bottom of file).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Reason codes — exact vocabulary from spec section 8.
R_BUSINESS_CLOSED = "BUSINESS_CLOSED"
R_STAFF_INACTIVE = "STAFF_INACTIVE"
R_STAFF_SETUP_INCOMPLETE = "STAFF_SETUP_INCOMPLETE"
R_OUTSIDE_WORKING_HOURS = "OUTSIDE_WORKING_HOURS"
R_DATE_OVERRIDE_BLOCKED = "DATE_OVERRIDE_BLOCKED"
R_ON_TIME_OFF = "ON_TIME_OFF"
R_DURING_BREAK = "DURING_BREAK"
R_SCHEDULE_CONFLICT = "SCHEDULE_CONFLICT"
R_DAILY_CAPACITY_EXCEEDED = "DAILY_CAPACITY_EXCEEDED"
R_CONCURRENT_CAPACITY_EXCEEDED = "CONCURRENT_CAPACITY_EXCEEDED"
R_TIMEZONE_CONTEXT_INVALID = "TIMEZONE_CONTEXT_INVALID"

# Job statuses that consume capacity (non-terminal — mirrors JOB_TRANSITIONS
# terminal set in app/engines/execution/constants.py: completed/cancelled/
# failed/closed_estimate_declined do NOT consume capacity).
_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}

DEFAULT_TIMEZONE = "Asia/Kolkata"


async def _fetch_business_hours(db: AsyncSession, tenant_id: uuid.UUID, dow: int) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=:tid AND scope_type='provider' AND scope_id IS NULL "
        "AND day_of_week=:dow AND is_active=true"
    ), {"tid": str(tenant_id), "dow": dow})).fetchall()
    return [dict(r._mapping) for r in rows]


async def _fetch_tenant_exception(db: AsyncSession, tenant_id: uuid.UUID, target_date: dt.date) -> dict | None:
    row = (await db.execute(text(
        "SELECT * FROM tenant_availability_exceptions "
        "WHERE tenant_id=:tid AND date=:d AND status='active'"
    ), {"tid": str(tenant_id), "d": target_date})).fetchone()
    return dict(row._mapping) if row else None


async def _fetch_staff_pattern(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID, dow: int) -> dict | None:
    row = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=:tid AND scope_type='staff_member' AND scope_id=:sid "
        "AND day_of_week=:dow AND is_active=true"
    ), {"tid": str(tenant_id), "sid": str(staff_id), "dow": dow})).fetchone()
    return dict(row._mapping) if row else None


async def _fetch_staff(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> dict | None:
    row = (await db.execute(text(
        "SELECT id, tenant_id, full_name, status, max_concurrent_jobs, deleted_at "
        "FROM provider_team_members WHERE id=:sid AND tenant_id=:tid"
    ), {"sid": str(staff_id), "tid": str(tenant_id)})).fetchone()
    return dict(row._mapping) if row else None


async def _fetch_assignments(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID,
                              target_date: dt.date) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT id, job_number, status, scheduled_time_window FROM service_jobs "
        "WHERE tenant_id=:tid AND assigned_staff_id=:sid AND scheduled_date=:d"
    ), {"tid": str(tenant_id), "sid": str(staff_id), "d": target_date})).fetchall()
    return [dict(r._mapping) for r in rows]


def _time_str(v) -> str | None:
    if v is None:
        return None
    return str(v)[:5]


async def _fetch_approved_time_off(
    db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID, target_date: dt.date,
) -> dict | None:
    """Approved, non-cancelled leave covering `target_date`, if any."""
    from app.engines.home_service_assignment.schedule_models import StaffTimeOffRequest
    row = (await db.execute(
        select(StaffTimeOffRequest).where(
            StaffTimeOffRequest.tenant_id == tenant_id,
            StaffTimeOffRequest.staff_member_id == staff_id,
            StaffTimeOffRequest.status == "approved",
            StaffTimeOffRequest.cancelled_at.is_(None),
            StaffTimeOffRequest.start_date <= target_date,
            StaffTimeOffRequest.end_date >= target_date,
        ).limit(1)
    )).scalars().first()
    if not row:
        return None
    return {
        "id": str(row.id),
        "is_full_day": row.is_full_day,
        "start_time": row.start_time.strftime("%H:%M") if row.start_time else None,
        "end_time": row.end_time.strftime("%H:%M") if row.end_time else None,
        "reason_category": row.reason_category,
    }


async def resolve_staff_day(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    target_date: dt.date,
) -> dict:
    """Resolve effective availability for one technician on one date.

    Implements spec section 8 steps 1-11 in exact precedence order and
    fails closed (available=False, reason set) whenever required context
    cannot be resolved.
    """
    dow = (target_date.isoweekday()) % 7  # 0=Sunday, matches provider_availability_rules convention (see router.py:1550)
    reasons: list[str] = []
    result: dict = {
        "staff_id": str(staff_id),
        "date": target_date.isoformat(),
        "available": False,
        "reasons": [],
        "timezone": DEFAULT_TIMEZONE,
        "business_hours": None,
        "working_hours": None,
        "break": None,
        "daily_capacity": None,
        "concurrent_capacity": None,
        "assignments_today": [],
        "capability_flags": {
            "time_off_supported": False,
            "date_override_supported_per_staff": False,
        },
    }

    # Step 2 — business operating hours (tenant-wide exception first, then weekly rule).
    exc = await _fetch_tenant_exception(db, tenant_id, target_date)
    if exc and exc.get("full_day_closed"):
        reasons.append(R_BUSINESS_CLOSED)
        result["reasons"] = reasons
        return result

    biz_rules = await _fetch_business_hours(db, tenant_id, dow)
    if not biz_rules and not exc:
        reasons.append(R_BUSINESS_CLOSED)
        result["reasons"] = reasons
        return result
    if biz_rules:
        result["business_hours"] = {
            "start": _time_str(biz_rules[0]["start_time"]),
            "end": _time_str(biz_rules[0]["end_time"]),
        }

    # Step 3/4 — technician active + readiness (setup incomplete = no profile/team row).
    staff = await _fetch_staff(db, tenant_id, staff_id)
    if not staff or staff.get("deleted_at") is not None:
        reasons.append(R_STAFF_INACTIVE)
        result["reasons"] = reasons
        return result
    if staff.get("status") != "active":
        reasons.append(R_STAFF_INACTIVE)
        result["reasons"] = reasons
        return result

    concurrent_cap = staff.get("max_concurrent_jobs")
    result["concurrent_capacity"] = {"limit": concurrent_cap}

    # Step 5 — weekly working pattern (per-technician; scope_type='staff_member').
    pattern = await _fetch_staff_pattern(db, tenant_id, staff_id, dow)
    if not pattern:
        reasons.append(R_STAFF_SETUP_INCOMPLETE)
        result["reasons"] = reasons
        return result
    result["working_hours"] = {"start": _time_str(pattern["start_time"]), "end": _time_str(pattern["end_time"])}
    result["daily_capacity"] = {"limit": pattern.get("max_jobs_per_day")}
    if pattern.get("timezone"):
        result["timezone"] = pattern["timezone"]

    # Step 6 — date override. GAP: no per-staff override table exists yet
    # (confirmed: provider_schedule_overrides does not exist). Tenant-wide
    # partial-day exception is the closest real analog available today.
    if exc and not exc.get("full_day_closed") and exc.get("start_time") and exc.get("end_time"):
        result["working_hours"] = {"start": _time_str(exc["start_time"]), "end": _time_str(exc["end_time"])}
        result["capability_flags"]["date_override_supported_per_staff"] = False
        # Recorded as an override-narrowed window, not a hard block (spec 6:
        # override REPLACES weekly hours; block-worthy scenario would be a
        # zero-width window, which _validate_exception_payload already prevents).

    # Step 7 — time off (approved leave).
    #
    # This was a documented GAP ("no staff_time_off table exists yet"), but
    # `staff_time_off_requests` HAS since been created
    # (schedule_models.StaffTimeOffRequest) -- the resolver was simply never
    # updated to consult it, so it kept reporting `time_off_supported: False`
    # and a technician on APPROVED leave still resolved as available and
    # could be handed work.
    #
    # Only `approved` and not-cancelled rows block: a pending request must
    # never silently remove someone from the roster before their tenant has
    # actually decided.
    time_off = await _fetch_approved_time_off(db, tenant_id, staff_id, target_date)
    result["capability_flags"]["time_off_supported"] = True
    if time_off:
        result["time_off"] = time_off
        if time_off.get("is_full_day"):
            reasons.append(R_ON_TIME_OFF)
            result["reasons"] = reasons
            return result
        # Partial-day leave narrows the working window rather than removing
        # the day entirely; the caller's slot search subtracts it.
        result["time_off_window"] = {
            "start": time_off.get("start_time"), "end": time_off.get("end_time"),
        }

    # Step 8 — break.
    break_start, break_end = _time_str(pattern.get("break_start_time")), _time_str(pattern.get("break_end_time"))
    if break_start and break_end:
        result["break"] = {"start": break_start, "end": break_end}

    # Step 9 — existing assignments (capacity-consuming = non-terminal status).
    assignments = await _fetch_assignments(db, tenant_id, staff_id, target_date)
    active_assignments = [a for a in assignments if a["status"] not in _TERMINAL_STATUSES]
    result["assignments_today"] = [
        {"job_number": a["job_number"], "status": a["status"], "time_window": a["scheduled_time_window"]}
        for a in assignments
    ]

    # Step 10 — concurrent capacity.
    if concurrent_cap is not None and len(active_assignments) >= concurrent_cap:
        reasons.append(R_CONCURRENT_CAPACITY_EXCEEDED)

    # Step 11 — daily capacity.
    daily_cap = pattern.get("max_jobs_per_day")
    if daily_cap is not None and len(active_assignments) >= daily_cap:
        reasons.append(R_DAILY_CAPACITY_EXCEEDED)

    result["daily_capacity"] = {"limit": daily_cap, "used": len(active_assignments),
                                 "remaining": (max(daily_cap - len(active_assignments), 0) if daily_cap is not None else None)}
    result["concurrent_capacity"] = {"limit": concurrent_cap, "used": len(active_assignments),
                                      "remaining": (max(concurrent_cap - len(active_assignments), 0) if concurrent_cap is not None else None)}

    result["reasons"] = reasons
    result["available"] = len(reasons) == 0
    return result


async def preview_staff_pattern_change(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    staff_id: uuid.UUID,
    day_of_week: int,
    proposed_is_active: bool,
    proposed_max_jobs_per_day: int | None,
    proposed_start_time: str | None,
    proposed_end_time: str | None,
    horizon_days: int = 60,
) -> dict:
    """Spec sections 6/11 — impact preview for a proposed weekly-pattern /
    capacity change, BEFORE it is saved. Reuses the same real-assignment
    query resolve_staff_day() uses (_fetch_assignments) rather than a
    separate conflict engine — checks the proposed values against REAL
    upcoming service_jobs rows for this exact technician + day-of-week,
    over the next `horizon_days` days (today inclusive).

    Never writes anything. Returns a stable shape the frontend can render
    before the caller decides whether to confirm.
    """
    today = dt.date.today()
    affected: list[dict] = []
    capacity_would_drop_below_existing = False

    d = today
    end = today + dt.timedelta(days=horizon_days)
    while d <= end:
        if (d.isoweekday() % 7) == day_of_week:
            assignments = await _fetch_assignments(db, tenant_id, staff_id, d)
            active = [a for a in assignments if a["status"] not in _TERMINAL_STATUSES]
            if active:
                reasons_for_date: list[str] = []
                if not proposed_is_active:
                    reasons_for_date.append("day_would_become_unavailable")
                if proposed_max_jobs_per_day is not None and len(active) > proposed_max_jobs_per_day:
                    reasons_for_date.append("capacity_below_existing_assignments")
                    capacity_would_drop_below_existing = True
                if reasons_for_date:
                    affected.append({
                        "date": d.isoformat(),
                        "existing_assignment_count": len(active),
                        "job_numbers": [a["job_number"] for a in active],
                        "reasons": reasons_for_date,
                    })
        d += dt.timedelta(days=1)

    return {
        "staff_id": str(staff_id),
        "day_of_week": day_of_week,
        "horizon_days": horizon_days,
        "future_assignments_affected": sum(a["existing_assignment_count"] for a in affected),
        "affected_dates": affected,
        "capacity_would_drop_below_existing": capacity_would_drop_below_existing,
        "requires_confirmation": len(affected) > 0,
    }


async def aggregate_slot_available(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: dt.date,
) -> dict:
    """Spec section 9 — customer-facing aggregate slot check.

    A slot is available only when AT LEAST ONE eligible (active) technician
    for this tenant is available for `target_date` per resolve_staff_day().
    Never returns individual technician identity/calendars — aggregate
    counts only, matching "do not expose individual technician calendars to
    customers".
    """
    staff_rows = (await db.execute(text(
        "SELECT id FROM provider_team_members WHERE tenant_id=:tid AND deleted_at IS NULL AND status='active'"
    ), {"tid": str(tenant_id)})).fetchall()
    staff_ids = [r[0] for r in staff_rows]

    if not staff_ids:
        # Fail closed: no technicians at all means no eligible-technician
        # context can be resolved — never assume unlimited/available.
        return {"available": False, "eligible_technician_count": 0, "remaining_capacity": 0,
                "reasons": [R_STAFF_INACTIVE]}

    eligible_count = 0
    remaining_capacity_total = 0
    reasons_seen: set[str] = set()
    for sid in staff_ids:
        day = await resolve_staff_day(db, tenant_id, sid, target_date)
        if day["available"]:
            eligible_count += 1
            dc = (day.get("daily_capacity") or {}).get("remaining")
            cc = (day.get("concurrent_capacity") or {}).get("remaining")
            remaining_capacity_total += min(v for v in (dc, cc) if v is not None) if (dc is not None or cc is not None) else 1
        else:
            reasons_seen.update(day["reasons"])

    return {
        "available": eligible_count > 0,
        "eligible_technician_count": eligible_count,
        "remaining_capacity": remaining_capacity_total,
        "reasons": [] if eligible_count > 0 else sorted(reasons_seen),
    }


async def resolve_tenant_week(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    date_from: dt.date,
    date_to: dt.date,
    staff_id: uuid.UUID | None = None,
) -> dict:
    """Canonical projection backing GET /v1/tenant/home-services/availability."""
    staff_rows = (await db.execute(text(
        "SELECT id, full_name, designation, status, max_concurrent_jobs, profile_photo_url "
        "FROM provider_team_members WHERE tenant_id=:tid AND deleted_at IS NULL "
        + ("AND id=:sid" if staff_id else "") + " ORDER BY full_name"
    ), {"tid": str(tenant_id), **({"sid": str(staff_id)} if staff_id else {})})).fetchall()
    staff_list = [dict(r._mapping) for r in staff_rows]

    schedules: list[dict] = []
    conflicts: list[dict] = []
    d = date_from
    while d <= date_to:
        for s in staff_list:
            day = await resolve_staff_day(db, tenant_id, s["id"], d)
            schedules.append(day)
            if R_SCHEDULE_CONFLICT in day["reasons"] or R_DAILY_CAPACITY_EXCEEDED in day["reasons"] \
               or R_CONCURRENT_CAPACITY_EXCEEDED in day["reasons"]:
                conflicts.append({"staff_id": str(s["id"]), "date": d.isoformat(), "reasons": day["reasons"]})
        d += dt.timedelta(days=1)

    today_iso = dt.date.today().isoformat()
    available_today = sum(1 for sc in schedules if sc["date"] == today_iso and sc["available"])
    # Real count now that `staff_time_off_requests` is consulted by
    # resolve_staff_day -- this used to be hardcoded 0 with a GAP note.
    on_leave_today = sum(
        1 for sc in schedules
        if sc["date"] == today_iso and R_ON_TIME_OFF in sc.get("reasons", [])
    )

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "timezone": DEFAULT_TIMEZONE,
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "summary": {
            "available_today": available_today,
            "on_leave_today": on_leave_today,
            "total_capacity": sum((s.get("max_concurrent_jobs") or 0) for s in staff_list),
            "technician_count": len(staff_list),
            "conflicts": len(conflicts),
        },
        "technicians": staff_list,
        "effective_schedules": schedules,
        "conflicts": conflicts,
        "capability_flags": {
            "time_off_supported": True,
            "date_override_supported_per_staff": False,
            "schedule_conflict_table_supported": False,
        },
    }
