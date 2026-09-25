"""Expired customer commitments must enter slot recovery, never assignment."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.engines.home_service_assignment.constants import ERR_VISIT_SLOT_EXPIRED
from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
from app.engines.weather.slots import slot_end, slot_has_ended


def _past_job(*, assigned_staff_id=None):
    local_today = datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=5, minutes=30))
    ).date()
    return SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        status="pending_assignment", assignment_status="unassigned",
        assigned_staff_id=assigned_staff_id,
        scheduled_date=local_today - timedelta(days=1),
        scheduled_time_window="16:30-18:30",
    )


def test_expiry_understands_customer_friendly_am_pm_windows():
    job = _past_job()
    assert slot_end(job.scheduled_date, "4:30 PM - 6:30 PM").hour == 18
    assert slot_has_ended(job.scheduled_date, "4:30 PM - 6:30 PM") is True


def test_date_without_committed_window_is_not_treated_as_expired():
    job = _past_job()
    assert slot_has_ended(job.scheduled_date, None) is False


@pytest.mark.asyncio
async def test_manual_assignment_is_blocked_before_staff_or_state_mutation():
    job = _past_job()
    service = HomeServiceJobAssignmentService(AsyncMock())
    service._load_job = AsyncMock(return_value=job)
    service._current_assignment = AsyncMock()
    service.validate_staff_eligibility = AsyncMock()

    with pytest.raises(ValueError, match=ERR_VISIT_SLOT_EXPIRED):
        await service.assign_job(
            job.id, uuid.uuid4(), job.tenant_id,
        )

    service._current_assignment.assert_not_awaited()
    service.validate_staff_eligibility.assert_not_awaited()


@pytest.mark.asyncio
async def test_unaccepted_technician_cannot_accept_an_expired_visit():
    staff_id = uuid.uuid4()
    job = _past_job(assigned_staff_id=staff_id)
    assignment = SimpleNamespace(
        assigned_staff_member_id=staff_id,
        assignment_status="assigned",
    )
    service = HomeServiceJobAssignmentService(AsyncMock())
    service._load_job = AsyncMock(return_value=job)
    service._current_assignment = AsyncMock(return_value=assignment)

    with pytest.raises(ValueError, match=ERR_VISIT_SLOT_EXPIRED):
        await service.technician_accept_job(job.id, staff_id, tenant_id=job.tenant_id)

    assert assignment.assignment_status == "assigned"
