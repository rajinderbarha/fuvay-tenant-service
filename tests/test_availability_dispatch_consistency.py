"""Availability must not advertise jobs that Dispatch has already closed."""
import datetime as dt
import uuid
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

import pytest

from app.engines.home_service_assignment import availability_resolver as resolver


@pytest.mark.asyncio
async def test_availability_uses_booking_date_and_excludes_closed_records():
    tenant_id, staff_id, job_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    day = dt.date(2026, 9, 14)
    db = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = [SimpleNamespace(_mapping={
        "id": job_id, "job_number": "JOB-NEW", "status": "assigned",
        "scheduled_time_window": "14:00-16:00", "service_name": "AC Repair",
    })]
    db.execute = AsyncMock(return_value=result)

    jobs = await resolver._fetch_assignments(db, tenant_id, staff_id, day)

    assert jobs[0]["job_number"] == "JOB-NEW"
    query, params = db.execute.await_args.args
    assert "COALESCE(j.scheduled_date, b.preferred_date)=:d" in query.text
    assert "COALESCE(j.scheduled_time_window, b.preferred_time_window)" in query.text
    assert "b.status != ALL" in query.text and "j.status != ALL" in query.text
    assert "completed" in params["terminal_statuses"]


@pytest.mark.asyncio
async def test_unassigned_bookings_are_returned_without_a_technician_roster():
    tenant_id, job_id = uuid.uuid4(), uuid.uuid4()
    day = dt.date(2026, 9, 14)
    db = MagicMock()
    count = MagicMock()
    count.scalar.return_value = 1
    rows = MagicMock()
    rows.all.return_value = [SimpleNamespace(
        id=job_id, job_number="JOB-NEW", status="pending_assignment",
        scheduled_date=day, time_window="14:00-16:00", service_name="AC Repair",
    )]
    db.execute = AsyncMock(side_effect=[count, rows])

    jobs, total = await resolver._fetch_unassigned_week(db, tenant_id, day, day)

    assert total == 1
    assert jobs == [{
        "job_id": str(job_id), "job_number": "JOB-NEW",
        "status": "pending_assignment", "date": "2026-09-14",
        "time_window": "14:00-16:00", "service_name": "AC Repair",
    }]
    for call in db.execute.await_args_list:
        query = call.args[0].text
        assert "j.assigned_staff_id IS NULL" in query
        assert "COALESCE(j.scheduled_date, b.preferred_date) BETWEEN" in query
        assert "b.status != ALL" in query


@pytest.mark.asyncio
async def test_availability_only_lists_nonterminal_assignments_even_on_closed_day(monkeypatch):
    active_id, completed_id, cancelled_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    assignments = [
        {"id": active_id, "job_number": "JOB-A", "status": "scheduled",
         "scheduled_time_window": "09:00-11:00", "service_name": "AC Repair"},
        {"id": completed_id, "job_number": "JOB-B", "status": "completed",
         "scheduled_time_window": "11:00-13:00", "service_name": "AC Repair"},
        {"id": cancelled_id, "job_number": "JOB-C", "status": "cancelled",
         "scheduled_time_window": "13:00-15:00", "service_name": "AC Repair"},
    ]
    monkeypatch.setattr(resolver, "_fetch_assignments", AsyncMock(return_value=assignments))
    monkeypatch.setattr(resolver, "_fetch_tenant_exception", AsyncMock(return_value={"full_day_closed": True}))

    day = await resolver.resolve_staff_day(
        MagicMock(), uuid.uuid4(), uuid.uuid4(), dt.date(2026, 9, 14),
    )

    assert [job["job_id"] for job in day["assignments_today"]] == [str(active_id)]
    assert day["overlapping_jobs"] == ["JOB-A"]


@pytest.mark.asyncio
async def test_completed_job_does_not_fill_an_open_day_or_appear_in_week(monkeypatch):
    active_id, completed_id = uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(resolver, "_fetch_assignments", AsyncMock(return_value=[
        {"id": active_id, "job_number": "JOB-A", "status": "scheduled",
         "scheduled_time_window": "09:00-11:00", "service_name": "AC Repair"},
        {"id": completed_id, "job_number": "JOB-B", "status": "completed",
         "scheduled_time_window": "11:00-13:00", "service_name": "AC Repair"},
    ]))
    monkeypatch.setattr(resolver, "_fetch_tenant_exception", AsyncMock(return_value=None))
    rule = {"start_time": dt.time(9), "end_time": dt.time(19),
            "break_start_time": None, "break_end_time": None, "max_jobs_per_day": 3}
    monkeypatch.setattr(resolver, "_fetch_business_hours", AsyncMock(return_value=[rule]))
    monkeypatch.setattr(resolver, "_fetch_staff", AsyncMock(return_value={
        "status": "active", "deleted_at": None,
    }))
    monkeypatch.setattr(resolver, "_fetch_staff_pattern", AsyncMock(return_value=rule))
    monkeypatch.setattr(resolver, "_staff_override", AsyncMock(return_value=None))
    monkeypatch.setattr(resolver, "_staff_time_off", AsyncMock(return_value=None))

    day = await resolver.resolve_staff_day(
        MagicMock(), uuid.uuid4(), uuid.uuid4(), dt.date(2026, 9, 14),
    )

    assert day["available"] is True
    assert [job["job_id"] for job in day["assignments_today"]] == [str(active_id)]
    assert day["daily_capacity"]["used"] == 1
