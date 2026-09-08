import datetime as dt
import os
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.engines.provider_portal.business_schedule import normalize_time, validate_window, WINDOW_DEFAULTS, save_week, persist_window
from app.engines.home_service_booking.provider_slot_service import _slots_from_rule
from app.exceptions import ServiceOSException


@pytest.mark.parametrize("value", [None, "", "25:00", "9", "12:70", "09:00:03"])
def test_incomplete_times_are_rejected(value):
    with pytest.raises(ServiceOSException): normalize_time(value)


def test_seconds_are_normalized_and_breaks_can_be_cleared():
    assert normalize_time("09:00:00") == "09:00"
    assert normalize_time("", True) is None


@pytest.mark.parametrize("field,value", [("minimum_notice_minutes", "1"), ("maximum_advance_booking_days", 0), ("maximum_advance_booking_days", 63), ("buffer_minutes_between_jobs", -1), ("timezone", "fake/time"), ("allow_same_day_booking", "yes")])
def test_invalid_booking_controls_are_rejected(field, value):
    with pytest.raises(ServiceOSException): validate_window({**WINDOW_DEFAULTS, field: value})


def test_break_and_travel_buffer_reduce_real_job_windows():
    rule = dict(start_time="09:00", end_time="18:00", break_start_time="13:00", break_end_time="14:00", buffer_minutes_between_jobs=30)
    assert _slots_from_rule(rule) == [(dt.time(9),dt.time(11)), (dt.time(14),dt.time(16))]
    rule.update(break_start_time=None, break_end_time=None)
    assert len(_slots_from_rule(rule)) == 3
    rule["buffer_minutes_between_jobs"] = 0
    assert len(_slots_from_rule(rule)) == 4


@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("RUN_LOCAL_SCHEDULE_DB_TEST") != "1", reason="Local PostgreSQL integration")
async def test_atomic_week_preserves_controls_reopens_days_and_rolls_back_invalid_save(monkeypatch):
    from app.config import get_settings
    from app.engines.vertical_catalog import seat_enforcement
    url = make_url(get_settings().DATABASE_URL)
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    monkeypatch.setattr(seat_enforcement, "get_seat_usage", AsyncMock(return_value={"entitled_seats":3,"used_seats":3}))
    engine = create_async_engine(url, echo=False)
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            try:
                async with AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                    tid = (await db.execute(text("SELECT tenant_id FROM users WHERE role='tenant_owner' AND tenant_id IS NOT NULL LIMIT 1"))).scalar_one()
                    rules = [dict(day_of_week=d, start_time="09:00", end_time="18:00", is_active=d==1, max_jobs_per_day=None) for d in range(7)]
                    result = await save_week(db, tid, {"rules":rules,"booking_window": {"minimum_notice_minutes":180,"maximum_advance_booking_days":14,"buffer_minutes_between_jobs":0}})
                    await db.commit()
                    monday = next(r for r in result["rules"] if r["day_of_week"] == 1)
                    partial = await persist_window(db, tid, {"allow_same_day_booking":False})
                    assert partial["minimum_notice_minutes"] == 180 and partial["maximum_advance_booking_days"] == 14
                    rules[1].update(start_time="10:00", end_time="19:00", is_active=False)
                    await save_week(db, tid, {"rules":rules})
                    rules[1]["is_active"] = True
                    result = await save_week(db, tid, {"rules":rules})
                    reopened = next(r for r in result["rules"] if r["day_of_week"] == 1)
                    assert reopened["id"] == monday["id"] and reopened["start_time"] == "10:00"
                    assert (await db.execute(text("SELECT count(*) FROM provider_availability_rules WHERE tenant_id=:tid AND scope_type='provider' AND scope_id IS NULL AND day_of_week=1 AND is_active=true"), {"tid":tid})).scalar_one() == 1
                    async with db.begin_nested() as savepoint:
                        rules[1]["max_jobs_per_day"] = 99
                        with pytest.raises(ServiceOSException): await save_week(db,tid,{"rules":rules,"booking_window":{"minimum_notice_minutes":60}})
                        await savepoint.rollback()
                    assert (await db.execute(text("SELECT minimum_notice_minutes FROM tenant_booking_window_settings WHERE tenant_id=:tid"), {"tid":tid})).scalar_one() == 180

                    # The customer slot engine reads this exact saved schedule,
                    # not a disconnected provider-only preview calculation.
                    from app.engines.home_service_booking import provider_slot_service as slots
                    monkeypatch.setattr(slots, "assignable_technician_count", AsyncMock(return_value=3))
                    monkeypatch.setattr(slots, "_booked_counts", AsyncMock(return_value={"10:00-12:00": 1}))
                    rules[1].update(max_jobs_per_day=6, break_start_time="12:00", break_end_time="13:00")
                    await save_week(db, tid, {"rules": rules, "booking_window": {"buffer_minutes_between_jobs": 30}})
                    day = dt.date(2099, 1, 5)  # Monday, isolated from today's bookings.
                    assert day.weekday() == 0
                    preview = await slots.daily_slot_preview(db, tid, day)
                    assert preview["daily_remaining"] == 5
                    assert [s["time_window"] for s in preview["slots"]] == ["10:00-12:00", "13:00-15:00", "15:30-17:30"]
                    assert [s["capacity"] for s in preview["slots"]] == [2, 2, 2]
                    assert [s["available_slots"] for s in preview["slots"]] == [1, 2, 2]
                    # A full-day holiday takes precedence even with another exception on the day.
                    for full_day in (False, True):
                        await db.execute(text("INSERT INTO tenant_availability_exceptions (id,tenant_id,date,reason,full_day_closed,start_time,end_time,status) VALUES (gen_random_uuid(),:tid,:day,'Schedule test',:closed,'10:00','12:00','active')"), {"tid": tid, "day": day, "closed": full_day})
                    closed = await slots.daily_slot_preview(db, tid, day)
                    assert closed["closed"] and closed["slots"] == [] and closed["daily_remaining"] == 0
            finally: await outer.rollback()
    finally: await engine.dispose()
