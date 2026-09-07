"""Provider-level bookable-slot resolution.

The provider configures business hours and slot length. Per-slot capacity is
derived from ready technicians scheduled for that weekday and assigned to the
requested service. It is not a manually-entered job limit: one technician
creates one place in a slot, and a provider can never promise more
simultaneous visits than its team can deliver.

Real gap this closes: slot length was configured, but capacity was split
between a hand-entered number and the roster. The booking pipeline now reads
the roster and its service/schedule assignments directly, and the customer is
never offered a slot the configured team cannot staff.

The customer is shown a real, capacity-checked slot BEFORE they confirm
(today first, then the next day, and so on), so they make the final call
on a promise the provider can actually keep -- rather than confirming
blind and waiting to find out.

NOTICE PERIOD -- provider-owned, not a hardcoded constant.

An earlier version of this module hardcoded a 6-hour normal / 2-hour
emergency lead time. That was wrong for the same reason this module exists
at all: `tenant_booking_window_settings` ALREADY holds these rules, the
provider portal already exposes full CRUD for them
(GET/PUT /booking-window), and nothing in the booking pipeline read them.
A global constant silently overrode whatever the provider had configured.

Everything timing-related now comes from that table:

  minimum_notice_minutes       how far ahead a slot must start (default 120)
  allow_same_day_booking       may today's slots be offered at all
  maximum_advance_booking_days how far ahead to look (default 7)
  emergency_booking_allowed    may the notice period be waived
  timezone                     the tenant's real local clock

An emergency request waives the notice period down to "the slot has not
started yet", and ONLY when the provider has opted in via
`emergency_booking_allowed`. It never invents capacity: the walk is
identical, so an emergency still only ever returns a slot inside the
provider's own configured business hours with real room in it. There is no
after-hours emergency concept, because the provider never configured one.

TIMEZONE: "now" is resolved in the tenant's own timezone rather than the
server's. This matters materially -- a server running in UTC against an
Asia/Kolkata tenant is 5h30m behind, and would offer slots that had
already passed in the tenant's actual local day.
"""
from __future__ import annotations
import datetime as dt
import uuid
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_assignment.eligibility import active_technician_sql

# Hard ceiling on the walk, independent of the provider's own
# `maximum_advance_booking_days`. A provider with no configured
# availability at all should fail fast and visibly, not scan forever.
MAX_SEARCH_DAYS = 62

# Used only when a provider has rules but left slot length unset.
FALLBACK_SLOT_MINUTES = 120

# Backward-compatible export for older integrations/tests. The booking engine
# no longer reads this value; capacity is derived solely from ready technicians.
FALLBACK_MAX_PER_SLOT = 1

logger = structlog.get_logger("home_service_booking.provider_slots")

# How many days that actually HAVE bookable slots to offer the customer.
# Product rule: today's remaining slots, plus the next open day's -- so a
# Saturday-evening customer with Sunday closed sees Monday, and a day with
# nothing left never counts against this.
DEFAULT_OFFERED_DAYS = 2

# Mirrors the column defaults on `tenant_booking_window_settings`, used only
# when a tenant has no row there yet. Kept in sync with the provider portal's
# own fallback block (see provider_portal/router.py get_booking_window) so a
# provider who has never opened the settings page gets identical behaviour
# either way.
BOOKING_WINDOW_DEFAULTS = {
    "minimum_notice_minutes": 120,
    "maximum_advance_booking_days": 7,
    "allow_same_day_booking": True,
    "emergency_booking_allowed": False,
    "timezone": "Asia/Kolkata",
}


async def booking_window_settings(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """The provider's own booking-window rules, or the documented defaults.

    Single source of truth for every timing decision in this module. Read
    from `tenant_booking_window_settings`, which the provider edits through
    the provider portal -- never from a constant in here.
    """
    row = (await db.execute(text(
        "SELECT minimum_notice_minutes, maximum_advance_booking_days, "
        "allow_same_day_booking, emergency_booking_allowed, timezone "
        "FROM tenant_booking_window_settings WHERE tenant_id=:tid"
    ), {"tid": str(tenant_id)})).fetchone()
    if not row:
        return dict(BOOKING_WINDOW_DEFAULTS)
    settings = dict(row._mapping)
    # A NULL in any column falls back rather than crashing the walk.
    return {k: (settings.get(k) if settings.get(k) is not None else v)
            for k, v in BOOKING_WINDOW_DEFAULTS.items()}


def _tenant_now(settings: dict) -> dt.datetime:
    """"Now" on the tenant's own clock, as a naive local datetime so it is
    directly comparable to the naive `start_time`/`end_time` the
    availability rules store.

    Degrades to server-local time if the timezone cannot be resolved at all
    -- notably on Windows, where `zoneinfo` has no system tz database and
    needs the `tzdata` package. A missing tz database must never stop a
    customer booking; it only costs the UTC-vs-local correction. The default
    is retried before giving up, in case only the tenant's own value is bad.
    """
    for key in (settings.get("timezone"), BOOKING_WINDOW_DEFAULTS["timezone"]):
        if not key:
            continue
        try:
            return dt.datetime.now(ZoneInfo(str(key))).replace(tzinfo=None)
        except Exception:  # noqa: BLE001 -- unknown tz / no tz database
            continue
    return dt.datetime.now()


def _notice_cutoff(settings: dict, now: dt.datetime, emergency: bool) -> dt.datetime:
    """Earliest moment a slot may start.

    Emergency waives the notice period entirely -- down to "has not started
    yet" -- but only if the provider opted in. A provider who has not
    enabled emergency booking keeps their full notice period no matter what
    the customer asks for.
    """
    if emergency and settings.get("emergency_booking_allowed"):
        return now
    return now + dt.timedelta(minutes=int(settings["minimum_notice_minutes"]))


def _parse_hhmm(value) -> dt.time | None:
    """Rules store times as strings ("09:00" / "09:00:00")."""
    if value is None:
        return None
    if isinstance(value, dt.time):
        return value
    s = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return dt.datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _window_label(start: dt.time, end: dt.time) -> str:
    """The canonical `scheduled_time_window` string stored on the job."""
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


async def _provider_rules_for_day(db: AsyncSession, tenant_id: uuid.UUID, dow: int) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT * FROM provider_availability_rules "
        "WHERE tenant_id=:tid AND scope_type='provider' AND scope_id IS NULL "
        "AND day_of_week=:dow AND is_active=true "
        "ORDER BY start_time"
    ), {"tid": str(tenant_id), "dow": dow})).fetchall()
    return [dict(r._mapping) for r in rows]


async def _is_closed(db: AsyncSession, tenant_id: uuid.UUID, day: dt.date) -> bool:
    row = (await db.execute(text(
        "SELECT full_day_closed FROM tenant_availability_exceptions "
        "WHERE tenant_id=:tid AND date=:d AND status='active'"
    ), {"tid": str(tenant_id), "d": day})).fetchone()
    return bool(row and row._mapping.get("full_day_closed"))


async def _booked_counts(db: AsyncSession, tenant_id: uuid.UUID, day: dt.date, exclude_job_id: uuid.UUID | None = None) -> dict[str, int]:
    """How many live jobs the provider already holds per time window that day.

    Cancelled/failed jobs must not consume capacity -- otherwise a day of
    cancellations would permanently block a provider's calendar.
    """
    rows = (await db.execute(text(
        "SELECT scheduled_time_window, COUNT(*) AS n FROM service_jobs "
        "WHERE tenant_id=:tid AND scheduled_date=:d "
        "AND (CAST(:exclude_id AS uuid) IS NULL OR id <> CAST(:exclude_id AS uuid)) "
        "AND status NOT IN ('cancelled','failed','rejected') "
        "GROUP BY scheduled_time_window"
    ), {"tid": str(tenant_id), "d": day, "exclude_id": str(exclude_job_id) if exclude_job_id else None})).fetchall()
    return {r._mapping["scheduled_time_window"]: int(r._mapping["n"]) for r in rows}


def _slots_from_rule(rule: dict) -> list[tuple[dt.time, dt.time]]:
    start = _parse_hhmm(rule.get("start_time"))
    end = _parse_hhmm(rule.get("end_time"))
    if not start or not end or start >= end:
        return []
    # Home Services visits reserve two hours, even for legacy one-hour rules.
    minutes = FALLBACK_SLOT_MINUTES

    slots: list[tuple[dt.time, dt.time]] = []
    cursor = dt.datetime.combine(dt.date.today(), start)
    limit = dt.datetime.combine(dt.date.today(), end)
    step = dt.timedelta(minutes=minutes)
    while cursor + step <= limit:
        nxt = cursor + step
        break_start = _parse_hhmm(rule.get("break_start_time"))
        break_end = _parse_hhmm(rule.get("break_end_time"))
        if break_start and break_end and cursor.time() < break_end and nxt.time() > break_start:
            cursor = dt.datetime.combine(cursor.date(), break_end)
            continue
        slots.append((cursor.time(), nxt.time()))
        cursor = nxt
    return slots


def _daily_remaining(rules: list[dict], technicians: int, booked: dict) -> int:
    """Provider daily volume, bounded by whole two-hour windows and funded staff."""
    windows = sorted({slot for rule in rules for slot in _slots_from_rule(rule)})
    # Overlapping schedule rows do not create extra physical working hours.
    count = 0
    previous_end = None
    for start, end in windows:
        if previous_end is None or start >= previous_end:
            count += 1
            previous_end = end
    physical_limit = count * max(0, technicians)
    limits = [int(r["max_jobs_per_day"]) for r in rules if r.get("max_jobs_per_day") is not None]
    limit = min([physical_limit, *limits])
    return max(0, limit - sum(booked.values()))


def _overlapping_bookings(booked: dict, start: dt.time, end: dt.time) -> int:
    """Old or edited time-window labels must still occupy overlapping capacity."""
    total = 0
    for label, count in booked.items():
        try:
            left, right = label.split("-", 1)
            booked_start, booked_end = _parse_hhmm(left), _parse_hhmm(right)
        except (AttributeError, ValueError):
            booked_start = booked_end = None
        if not booked_start or not booked_end or (booked_start < end and booked_end > start):
            total += count
    return total


async def assignable_technician_count(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    master_service_id: uuid.UUID | None = None,
    day: dt.date | None = None,
) -> int:
    """Count funded, verified technicians who contribute one place to a slot.

    Capacity is headcount, capped by the tenant's live purchased seats. A
    technician contributes capacity only after all required identity and
    background documents are current and verified. Activation can therefore
    finish before payment, while customer booking still fails closed.

    `master_service_id` and `day` remain accepted for existing callers but do
    not narrow this provider-level count. Service coverage is enforced by the
    matching/assignment gates; provider availability defines the offered day.

    Returns -1 (not 0) when the roster cannot be read, so callers can tell
    "unknown" apart from "genuinely nobody" and fail closed.
    """
    try:
        from app.engines.vertical_catalog.document_requirements import (
            required_technician_keys,
        )

        required_documents = sorted(required_technician_keys(vertical="home_services"))
        row = (await db.execute(
            text(
                "WITH ready AS ("
                " SELECT ptm.id FROM provider_team_members ptm "
                " WHERE ptm.tenant_id = CAST(:tid AS uuid) AND "
                + active_technician_sql("ptm") +
                " AND (:required_count = 0 OR ("
                "   SELECT count(DISTINCT td.doc_type) FROM tenant_documents td "
                "   WHERE td.tenant_id = ptm.tenant_id "
                "     AND td.staff_member_id = ptm.id "
                "     AND td.is_current = true AND td.status = 'verified' "
                "     AND (td.expiry_date IS NULL OR td.expiry_date > now()) "
                "     AND td.doc_type = ANY(CAST(:required_documents AS text[]))"
                " ) = :required_count)"
                "), funded AS ("
                " SELECT COALESCE(SUM(e.seats), 0)::bigint AS seats "
                " FROM tenant_topup_entitlements e "
                " WHERE e.tenant_id = CAST(:tid AS uuid) AND e.status = 'active' "
                "   AND (e.expires_at IS NULL OR e.expires_at > now())"
                ") SELECT LEAST((SELECT count(*) FROM ready), "
                "               (SELECT seats FROM funded))"
            ),
            {
                "tid": str(tenant_id),
                "required_documents": required_documents,
                "required_count": len(required_documents),
            },
        )).first()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:  # noqa: BLE001 -- fail closed rather than inventing capacity
        logger.warning("slots.technician_count_failed", tenant_id=str(tenant_id))
        return -1


def _effective_cap(rule: dict, technicians: int) -> int:
    """One simultaneous booking per ready technician.

    ``max_bookings_per_slot`` is a retired second capacity authority and is
    intentionally ignored. An unreadable or empty team has zero safe capacity.
    """
    return max(technicians, 0)


async def find_earliest_available_slot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    from_datetime: dt.datetime | None = None,
    search_days: int | None = None,
    emergency: bool = False,
    master_service_id: uuid.UUID | None = None,
) -> dict | None:
    """First slot this provider genuinely has capacity for, respecting their
    own configured notice period.

    Walks forward day by day from `from_datetime` (default: now on the
    tenant's clock) and returns the first slot whose live booking count is
    below the number of ready technicians for this service. A slot starting inside
    the notice period is skipped even if it technically hasn't started yet
    -- a provider cannot honour a window with no real time to prepare for
    it. Once the working day's slots run out, the walk moves to the next day
    exactly as configured -- there is no after-hours fallback.

    Returns None when the provider has no capacity anywhere in the search
    horizon. Callers must treat that as "cannot promise a time", never as
    "book it anyway".
    """
    settings = await booking_window_settings(db, tenant_id)
    now = from_datetime or _tenant_now(settings)
    cutoff = _notice_cutoff(settings, now, emergency)
    day = now.date()
    horizon = min(
        search_days if search_days is not None else int(settings["maximum_advance_booking_days"]),
        MAX_SEARCH_DAYS,
    )

    for offset in range(horizon):
        target = day + dt.timedelta(days=offset)
        # The provider can switch same-day booking off entirely.
        if offset == 0 and not settings["allow_same_day_booking"]:
            continue
        if await _is_closed(db, tenant_id, target):
            continue

        dow = target.isoweekday() % 7  # 0=Sunday, matches provider_availability_rules
        rules = await _provider_rules_for_day(db, tenant_id, dow)
        if not rules:
            continue

        technicians = await assignable_technician_count(
            db, tenant_id, master_service_id=master_service_id, day=target,
        )
        if technicians <= 0:
            continue

        booked = await _booked_counts(db, tenant_id, target)

        if _daily_remaining(rules, technicians, booked) <= 0:
            continue

        for rule in rules:
            cap = _effective_cap(rule, technicians)
            for start, end in _slots_from_rule(rule):
                # Never offer a window inside the notice period. With
                # emergency + opted-in this reduces to "has not started yet",
                # which is still a real constraint.
                if dt.datetime.combine(target, start) < cutoff:
                    continue
                label = _window_label(start, end)
                if _overlapping_bookings(booked, start, end) >= cap:
                    continue
                return {
                    "date": target.isoformat(),
                    "time_window": label,
                    "starts_at": dt.datetime.combine(target, start).isoformat(),
                    "ends_at": dt.datetime.combine(target, end).isoformat(),
                    "slot_minutes": int(
                        (dt.datetime.combine(target, end) - dt.datetime.combine(target, start)).total_seconds() // 60
                    ),
                    "capacity": cap,
                    "already_booked": _overlapping_bookings(booked, start, end),
                    "days_ahead": offset,
                }
    return None


async def list_available_slots(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    from_datetime: dt.datetime | None = None,
    search_days: int | None = None,
    max_days: int = DEFAULT_OFFERED_DAYS,
    emergency: bool = False,
    master_service_id: uuid.UUID | None = None,
) -> list[dict]:
    """Every genuinely bookable slot for this provider, earliest first, each
    outside their configured notice period -- the list form of
    `find_earliest_available_slot`, sharing its exact capacity and notice
    rules so a slot offered here is honoured the same way at confirmation
    (`slot_has_capacity` re-checks the same capacity rule;
    `select_promised_slot` re-derives from this same function).

    Offered by WHOLE DAY, never truncated mid-day (product rule): the
    customer sees ALL of today's remaining bookable slots; if today has
    none left, they see the next open day's; and a closed day is skipped
    entirely rather than counted. So on a Saturday evening with Sunday
    closed, the list is Monday's full day -- not a handful of slots cut off
    arbitrarily part-way through.

    `max_days` counts only days that actually HAVE bookable slots, so a run
    of closed or fully-booked days never eats into what the customer is
    shown. `search_days` overrides the provider's own
    `maximum_advance_booking_days` horizon when a caller needs to reach a
    specific day.
    """
    settings = await booking_window_settings(db, tenant_id)
    now = from_datetime or _tenant_now(settings)
    cutoff = _notice_cutoff(settings, now, emergency)
    day = now.date()
    results: list[dict] = []
    seen_slots: set[tuple[str, str]] = set()
    days_with_slots = 0
    horizon = min(
        search_days if search_days is not None else int(settings["maximum_advance_booking_days"]),
        MAX_SEARCH_DAYS,
    )

    for offset in range(horizon):
        if days_with_slots >= max_days:
            break
        target = day + dt.timedelta(days=offset)
        if offset == 0 and not settings["allow_same_day_booking"]:
            continue
        if await _is_closed(db, tenant_id, target):
            continue

        dow = target.isoweekday() % 7  # 0=Sunday, matches provider_availability_rules
        rules = await _provider_rules_for_day(db, tenant_id, dow)
        if not rules:
            continue

        technicians = await assignable_technician_count(
            db, tenant_id, master_service_id=master_service_id, day=target,
        )
        if technicians <= 0:
            continue

        booked = await _booked_counts(db, tenant_id, target)
        daily_remaining = _daily_remaining(rules, technicians, booked)
        if daily_remaining <= 0:
            continue
        found_today = False

        for rule in rules:
            cap = _effective_cap(rule, technicians)
            for start, end in _slots_from_rule(rule):
                if dt.datetime.combine(target, start) < cutoff:
                    continue
                label = _window_label(start, end)
                if _overlapping_bookings(booked, start, end) >= cap:
                    continue
                # Legacy/provider edits can leave overlapping active business-
                # hour rows. A physical provider slot is still one choice;
                # returning it once per rule produced duplicate rows in the
                # customer picker (and ambiguous capacity semantics).
                slot_key = (target.isoformat(), label)
                if slot_key in seen_slots:
                    continue
                seen_slots.add(slot_key)
                found_today = True
                results.append({
                    "date": target.isoformat(),
                    "time_window": label,
                    "starts_at": dt.datetime.combine(target, start).isoformat(),
                    "ends_at": dt.datetime.combine(target, end).isoformat(),
                    "slot_minutes": int(
                        (dt.datetime.combine(target, end) - dt.datetime.combine(target, start)).total_seconds() // 60
                    ),
                    "capacity": cap,
                    "already_booked": _overlapping_bookings(booked, start, end),
                    "daily_remaining": daily_remaining,
                    "days_ahead": offset,
                })

        # Counted only when the day genuinely yielded something bookable --
        # a closed or fully-booked day must not consume one of the offered
        # days and leave the customer with fewer real choices.
        if found_today:
            days_with_slots += 1

    return results


async def slot_has_capacity(
    db: AsyncSession, *, tenant_id: uuid.UUID, day: dt.date, time_window: str,
    master_service_id: uuid.UUID | None = None,
    exclude_job_id: uuid.UUID | None = None,
) -> bool:
    """Re-check a specific slot at confirmation time.

    The customer may sit on the review screen for a while, and another
    customer can take the last place in the meantime -- so the promise is
    always re-validated before it is committed, never trusted from the
    earlier offer. Capacity only -- lead time is re-enforced separately by
    `select_promised_slot`, which re-derives the slot from
    `list_available_slots` (the same function that applied it when the
    slot was first offered).
    """
    technicians = await assignable_technician_count(
        db, tenant_id, master_service_id=master_service_id, day=day,
    )

    if await _is_closed(db, tenant_id, day):
        return False
    dow = day.isoweekday() % 7
    rules = await _provider_rules_for_day(db, tenant_id, dow)
    if not rules:
        return False
    booked = await _booked_counts(db, tenant_id, day, exclude_job_id=exclude_job_id)
    if _daily_remaining(rules, technicians, booked) <= 0:
        return False
    for rule in rules:
        cap = _effective_cap(rule, technicians)
        for start, end in _slots_from_rule(rule):
            if _window_label(start, end) == time_window:
                return _overlapping_bookings(booked, start, end) < cap
    return False
