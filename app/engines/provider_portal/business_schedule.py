"""Atomic, provider-owned weekly hours and booking-window configuration."""
import datetime as dt
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from app.exceptions import ServiceOSException

WINDOW_DEFAULTS = dict(minimum_notice_minutes=120, maximum_advance_booking_days=7,
                       slot_duration_minutes=120, buffer_minutes_between_jobs=30,
                       allow_same_day_booking=True, emergency_booking_allowed=False,
                       timezone="Asia/Kolkata")


def normalize_time(value, optional=False):
    if value is None or value == "":
        if optional:
            return None
        raise ServiceOSException("INVALID_AVAILABILITY_TIME", "Enter a complete time in HH:MM format.", status_code=422)
    try:
        parsed = dt.time.fromisoformat(str(value))
        if parsed.second or parsed.microsecond or parsed.tzinfo:
            raise ValueError()
        return parsed.strftime("%H:%M")
    except (ValueError, TypeError):
        raise ServiceOSException("INVALID_AVAILABILITY_TIME", "Enter a valid time in HH:MM format.", status_code=422)


def validate_window(window):
    for field, minimum, maximum in (
        ("minimum_notice_minutes", 0, 43200), ("maximum_advance_booking_days", 1, 62),
        ("buffer_minutes_between_jobs", 0, 1440),
    ):
        value = window.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ServiceOSException("INVALID_BOOKING_WINDOW", f"{field.replace('_', ' ')} must be a whole number between {minimum} and {maximum}.", status_code=422)
    for field in ("allow_same_day_booking", "emergency_booking_allowed"):
        if not isinstance(window.get(field), bool):
            raise ServiceOSException("INVALID_BOOKING_WINDOW", f"{field} must be enabled or disabled.", status_code=422)
    try:
        ZoneInfo(window["timezone"])
    except (ZoneInfoNotFoundError, TypeError, KeyError, ValueError):
        raise ServiceOSException("INVALID_TIMEZONE", "Select a valid business timezone.", status_code=422)


async def persist_window(db, tenant_id, payload):
    if not isinstance(payload, dict):
        raise ServiceOSException("INVALID_BOOKING_WINDOW", "Booking controls must be an object.", status_code=422)
    row = (await db.execute(text("SELECT * FROM tenant_booking_window_settings WHERE tenant_id=:tid FOR UPDATE"), {"tid": str(tenant_id)})).fetchone()
    current = dict(row._mapping) if row else {}
    merged = {**WINDOW_DEFAULTS, **current, **{k: v for k, v in payload.items() if k in WINDOW_DEFAULTS}, "slot_duration_minutes": 120}
    validate_window(merged)
    columns = list(WINDOW_DEFAULTS)
    await db.execute(text(
        f"INSERT INTO tenant_booking_window_settings (tenant_id,{','.join(columns)}) "
        f"VALUES (:tid,{','.join(':'+c for c in columns)}) ON CONFLICT (tenant_id) DO UPDATE SET "
        + ','.join(f"{c}=EXCLUDED.{c}" for c in columns) + ",updated_at=now()"
    ), {"tid": str(tenant_id), **{c: merged[c] for c in columns}})
    return merged


async def save_week(db, tenant_id, payload):
    from app.engines.home_service_booking.provider_slot_service import _slots_from_rule
    from app.engines.vertical_catalog.seat_enforcement import get_seat_usage
    from app.engines.provider_portal.router import _validate_availability_time_range, _validate_break_time
    rules = payload.get("rules")
    if not isinstance(rules, list) or len(rules) != 7 or any(not isinstance(r, dict) for r in rules):
        raise ServiceOSException("INVALID_WEEKLY_SCHEDULE", "Provide one schedule for each of the seven days.", status_code=422)
    days = [r.get("day_of_week") for r in rules]
    if any(isinstance(d, bool) or not isinstance(d, int) for d in days) or set(days) != set(range(7)):
        raise ServiceOSException("INVALID_WEEKLY_SCHEDULE", "Each weekday must appear exactly once.", status_code=422)
    # Lock the workspace, including the first save when no schedule row exists.
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"business-schedule:{tenant_id}"})
    window = await persist_window(db, tenant_id, payload.get("booking_window") or {})
    usage = await get_seat_usage(db, tenant_id)
    capacity = min(usage["entitled_seats"], usage["used_seats"])
    result = []
    for rule in rules:
        rule = {**rule, "start_time": normalize_time(rule.get("start_time")), "end_time": normalize_time(rule.get("end_time")),
                "break_start_time": normalize_time(rule.get("break_start_time"), True),
                "break_end_time": normalize_time(rule.get("break_end_time"), True),
                "buffer_minutes_between_jobs": window["buffer_minutes_between_jobs"]}
        if not isinstance(rule.get("is_active"), bool):
            raise ServiceOSException("INVALID_WEEKLY_SCHEDULE", "Choose open or closed for each day.", status_code=422)
        _validate_availability_time_range(rule["start_time"], rule["end_time"])
        _validate_break_time(rule["start_time"], rule["end_time"], rule["break_start_time"], rule["break_end_time"])
        slots = _slots_from_rule(rule)
        if rule["is_active"] and not slots:
            raise ServiceOSException("NO_COMPLETE_JOB_WINDOW", "Each open day needs at least one complete two-hour job window outside its break.", status_code=422)
        limit = rule.get("max_jobs_per_day")
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
                                  or (rule["is_active"] and limit > len(slots) * capacity)):
            raise ServiceOSException("DAILY_CAPACITY_EXCEEDS_TEAM", f"Daily jobs cannot exceed {len(slots) * capacity} for these hours. Reduce the limit or choose Automatic.", status_code=422)
        existing = (await db.execute(text(
            "SELECT id FROM provider_availability_rules WHERE tenant_id=:tid AND scope_type='provider' "
            "AND scope_id IS NULL AND day_of_week=:day ORDER BY is_active DESC,updated_at DESC,created_at DESC,id DESC LIMIT 1 FOR UPDATE"
        ), {"tid": str(tenant_id), "day": rule["day_of_week"]})).scalar()
        rid = str(existing or uuid.uuid4())
        params = {"id": rid, "tid": str(tenant_id), "day": rule["day_of_week"], "start": rule["start_time"], "end": rule["end_time"],
                  "bs": rule["break_start_time"], "be": rule["break_end_time"], "limit": limit, "active": rule["is_active"], "tz": window["timezone"]}
        await db.execute(text("""
            INSERT INTO provider_availability_rules (id,tenant_id,scope_type,day_of_week,start_time,end_time,
                break_start_time,break_end_time,max_jobs_per_day,is_active,slot_duration_minutes,timezone)
            VALUES (:id,:tid,'provider',:day,:start,:end,:bs,:be,:limit,:active,120,:tz)
            ON CONFLICT (id) DO UPDATE SET start_time=:start,end_time=:end,break_start_time=:bs,break_end_time=:be,
                max_jobs_per_day=:limit,is_active=:active,slot_duration_minutes=120,timezone=:tz,updated_at=now()
        """), params)
        # Keep historical rows recoverable, but never sell duplicate working hours.
        await db.execute(text("UPDATE provider_availability_rules SET is_active=false WHERE tenant_id=:tid "
                              "AND scope_type='provider' AND scope_id IS NULL AND day_of_week=:day AND id<>:id"), params)
        row = (await db.execute(text("SELECT * FROM provider_availability_rules WHERE id=:id AND tenant_id=:tid"), params)).one()
        result.append(dict(row._mapping))
    return {"rules": result, "booking_window": window}
