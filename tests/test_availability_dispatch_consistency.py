"""Availability must not advertise jobs that Dispatch has already closed."""
import datetime as dt
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.home_service_assignment import availability_resolver as resolver


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
