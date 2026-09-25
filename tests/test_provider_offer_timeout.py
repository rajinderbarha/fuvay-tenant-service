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


class _Savepoint:
    """`db.begin_nested()` returns an async context manager, not a coroutine.

    The sweep wraps each job in its own savepoint so one provider at capacity
    cannot roll back every other job's escalation with it.
    """

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _sweep_db():
    session = AsyncMock()
    session.begin_nested = MagicMock(side_effect=lambda: _Savepoint())
    return session


def job(*, minutes_old=31, scheduled_date=None, scheduled_time_window=None,
        is_emergency=False, status="pending_assignment"):
    now = datetime.now(timezone.utc)
    return NS(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        status=status, assignment_status="unassigned",
        assigned_staff_id=None, provider_offer_started_at=now-timedelta(minutes=minutes_old),
        created_at=now-timedelta(minutes=minutes_old), updated_at=now,
        scheduled_date=scheduled_date, scheduled_time_window=scheduled_time_window,
        is_emergency=is_emergency,
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


def test_emergency_and_any_same_day_slot_use_ten_minutes():
    now = datetime(2026, 9, 13, 4, 0, tzinfo=timezone.utc)
    local_today = now.astimezone(timezone(timedelta(hours=5, minutes=30))).date()

    same_day = job(
        minutes_old=11, scheduled_date=local_today,
        scheduled_time_window="20:00-22:00",
    )
    future_emergency = job(
        minutes_old=11, scheduled_date=local_today + timedelta(days=2),
        scheduled_time_window="10:00-12:00", is_emergency=True,
    )

    for target in (same_day, future_emergency):
        target.provider_offer_started_at = now - timedelta(minutes=11)
        deadline = for_job(target, policy(), now)
        assert deadline.urgent is True
        assert deadline.minutes == 10
        assert deadline.overdue is True


def test_future_standard_slot_keeps_normal_assignment_window():
    now = datetime(2026, 9, 13, 4, 0, tzinfo=timezone.utc)
    local_today = now.astimezone(timezone(timedelta(hours=5, minutes=30))).date()
    target = job(
        minutes_old=11, scheduled_date=local_today + timedelta(days=2),
        scheduled_time_window="10:00-12:00",
    )
    target.provider_offer_started_at = now - timedelta(minutes=11)
    deadline = for_job(target, policy(), now)
    assert deadline.urgent is False
    assert deadline.minutes == 30
    assert deadline.overdue is False


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
    db = _sweep_db()
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
async def test_timeout_never_auto_assigns_after_visit_window_ended(monkeypatch):
    from app.engines.tenant_engine import health
    from app.engines.vertical_monetization import runtime_operations

    local_today = datetime.now(timezone.utc).astimezone(
        timezone(timedelta(hours=5, minutes=30))
    ).date()
    target = job(
        scheduled_date=local_today - timedelta(days=1),
        scheduled_time_window="10:00-12:00",
    )
    target.job_number = "JOB-EXPIRED"
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [target]
    owner_result = MagicMock()
    owner_result.scalar.return_value = None
    db = _sweep_db()
    db.execute.side_effect = [candidate_result, owner_result]
    db.scalar.return_value = None
    db.add = MagicMock()
    service = AsyncMock()
    monkeypatch.setattr(timeout, "HomeServiceJobAssignmentService", lambda _db: service)
    monkeypatch.setattr(
        runtime_operations, "get_home_services_operations_policy",
        AsyncMock(return_value=policy()),
    )
    refresh = AsyncMock()
    monkeypatch.setattr(health, "refresh_provider_operational_health", refresh)

    result = await timeout.sweep(db)

    assert result["auto_assigned"] == 0
    assert result["escalated"] == 1
    service.list_eligible_staff_for_job.assert_not_awaited()
    service.assign_job.assert_not_awaited()
    refresh.assert_awaited_once_with(db, target.tenant_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_status", ["assigned", "scheduled"])
async def test_timeout_recovers_legacy_unassigned_statuses(monkeypatch, legacy_status):
    """A stale projection must not remain breached forever with no technician."""
    from app.engines.tenant_engine import health
    from app.engines.vertical_monetization import runtime_operations

    target = job(status=legacy_status)
    staff_id = uuid.uuid4()
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [target]
    workload_result = MagicMock()
    workload_result.all.return_value = []
    db = _sweep_db()
    db.execute.side_effect = [candidate_result, workload_result]
    db.scalar.return_value = None
    db.add = MagicMock()
    service = AsyncMock()
    service.list_eligible_staff_for_job.return_value = {
        "eligible_staff": [{"staff_member_id": str(staff_id), "name": "Tech"}],
        "blocked_staff": [],
    }
    monkeypatch.setattr(timeout, "HomeServiceJobAssignmentService", lambda _db: service)
    monkeypatch.setattr(
        runtime_operations, "get_home_services_operations_policy",
        AsyncMock(return_value=policy()),
    )
    monkeypatch.setattr(health, "refresh_provider_operational_health", AsyncMock())

    result = await timeout.sweep(db)

    assert result["auto_assigned"] == 1
    service.assign_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_eligible_technician_keeps_job_open(monkeypatch):
    from app.engines.tenant_engine import health
    from app.engines.vertical_monetization import runtime_operations

    target = job()
    candidate_result = MagicMock()
    candidate_result.scalars.return_value.all.return_value = [target]
    db = _sweep_db()
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
