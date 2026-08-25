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
import json
import re
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Reason codes — exact vocabulary from spec section 8.
R_BUSINESS_CLOSED = "BUSINESS_CLOSED"
R_STAFF_INACTIVE = "STAFF_INACTIVE"
R_STAFF_SETUP_INCOMPLETE = "STAFF_SETUP_INCOMPLETE"
# Distinct reasons on purpose: "on leave" and "not working that day" look the same on a
# grid but mean different things to whoever is trying to staff the job.
R_STAFF_TIME_OFF = "STAFF_TIME_OFF"
R_STAFF_OFF_DAY = "STAFF_DATE_OVERRIDE_CLOSED"
R_OUTSIDE_WORKING_HOURS = "OUTSIDE_WORKING_HOURS"
R_DATE_OVERRIDE_BLOCKED = "DATE_OVERRIDE_BLOCKED"
R_ON_TIME_OFF = "ON_TIME_OFF"
R_DURING_BREAK = "DURING_BREAK"
R_SCHEDULE_CONFLICT = "SCHEDULE_CONFLICT"
R_ASSIGNMENT_OUTSIDE_AVAILABILITY = "ASSIGNMENT_OUTSIDE_AVAILABILITY"
# Either origin means the same thing to a summary count: this person is not working today.
LEAVE_REASONS = {R_STAFF_TIME_OFF, R_ON_TIME_OFF}
R_DAILY_CAPACITY_EXCEEDED = "DAILY_CAPACITY_EXCEEDED"
R_CONCURRENT_CAPACITY_EXCEEDED = "CONCURRENT_CAPACITY_EXCEEDED"
R_TIMEZONE_CONTEXT_INVALID = "TIMEZONE_CONTEXT_INVALID"

# Job statuses that consume capacity (non-terminal — mirrors JOB_TRANSITIONS
# terminal set in app/engines/execution/constants.py: completed/cancelled/
# failed/closed_estimate_declined do NOT consume capacity).
_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}

DEFAULT_TIMEZONE = "Asia/Kolkata"


async def _fetch_business_hours(db: AsyncSession, tenant_id: uuid.UUID, dow: int) -> list[dict]:
    cache = db.info.get("availability_resolution_cache")
    if cache and cache["tenant_id"] == str(tenant_id):
        return cache["business_hours"].get(dow, [])
    rows = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=:tid AND scope_type='provider' AND scope_id IS NULL "
        "AND day_of_week=:dow AND is_active=true"
    ), {"tid": str(tenant_id), "dow": dow})).fetchall()
    return [dict(r._mapping) for r in rows]


async def _fetch_tenant_exception(db: AsyncSession, tenant_id: uuid.UUID, target_date: dt.date) -> dict | None:
    cache = db.info.get("availability_resolution_cache")
    if cache and cache["tenant_id"] == str(tenant_id):
        return cache["tenant_exceptions"].get(target_date)
    row = (await db.execute(text(
        "SELECT * FROM tenant_availability_exceptions "
        "WHERE tenant_id=:tid AND date=:d AND status='active'"
    ), {"tid": str(tenant_id), "d": target_date})).fetchone()
    return dict(row._mapping) if row else None


async def _fetch_staff_pattern(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID, dow: int) -> dict | None:
    cache = db.info.get("availability_resolution_cache")
    if cache and cache["tenant_id"] == str(tenant_id):
        return cache["staff_patterns"].get((str(staff_id), dow))
    row = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=:tid AND scope_type='staff_member' AND scope_id=:sid "
        "AND day_of_week=:dow AND is_active=true"
    ), {"tid": str(tenant_id), "sid": str(staff_id), "dow": dow})).fetchone()
    return dict(row._mapping) if row else None


async def _fetch_staff(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> dict | None:
    cache = db.info.get("availability_resolution_cache")
    if cache and cache["tenant_id"] == str(tenant_id):
        return cache["staff"].get(str(staff_id))
    row = (await db.execute(text(
        "SELECT id, tenant_id, full_name, status, max_concurrent_jobs, deleted_at "
        "FROM provider_team_members WHERE id=:sid AND tenant_id=:tid"
    ), {"sid": str(staff_id), "tid": str(tenant_id)})).fetchone()
    return dict(row._mapping) if row else None


async def _fetch_assignments(db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID,
                              target_date: dt.date) -> list[dict]:
    """This technician's jobs on this date, with the service each one is for.

    The board draws a job as "10:00-12:00 / AC Repair". It only had the job number, so
    every cell read as an opaque code and a provider scanning the week could not tell an
    AC install from a drain callout without opening each one.

    `offering_id` points at either a tenant's own service row or straight at the master
    service depending on how the job was created, so the join follows both and prefers
    the tenant's display name where one exists -- that is the name the provider gave the
    service, and the master name is the fallback, not the other way round.
    """
    cache = db.info.get("availability_resolution_cache")
    if cache and cache["tenant_id"] == str(tenant_id):
        return cache["assignments"].get((str(staff_id), target_date), [])
    rows = (await db.execute(text(
        "SELECT j.id, j.job_number, j.status, j.scheduled_time_window, "
        "       COALESCE(ts.tenant_display_name, ms.service_name) AS service_name "
        "FROM service_jobs j "
        "LEFT JOIN tenant_services ts ON ts.id = j.offering_id "
        "LEFT JOIN master_services ms ON ms.id = COALESCE(ts.master_service_id, j.offering_id) "
        "WHERE j.tenant_id=:tid AND j.assigned_staff_id=:sid AND j.scheduled_date=:d"
    ), {"tid": str(tenant_id), "sid": str(staff_id), "d": target_date})).fetchall()
    return [dict(r._mapping) for r in rows]


def _time_str(v) -> str | None:
    if v is None:
        return None
    return str(v)[:5]


async def _staff_time_off(db: AsyncSession, tenant_id, staff_id, day: dt.date) -> dict | None:
    """Approved leave covering this date, from EITHER leave store, or None.

    There are two, and both are real. `staff_time_off` (migration 242) is leave the owner
    books against a technician from the availability board. `staff_time_off_requests` is
    leave the technician submits from the staff app and the owner approves. They record
    the same fact — this person is not working — arrived at two different ways, so the
    resolver has to consult both or a technician is unavailable in one surface and bookable
    in the other.

    They are returned in ONE shape. The two tables disagree on column names
    (`all_day`/`start_time` vs `is_full_day`/`start_time`, `reason` vs `reason_category`),
    and leaking that split to the board would make every consumer branch on which table
    happened to answer. `source` is kept because "the owner booked this" and "the
    technician asked for this" are different answers to "why", even though the day is
    blocked either way.

    Full-day leave wins the ordering: if someone has both a half day and a full day
    recorded over one date, the full day is the stronger claim and blocks it.
    """
    cache = db.info.get("availability_resolution_cache")
    if cache and cache["tenant_id"] == str(tenant_id):
        return cache["time_off"].get((str(staff_id), day))

    owner_booked = (await db.execute(text(
        "SELECT id, all_day, start_time, end_time, reason "
        "FROM staff_time_off "
        "WHERE tenant_id = CAST(:tid AS uuid) AND staff_member_id = CAST(:sid AS uuid) "
        "  AND status = 'approved' AND :d BETWEEN start_date AND end_date "
        "ORDER BY all_day DESC LIMIT 1"
    ), {"tid": str(tenant_id), "sid": str(staff_id), "d": day})).fetchone()

    candidates: list[dict] = []
    if owner_booked:
        m = dict(owner_booked._mapping)
        candidates.append({
            "id": str(m["id"]),
            "all_day": bool(m["all_day"]),
            "start": _time_str(m["start_time"]),
            "end": _time_str(m["end_time"]),
            "reason": m.get("reason"),
            "source": "owner_booked",
        })

    from app.engines.home_service_assignment.schedule_models import StaffTimeOffRequest
    requested = (await db.execute(
        select(StaffTimeOffRequest).where(
            StaffTimeOffRequest.tenant_id == tenant_id,
            StaffTimeOffRequest.staff_member_id == staff_id,
            # Only approved and not-cancelled leave blocks. A pending request must never
            # quietly remove someone from the roster before their tenant has decided.
            StaffTimeOffRequest.status == "approved",
            StaffTimeOffRequest.cancelled_at.is_(None),
            StaffTimeOffRequest.start_date <= day,
            StaffTimeOffRequest.end_date >= day,
        ).limit(1)
    )).scalars().first()
    if requested:
        candidates.append({
            "id": str(requested.id),
            "all_day": bool(requested.is_full_day),
            "start": requested.start_time.strftime("%H:%M") if requested.start_time else None,
            "end": requested.end_time.strftime("%H:%M") if requested.end_time else None,
            "reason": requested.reason_category,
            "source": "requested",
        })

    if not candidates:
        return None
    candidates.sort(key=lambda c: not c["all_day"])
    return candidates[0]


async def _staff_override(db: AsyncSession, tenant_id, staff_id, day: dt.date) -> dict | None:
    """This technician's hours for this specific date, replacing the weekly pattern."""
    cache = db.info.get("availability_resolution_cache")
    if cache and cache["tenant_id"] == str(tenant_id):
        return cache["overrides"].get((str(staff_id), day))
    row = (await db.execute(text(
        "SELECT start_time, end_time, full_day_closed, reason "
        "FROM staff_availability_overrides "
        "WHERE tenant_id = CAST(:tid AS uuid) AND staff_member_id = CAST(:sid AS uuid) "
        "  AND override_date = :d"
    ), {"tid": str(tenant_id), "sid": str(staff_id), "d": day})).fetchone()
    return dict(row._mapping) if row else None


async def _prefetch_resolution_cache(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    staff_rows: list[dict],
    date_from: dt.date,
    date_to: dt.date,
) -> dict:
    """Load a whole planner page in a bounded, constant number of queries.

    ``resolve_staff_day`` remains the single rules engine. Its small fetch
    helpers read this request-local cache while the planner projection loops
    through staff and dates, avoiding the old staff x day x query explosion.
    """
    staff_ids = [str(row["id"]) for row in staff_rows]
    cache = {
        "tenant_id": str(tenant_id),
        "business_hours": {},
        "tenant_exceptions": {},
        "staff_patterns": {},
        "staff": {str(row["id"]): row for row in staff_rows},
        "overrides": {},
        "time_off": {},
        "assignments": {},
    }
    if not staff_ids:
        return cache

    business_rows = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=CAST(:tid AS uuid) AND scope_type='provider' "
        "AND scope_id IS NULL AND is_active=true"
    ), {"tid": str(tenant_id)})).all()
    for row in business_rows:
        value = dict(row._mapping)
        cache["business_hours"].setdefault(value["day_of_week"], []).append(value)

    exception_rows = (await db.execute(text(
        "SELECT * FROM tenant_availability_exceptions "
        "WHERE tenant_id=CAST(:tid AS uuid) AND date BETWEEN :date_from AND :date_to "
        "AND status='active'"
    ), {"tid": str(tenant_id), "date_from": date_from, "date_to": date_to})).all()
    for row in exception_rows:
        value = dict(row._mapping)
        cache["tenant_exceptions"][value["date"]] = value

    pattern_rows = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=CAST(:tid AS uuid) AND scope_type='staff_member' "
        "AND scope_id=ANY(CAST(:staff_ids AS uuid[])) AND is_active=true"
    ), {"tid": str(tenant_id), "staff_ids": staff_ids})).all()
    for row in pattern_rows:
        value = dict(row._mapping)
        cache["staff_patterns"][(str(value["scope_id"]), value["day_of_week"])] = value

    override_rows = (await db.execute(text(
        "SELECT staff_member_id, override_date, start_time, end_time, full_day_closed, reason "
        "FROM staff_availability_overrides "
        "WHERE tenant_id=CAST(:tid AS uuid) "
        "AND staff_member_id=ANY(CAST(:staff_ids AS uuid[])) "
        "AND override_date BETWEEN :date_from AND :date_to"
    ), {
        "tid": str(tenant_id), "staff_ids": staff_ids,
        "date_from": date_from, "date_to": date_to,
    })).all()
    for row in override_rows:
        value = dict(row._mapping)
        cache["overrides"][(str(value.pop("staff_member_id")), value.pop("override_date"))] = value

    def add_time_off(value: dict) -> None:
        start = max(value.pop("start_date"), date_from)
        end = min(value.pop("end_date"), date_to)
        staff_id = str(value.pop("staff_member_id"))
        day = start
        while day <= end:
            key = (staff_id, day)
            current = cache["time_off"].get(key)
            if current is None or (value["all_day"] and not current["all_day"]):
                cache["time_off"][key] = dict(value)
            day += dt.timedelta(days=1)

    owner_leave_rows = (await db.execute(text(
        "SELECT id, staff_member_id, start_date, end_date, all_day, start_time, end_time, reason "
        "FROM staff_time_off WHERE tenant_id=CAST(:tid AS uuid) "
        "AND staff_member_id=ANY(CAST(:staff_ids AS uuid[])) AND status='approved' "
        "AND start_date<=:date_to AND end_date>=:date_from "
        "ORDER BY all_day DESC, created_at DESC"
    ), {
        "tid": str(tenant_id), "staff_ids": staff_ids,
        "date_from": date_from, "date_to": date_to,
    })).all()
    for row in owner_leave_rows:
        value = dict(row._mapping)
        value.update({
            "id": str(value["id"]), "start": _time_str(value.pop("start_time")),
            "end": _time_str(value.pop("end_time")), "source": "owner_booked",
        })
        add_time_off(value)

    requested_leave_rows = (await db.execute(text(
        "SELECT id, staff_member_id, start_date, end_date, is_full_day, start_time, end_time, reason_category "
        "FROM staff_time_off_requests WHERE tenant_id=CAST(:tid AS uuid) "
        "AND staff_member_id=ANY(CAST(:staff_ids AS uuid[])) AND status='approved' "
        "AND cancelled_at IS NULL AND start_date<=:date_to AND end_date>=:date_from "
        "ORDER BY is_full_day DESC, created_at DESC"
    ), {
        "tid": str(tenant_id), "staff_ids": staff_ids,
        "date_from": date_from, "date_to": date_to,
    })).all()
    for row in requested_leave_rows:
        value = dict(row._mapping)
        value.update({
            "id": str(value["id"]), "all_day": bool(value.pop("is_full_day")),
            "start": _time_str(value.pop("start_time")),
            "end": _time_str(value.pop("end_time")),
            "reason": value.pop("reason_category"), "source": "requested",
        })
        add_time_off(value)

    # Some historical jobs store the roster id, while older rows store the
    # linked user id. Resolve both to one canonical roster row so capacity is
    # never understated during the transition.
    assignment_owner: dict[str, str] = {}
    for row in staff_rows:
        canonical = str(row["id"])
        assignment_owner[canonical] = canonical
        if row.get("user_id"):
            assignment_owner[str(row["user_id"])] = canonical
    assignment_ids = list(assignment_owner)
    assignment_rows = (await db.execute(text(
        "SELECT j.id, j.assigned_staff_id, j.scheduled_date, j.job_number, j.status, "
        "j.scheduled_time_window, COALESCE(ts.tenant_display_name, ms.service_name) AS service_name "
        "FROM service_jobs j "
        "LEFT JOIN tenant_services ts ON ts.id=j.offering_id "
        "LEFT JOIN master_services ms ON ms.id=COALESCE(ts.master_service_id,j.offering_id) "
        "WHERE j.tenant_id=CAST(:tid AS uuid) "
        "AND j.assigned_staff_id=ANY(CAST(:assignment_ids AS uuid[])) "
        "AND j.scheduled_date BETWEEN :date_from AND :date_to"
    ), {
        "tid": str(tenant_id), "assignment_ids": assignment_ids,
        "date_from": date_from, "date_to": date_to,
    })).all()
    for row in assignment_rows:
        value = dict(row._mapping)
        canonical = assignment_owner.get(str(value.pop("assigned_staff_id")))
        scheduled_date = value.pop("scheduled_date")
        if canonical:
            cache["assignments"].setdefault((canonical, scheduled_date), []).append(value)
    return cache


_WINDOW_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*[-\u2013\u2014]\s*(\d{1,2}):(\d{2})\s*$")


def _parse_window(label: str | None) -> tuple[int, int] | None:
    """`scheduled_time_window` as minutes-from-midnight, or None if it isn't a range.

    The column is free text and holds all three of "14:30-16:30", "morning", and NULL.
    Anything that is not an explicit range returns None and is treated as unprovable
    rather than assumed: a job labelled "morning" cannot be shown to overlap another job,
    and inventing a window for it would let the board accuse a provider of a clash that
    the data does not support.
    """
    if not label:
        return None
    m = _WINDOW_RE.match(label)
    if not m:
        return None
    sh, sm, eh, em = (int(g) for g in m.groups())
    if sh > 23 or eh > 24 or sm > 59 or em > 59:
        return None
    start, end = sh * 60 + sm, eh * 60 + em
    return (start, end) if end > start else None


def _peak_overlap(assignments: list[dict]) -> tuple[int, list[str]]:
    """Most jobs running at once, and the job numbers involved in that peak.

    A sweep over the window edges rather than pairwise comparison, so three jobs
    overlapping the same hour count as three at one instant and not as three separate
    pairs -- "how many at once" is the question `max_concurrent_jobs` actually asks.

    Jobs without a parseable window are excluded from the peak but still consume daily
    volume. They are counted in `unscheduled` by the caller so the board can say how much
    of the day it could not reason about, instead of quietly reporting a peak of 0 for a
    technician whose whole day is untimed.
    """
    timed = [(w, a["job_number"]) for a in assignments if (w := _parse_window(a.get("time_window") or a.get("scheduled_time_window"))) ]
    if not timed:
        return 0, []
    events: list[tuple[int, int]] = []
    for (start, end), _ in timed:
        events.append((start, 1))
        events.append((end, -1))
    # Ends before starts at the same minute: a job finishing at 12:00 and one beginning
    # at 12:00 are consecutive, not concurrent.
    events.sort(key=lambda e: (e[0], e[1]))
    running = peak = 0
    peak_at = None
    for minute, delta in events:
        running += delta
        if running > peak:
            peak, peak_at = running, minute
    involved = [jn for (s, e), jn in timed if peak_at is not None and s <= peak_at < e]
    return peak, involved


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
        # Both are real now (migration 242). They were declared False while the tables
        # did not exist, so the board could say so instead of rendering empty cells.
        "capability_flags": {
            "time_off_supported": True,
            "date_override_supported_per_staff": True,
        },
        "time_off": None,
        "date_override": None,
        "tenant_exception": None,
        # Present on every response, including the early returns above, so the board never
        # has to distinguish "no conflict" from "this key is missing on days that ended
        # early" -- a closed day has no overlapping jobs, and says so.
        "overlapping_jobs": [],
    }

    # Committed work must remain visible even when a later availability rule closes the
    # day. Those are the assignments an operator has to move, not records to hide.
    assignments = await _fetch_assignments(db, tenant_id, staff_id, target_date)
    active_assignments = [a for a in assignments if a["status"] not in _TERMINAL_STATUSES]
    result["assignments_today"] = [
        {
            "job_id": str(a["id"]),
            "job_number": a["job_number"],
            "status": a["status"],
            "time_window": a["scheduled_time_window"],
            "service_name": a.get("service_name"),
        }
        for a in assignments
    ]

    def unavailable_result() -> dict:
        if active_assignments and R_ASSIGNMENT_OUTSIDE_AVAILABILITY not in reasons:
            reasons.append(R_ASSIGNMENT_OUTSIDE_AVAILABILITY)
            result["overlapping_jobs"] = [a["job_number"] for a in active_assignments]
        result["reasons"] = reasons
        return result

    # Step 2 — business operating hours (tenant-wide exception first, then weekly rule).
    exc = await _fetch_tenant_exception(db, tenant_id, target_date)
    if exc and exc.get("full_day_closed"):
        reasons.append(R_BUSINESS_CLOSED)
        return unavailable_result()

    biz_rules = await _fetch_business_hours(db, tenant_id, dow)
    if not biz_rules and not exc:
        reasons.append(R_BUSINESS_CLOSED)
        return unavailable_result()
    if biz_rules:
        result["business_hours"] = {
            "start": _time_str(biz_rules[0]["start_time"]),
            "end": _time_str(biz_rules[0]["end_time"]),
        }

    # Step 3/4 — technician active + readiness (setup incomplete = no profile/team row).
    staff = await _fetch_staff(db, tenant_id, staff_id)
    if not staff or staff.get("deleted_at") is not None:
        reasons.append(R_STAFF_INACTIVE)
        return unavailable_result()
    if staff.get("status") != "active":
        reasons.append(R_STAFF_INACTIVE)
        return unavailable_result()

    concurrent_cap = staff.get("max_concurrent_jobs")
    # Same keys the fully-resolved result carries, so a caller reading `used` does not
    # have to know whether the day happened to end early.
    result["concurrent_capacity"] = {
        "limit": concurrent_cap, "used": 0, "remaining": concurrent_cap,
        "untimed_assignments": 0,
    }

    # Step 5 — weekly working pattern (per-technician; scope_type='staff_member').
    pattern = await _fetch_staff_pattern(db, tenant_id, staff_id, dow)
    if not pattern:
        reasons.append(R_STAFF_SETUP_INCOMPLETE)
        result["reasons"] = reasons
        return result
    result["working_hours"] = {"start": _time_str(pattern["start_time"]), "end": _time_str(pattern["end_time"])}

    # Step 5a — this technician's own date override REPLACES the weekly pattern. A
    # provider who set 10:00-16:00 for one Wednesday meant that Wednesday, not a change
    # to every Wednesday.
    override = await _staff_override(db, tenant_id, staff_id, target_date)
    if override:
        result["date_override"] = {
            "start": _time_str(override["start_time"]),
            "end": _time_str(override["end_time"]),
            "full_day_closed": bool(override["full_day_closed"]),
            "reason": override.get("reason"),
        }
        if override["full_day_closed"]:
            reasons.append(R_STAFF_OFF_DAY)
            return unavailable_result()
        result["working_hours"] = {
            "start": _time_str(override["start_time"]),
            "end": _time_str(override["end_time"]),
        }

    # Step 5b — approved leave. Checked AFTER the override so the board can still show
    # what the day would have been, and last among the schedule steps because leave beats
    # any hours: a technician on holiday is not working the override either.
    time_off = await _staff_time_off(db, tenant_id, staff_id, target_date)
    if time_off:
        result["time_off"] = time_off
        if time_off["all_day"]:
            # Two codes for two origins. On a grid they look identical -- nobody
            # available -- but to whoever is trying to staff the job, "the owner booked
            # this person off" and "this person asked for leave and it was approved" are
            # different answers, and collapsing them would lose that.
            reasons.append(R_ON_TIME_OFF if time_off["source"] == "requested" else R_STAFF_TIME_OFF)
            return unavailable_result()
        # A part-day absence leaves the rest of the day workable, so the day is NOT
        # closed -- the board draws the blocked hours and the technician keeps the rest.
        result["time_off_window"] = {"start": time_off["start"], "end": time_off["end"]}

    if pattern.get("timezone"):
        result["timezone"] = pattern["timezone"]

    # Step 6 — tenant-wide partial-day exception ("we close early on the 31st").
    #
    # This narrows the day for the WHOLE business, so it applies on top of whatever hours
    # this technician ended up with, rather than replacing them. It used to overwrite
    # working_hours outright, which silently threw away a per-staff override set for the
    # same date: a technician given 10:00-16:00 for one Wednesday would show the tenant's
    # hours instead, and the override the provider had just saved would vanish from the
    # board with nothing to say it had been ignored.
    #
    # Intersecting is the honest answer -- the business being shut at 17:00 cannot make a
    # technician available until 18:00, and a technician starting at 10:00 is not made to
    # start at 09:00 because the business opens then.
    if exc and not exc.get("full_day_closed") and exc.get("start_time") and exc.get("end_time"):
        exc_start, exc_end = _time_str(exc["start_time"]), _time_str(exc["end_time"])
        cur = result["working_hours"] or {"start": None, "end": None}
        start = max(s for s in (cur["start"], exc_start) if s) if (cur["start"] or exc_start) else exc_start
        end = min(e for e in (cur["end"], exc_end) if e) if (cur["end"] or exc_end) else exc_end
        result["tenant_exception"] = {"start": exc_start, "end": exc_end}
        if start and end and start >= end:
            # The intersection is empty: the business is only open at hours this
            # technician does not work. Nobody can be booked into a zero-width window,
            # so say so rather than rendering a backwards range.
            result["working_hours"] = {"start": start, "end": end}
            reasons.append(R_OUTSIDE_WORKING_HOURS)
            return unavailable_result()
        result["working_hours"] = {"start": start, "end": end}

    # Step 8 — break.
    break_start, break_end = _time_str(pattern.get("break_start_time")), _time_str(pattern.get("break_end_time"))
    if break_start and break_end:
        result["break"] = {"start": break_start, "end": break_end}

    # Step 9 — existing assignments (capacity-consuming = non-terminal status).
    assignments = await _fetch_assignments(db, tenant_id, staff_id, target_date)
    active_assignments = [a for a in assignments if a["status"] not in _TERMINAL_STATUSES]
    result["assignments_today"] = [
        {"job_id": str(a["id"]), "job_number": a["job_number"], "status": a["status"],
         "time_window": a["scheduled_time_window"], "service_name": a.get("service_name")}
        for a in assignments
    ]

    # Step 10 — concurrent capacity, measured as jobs actually running AT ONCE.
    #
    # This compared the day's TOTAL job count against max_concurrent_jobs, which is the
    # daily-volume question, not the concurrency one: a technician allowed 2 jobs at a
    # time was reported over capacity the moment they had a third job anywhere in the day,
    # even at 09:00, 13:00 and 17:00 with nothing overlapping. That both hid real clashes
    # and manufactured false ones, and it is why the board's Conflicts tile had nothing
    # trustworthy behind it.
    peak, peak_jobs = _peak_overlap(active_assignments)
    untimed = [a for a in active_assignments if not _parse_window(a["scheduled_time_window"])]
    if concurrent_cap is not None and peak > concurrent_cap:
        reasons.append(R_CONCURRENT_CAPACITY_EXCEEDED)
        # A distinct fact from "this technician is full": these particular jobs were
        # booked over each other and someone has to move one. The board draws the jobs in
        # `overlapping_jobs` red and says which day.
        reasons.append(R_SCHEDULE_CONFLICT)

    working = result.get("working_hours") or {}
    working_window = _parse_window(
        f"{working.get('start')}-{working.get('end')}"
        if working.get("start") and working.get("end") else None
    )
    break_window = _parse_window(f"{break_start}-{break_end}" if break_start and break_end else None)
    leave_window = None
    if time_off and not time_off.get("all_day"):
        leave_window = _parse_window(f"{time_off.get('start')}-{time_off.get('end')}")

    outside_jobs: list[str] = []
    for assignment in active_assignments:
        window = _parse_window(assignment.get("scheduled_time_window"))
        if not window:
            continue
        outside_shift = bool(working_window and (window[0] < working_window[0] or window[1] > working_window[1]))
        during_break = bool(break_window and window[0] < break_window[1] and break_window[0] < window[1])
        during_leave = bool(leave_window and window[0] < leave_window[1] and leave_window[0] < window[1])
        if outside_shift or during_break or during_leave:
            outside_jobs.append(assignment["job_number"])
    if outside_jobs:
        if R_ASSIGNMENT_OUTSIDE_AVAILABILITY not in reasons:
            reasons.append(R_ASSIGNMENT_OUTSIDE_AVAILABILITY)
        if R_SCHEDULE_CONFLICT not in reasons:
            reasons.append(R_SCHEDULE_CONFLICT)

    # Step 11 — daily capacity (volume across the whole day, timed or not).
    daily_cap = pattern.get("max_jobs_per_day")
    if daily_cap is not None and len(active_assignments) >= daily_cap:
        reasons.append(R_DAILY_CAPACITY_EXCEEDED)

    result["daily_capacity"] = {"limit": daily_cap, "used": len(active_assignments),
                                 "remaining": (max(daily_cap - len(active_assignments), 0) if daily_cap is not None else None)}
    result["concurrent_capacity"] = {
        "limit": concurrent_cap,
        "used": peak,
        "remaining": (max(concurrent_cap - peak, 0) if concurrent_cap is not None else None),
        # Surfaced, not swallowed: jobs with no parseable window ("morning", or nothing at
        # all) cannot be placed on a timeline, so the peak above is a floor rather than a
        # measurement. The board says how many it could not read instead of implying the
        # day is emptier than it is.
        "untimed_assignments": len(untimed),
    }
    result["overlapping_jobs"] = sorted(set(peak_jobs + outside_jobs)) if R_SCHEDULE_CONFLICT in reasons else []

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


async def _resolve_tenant_week_legacy(
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
            # Only genuine overlap counts as a conflict. A technician who has hit their
            # daily limit is FULL, which is a normal, intended end state and needs no
            # review -- counting it here put a permanent non-zero number on the Conflicts
            # tile and next to "Review conflicts", training the provider to ignore both.
            if R_SCHEDULE_CONFLICT in day["reasons"]:
                conflicts.append({
                    "staff_id": str(s["id"]),
                    "date": d.isoformat(),
                    "reasons": day["reasons"],
                    "overlapping_jobs": day.get("overlapping_jobs", []),
                    "concurrent_limit": (day.get("concurrent_capacity") or {}).get("limit"),
                    "peak_concurrent": (day.get("concurrent_capacity") or {}).get("used"),
                })
        d += dt.timedelta(days=1)

    today_iso = dt.date.today().isoformat()
    available_today = sum(1 for sc in schedules if sc["date"] == today_iso and sc["available"])
    # Both leave codes count. This looked only for ON_TIME_OFF, the code raised by
    # technician-submitted requests, so leave the owner booked from this very board
    # (STAFF_TIME_OFF, migration 242) left the On leave tile reading 0 while the grid
    # showed the person greyed out -- the board contradicting itself on one screen.
    on_leave_today = sum(
        1 for sc in schedules
        if sc["date"] == today_iso and LEAVE_REASONS & set(sc.get("reasons", []))
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
        # Migration 242 gave both of these real tables, and resolve_staff_day above reads
        # them. This block still said date overrides were unsupported, and the board reads
        # THIS copy, not the per-day one -- so the page kept rendering its "not configured
        # in this system yet" disclosure over data that was by then real.
        #
        # Conflicts are derived from overlapping assignment windows rather than stored, so
        # that flag stays false and means what it says: there is no conflict table, and
        # a conflict is a live reading of the jobs on the day.
        "capability_flags": {
            "time_off_supported": True,
            "date_override_supported_per_staff": True,
            "schedule_conflict_table_supported": False,
            "schedule_conflict_derived": True,
        },
    }


async def resolve_tenant_week(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    date_from: dt.date,
    date_to: dt.date,
    staff_id: uuid.UUID | None = None,
    *,
    search: str | None = None,
    designation: str | None = None,
    capability: uuid.UUID | None = None,
    availability: str | None = None,
    limit: int = 50,
    offset: int = 0,
    focus_date: dt.date | None = None,
) -> dict:
    """Enterprise planner projection with bounded queries and tenant-scoped paging."""
    clauses = [
        "tenant_id=CAST(:tid AS uuid)",
        "deleted_at IS NULL",
        "member_type IN ('technician','owner_technician')",
    ]
    params: dict = {"tid": str(tenant_id), "limit": limit, "offset": offset}
    if staff_id:
        clauses.append("id=CAST(:staff_id AS uuid)")
        params["staff_id"] = str(staff_id)
    if search:
        clauses.append("(lower(full_name) LIKE :search OR lower(COALESCE(designation,'')) LIKE :search)")
        params["search"] = f"%{search.strip().lower()}%"
    if designation:
        clauses.append("lower(COALESCE(designation,''))=lower(:designation)")
        params["designation"] = designation
    if capability:
        clauses.append("COALESCE(supported_offering_ids,'[]'::jsonb) @> CAST(:capability AS jsonb)")
        params["capability"] = json.dumps([str(capability)])

    where = " AND ".join(clauses)
    total = int((await db.execute(text(
        f"SELECT count(*) FROM provider_team_members WHERE {where}"
    ), params)).scalar() or 0)
    rows = (await db.execute(text(
        "SELECT id, user_id, full_name, designation, member_type, status, "
        "max_concurrent_jobs, profile_photo_url, supported_offering_ids, deleted_at "
        f"FROM provider_team_members WHERE {where} "
        "ORDER BY lower(full_name), id LIMIT :limit OFFSET :offset"
    ), params)).all()
    staff_list = [dict(row._mapping) for row in rows]

    offering_rows = (await db.execute(text(
        "SELECT ts.id::text AS id, COALESCE(ts.tenant_display_name, ms.service_name) AS name "
        "FROM tenant_services ts JOIN master_services ms ON ms.id=ts.master_service_id "
        "WHERE ts.tenant_id=CAST(:tid AS uuid) AND COALESCE(ts.is_enabled,true)=true "
        "ORDER BY lower(COALESCE(ts.tenant_display_name, ms.service_name)), ts.id"
    ), {"tid": str(tenant_id)})).all()
    offering_map = {row.id: row.name for row in offering_rows}
    capabilities = [{"id": row.id, "name": row.name} for row in offering_rows]
    for staff in staff_list:
        supported_ids = [str(value) for value in (staff.get("supported_offering_ids") or [])]
        staff["supported_service_ids"] = supported_ids
        staff["supported_services"] = [
            {"id": service_id, "name": offering_map[service_id]}
            for service_id in supported_ids if service_id in offering_map
        ]

    cache = await _prefetch_resolution_cache(db, tenant_id, staff_list, date_from, date_to)
    db.info["availability_resolution_cache"] = cache
    schedules: list[dict] = []
    conflicts: list[dict] = []
    try:
        day = date_from
        while day <= date_to:
            for staff in staff_list:
                resolved = await resolve_staff_day(db, tenant_id, staff["id"], day)
                schedules.append(resolved)
                if R_SCHEDULE_CONFLICT in resolved["reasons"]:
                    conflicts.append({
                        "staff_id": str(staff["id"]),
                        "date": day.isoformat(),
                        "reasons": resolved["reasons"],
                        "overlapping_jobs": resolved.get("overlapping_jobs", []),
                        "concurrent_limit": (resolved.get("concurrent_capacity") or {}).get("limit"),
                        "peak_concurrent": (resolved.get("concurrent_capacity") or {}).get("used"),
                    })
            day += dt.timedelta(days=1)
    finally:
        db.info.pop("availability_resolution_cache", None)

    selected_day = focus_date or date_from
    if availability in {"available", "unavailable"}:
        wanted = availability == "available"
        included = {
            item["staff_id"] for item in schedules
            if item["date"] == selected_day.isoformat() and item["available"] is wanted
        }
        staff_list = [staff for staff in staff_list if str(staff["id"]) in included]
        schedules = [item for item in schedules if item["staff_id"] in included]
        conflicts = [item for item in conflicts if item["staff_id"] in included]

    focus_iso = selected_day.isoformat()
    focus_schedules = [item for item in schedules if item["date"] == focus_iso]
    designations = (await db.execute(text(
        "SELECT DISTINCT designation FROM provider_team_members "
        "WHERE tenant_id=CAST(:tid AS uuid) AND deleted_at IS NULL "
        "AND member_type IN ('technician','owner_technician') AND designation IS NOT NULL "
        "ORDER BY designation"
    ), {"tid": str(tenant_id)})).scalars().all()

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "timezone": DEFAULT_TIMEZONE,
        "from": date_from.isoformat(),
        "to": date_to.isoformat(),
        "focus_date": focus_iso,
        "summary": {
            "available_today": sum(1 for item in focus_schedules if item["available"]),
            "on_leave_today": sum(1 for item in focus_schedules if LEAVE_REASONS & set(item.get("reasons", []))),
            "total_capacity": sum((item.get("concurrent_capacity") or {}).get("limit") or 0 for item in focus_schedules),
            "technician_count": total,
            "conflicts": len(conflicts),
        },
        "technicians": staff_list,
        "effective_schedules": schedules,
        "conflicts": conflicts,
        "pagination": {
            "total": total, "limit": limit, "offset": offset,
            "has_next": offset + limit < total,
        },
        "available_filters": {"designations": list(designations), "capabilities": capabilities},
        "capability_flags": {
            "time_off_supported": True,
            "date_override_supported_per_staff": True,
            "schedule_conflict_table_supported": False,
            "schedule_conflict_derived": True,
        },
    }
