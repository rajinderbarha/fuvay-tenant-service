"""Provider ownership is fixed; assignment timeout escalates within it."""
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.final_records.tenant_bookings_jobs_router import _offer_expired
from app.engines.home_service_assignment.assignment_deadlines import for_job
from app.jobs import provider_assignment_timeout as timeout


def policy(**overrides):
    values = dict(
        assignment_timeout_enabled=True, assignment_timeout_minutes=30,
        urgent_assignment_timeout_minutes=10,
        urgent_assignment_threshold_minutes=120,
        assignment_auto_assign_enabled=True,
    )
    values.update(overrides)
    return NS(**values)


def job(*, minutes_old=31, scheduled_date=None, scheduled_time_window=None):
    now = datetime.now(timezone.utc)
    return NS(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        status="pending_assignment", assignment_status="unassigned",
        assigned_staff_id=None, provider_offer_started_at=now-timedelta(minutes=minutes_old),
        created_at=now-timedelta(minutes=minutes_old), updated_at=now,
        scheduled_date=scheduled_date, scheduled_time_window=scheduled_time_window,
    )


def test_normal_and_urgent_assignment_windows():
    now = datetime.now(timezone.utc)
    normal = job(minutes_old=11, scheduled_date=date.today()+timedelta(days=1), scheduled_time_window="10:00-12:00")
    visit = now.astimezone(timezone(timedelta(hours=5, minutes=30))) + timedelta(hours=1)
    urgent = job(
        minutes_old=11, scheduled_date=visit.date(),
        scheduled_time_window=f"{visit:%H:%M}-{(visit + timedelta(hours=1)):%H:%M}",
    )
    assert not for_job(normal, policy(), now).overdue
    urgent_result = for_job(urgent, policy(), now)
    assert urgent_result.urgent and urgent_result.minutes == 10 and urgent_result.overdue


@pytest.mark.asyncio
async def test_timeout_auto_assigns_inside_same_provider(monkeypatch):
    from app.engines.tenant_engine import health
    from app.engines.vertical_monetization import runtime_operations

    target = job()
    staff_id = uuid.uuid4()
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [target]
    workload_result = MagicMock()
    workload_result.all.return_value = []
    db = AsyncMock()
    db.execute.side_effect = [candidate_result, workload_result]
    db.scalar.return_value = None
    db.add = MagicMock()
    service = AsyncMock()
    service.list_eligible_staff_for_job.return_value = {
        "eligible_staff": [{"staff_member_id": str(staff_id), "name": "Tech"}],
        "blocked_staff": [],
    }
    monkeypatch.setattr(timeout, "HomeServiceJobAssignmentService", lambda _db: service)
    monkeypatch.setattr(runtime_operations, "get_home_services_operations_policy", AsyncMock(return_value=policy()))
    refresh = AsyncMock()
    monkeypatch.setattr(health, "refresh_provider_operational_health", refresh)

    result = await timeout.sweep(db)

    assert result == {
        "examined": 1, "auto_assigned": 1, "escalated": 1,
        "assignment_timeout_minutes": 30, "urgent_assignment_timeout_minutes": 10,
    }
    kwargs = service.assign_job.await_args.kwargs
    assert kwargs["tenant_id"] == target.tenant_id
    assert kwargs["assignment_type"] == "auto"
    assert target.tenant_id == kwargs["tenant_id"]  # no provider transfer
    refresh.assert_awaited_once_with(db, target.tenant_id)


@pytest.mark.asyncio
async def test_no_eligible_technician_keeps_job_open(monkeypatch):
    from app.engines.tenant_engine import health
    from app.engines.vertical_monetization import runtime_operations

    target = job()
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [target]
    db = AsyncMock()
    db.execute.return_value = candidate_result
    db.scalar.return_value = None
    db.add = MagicMock()
    service = AsyncMock()
    service.list_eligible_staff_for_job.return_value = {"eligible_staff": [], "blocked_staff": []}
    monkeypatch.setattr(timeout, "HomeServiceJobAssignmentService", lambda _db: service)
    monkeypatch.setattr(runtime_operations, "get_home_services_operations_policy", AsyncMock(return_value=policy()))
    monkeypatch.setattr(health, "refresh_provider_operational_health", AsyncMock())

    result = await timeout.sweep(db)

    assert result["auto_assigned"] == 0 and result["escalated"] == 1
    assert target.status == "pending_assignment"
    assert target.tenant_id is not None
    service.assign_job.assert_not_awaited()


def test_booking_drawer_never_expires_provider_ownership():
    target = job(minutes_old=300)
    assert not _offer_expired(target, enabled=True, minutes=15, now=datetime.now(timezone.utc))
