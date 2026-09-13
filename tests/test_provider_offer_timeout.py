"""An unanswered provider offer reroutes or closes at its own deadline."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.jobs import provider_assignment_timeout as timeout
from app.engines.final_records.tenant_bookings_jobs_router import _offer_expired


@pytest.fixture
def offer(monkeypatch):
    from app.engines.tenant_engine import health
    from app.engines.vertical_monetization import runtime_operations

    now = datetime.now(timezone.utc)
    old_tenant = uuid.uuid4()
    job = NS(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=old_tenant,
        status="accepted", assignment_status="unassigned", assigned_staff_id=None,
        provider_offer_started_at=now - timedelta(minutes=16),
        created_at=now - timedelta(minutes=16), updated_at=now - timedelta(minutes=1),
        failure_reason=None,
    )
    booking = NS(
        id=job.booking_id, tenant_id=old_tenant, status="accepted",
        assignment_status="unassigned", provider_snapshot=None, failure_reason=None,
    )
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [job]
    db.execute.return_value = result
    db.scalar.return_value = None
    db.get.return_value = booking
    db.add = MagicMock()
    db.add_all = MagicMock()
    monkeypatch.setattr(runtime_operations, "get_home_services_operations_policy",
                        AsyncMock(return_value=NS(assignment_timeout_enabled=True,
                                                  assignment_timeout_minutes=15)))
    health_refresh = AsyncMock()
    monkeypatch.setattr(health, "refresh_provider_operational_health", health_refresh)
    return NS(db=db, job=job, booking=booking, old_tenant=old_tenant,
              health_refresh=health_refresh)


@pytest.mark.asyncio
async def test_timeout_reroutes_and_starts_a_new_fifteen_minute_window(offer, monkeypatch):
    replacement = uuid.uuid4()
    monkeypatch.setattr(timeout, "_find_replacement", AsyncMock(return_value=(replacement, {"name": "Next"})))

    before = datetime.now(timezone.utc)
    result = await timeout.sweep(offer.db)

    assert result["reassigned"] == 1 and result["closed"] == 0
    assert offer.job.tenant_id == replacement
    assert offer.booking.tenant_id == replacement
    assert offer.job.provider_offer_started_at >= before
    assert offer.job.assignment_status == "unassigned"
    statement = offer.db.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "coalesce(service_jobs.provider_offer_started_at, service_jobs.created_at) <=" in sql
    assert "updated_at <=" not in sql
    seen_sql = str(offer.db.scalar.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "service_job_execution_events.created_at >=" in seen_sql
    offer.health_refresh.assert_awaited_once_with(offer.db, offer.old_tenant)


@pytest.mark.asyncio
async def test_timeout_closes_when_no_other_provider_can_take_the_job(offer, monkeypatch):
    monkeypatch.setattr(timeout, "_find_replacement", AsyncMock(return_value=None))

    result = await timeout.sweep(offer.db)

    assert result["reassigned"] == 0 and result["closed"] == 1
    assert offer.job.status == "cancelled" and offer.booking.status == "cancelled"
    assert "no alternative provider" in offer.job.failure_reason
    assert offer.booking.failure_reason == offer.job.failure_reason
    event = offer.db.add_all.call_args.args[0][0]
    assert event.tenant_id == offer.old_tenant
    assert event.event_type == "provider_assignment_timeout"
    assert event.event_metadata["outcome"] == "closed_no_alternative_provider"
    offer.health_refresh.assert_awaited_once_with(offer.db, offer.old_tenant)


@pytest.mark.asyncio
async def test_each_unanswered_provider_is_penalized_and_final_offer_closes(offer, monkeypatch):
    replacement = uuid.uuid4()
    find_replacement = AsyncMock(side_effect=[
        (replacement, {"name": "Next"}), None,
    ])
    monkeypatch.setattr(timeout, "_find_replacement", find_replacement)

    first = await timeout.sweep(offer.db)
    offer.job.provider_offer_started_at -= timedelta(minutes=16)
    second = await timeout.sweep(offer.db)

    assert first["reassigned"] == 1
    assert second["closed"] == 1
    assert offer.job.status == "cancelled" and offer.booking.status == "cancelled"
    assert offer.health_refresh.await_args_list[0].args[1] == offer.old_tenant
    assert offer.health_refresh.await_args_list[1].args[1] == replacement
    assert find_replacement.await_count == 2


def test_booking_drawer_does_not_offer_expired_or_transferred_assignments(offer):
    now = datetime.now(timezone.utc)
    offer.job.provider_offer_started_at = None  # legacy job uses creation time
    assert _offer_expired(offer.job, enabled=True, minutes=15, now=now)
    assert not _offer_expired(offer.job, enabled=False, minutes=15, now=now)
    offer.job.assigned_staff_id = uuid.uuid4()
    assert not _offer_expired(offer.job, enabled=True, minutes=15, now=now)


@pytest.mark.asyncio
async def test_admin_reopen_starts_a_fresh_offer_window(monkeypatch):
    from app.engines.execution import admin_job_actions

    now = datetime.now(timezone.utc)
    job = NS(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        status="cancelled", assigned_staff_id=None, assignment_status="cancelled",
        failure_reason="Prior timeout", provider_offer_started_at=now - timedelta(days=1),
    )
    booking = NS(status="cancelled", assignment_status="cancelled", failure_reason="Prior timeout")
    db = AsyncMock()
    job_result = MagicMock()
    job_result.scalars.return_value.first.return_value = job
    assignment_result = MagicMock()
    assignment_result.scalars.return_value.first.return_value = None
    db.execute.side_effect = [job_result, assignment_result]
    db.get.return_value = booking
    db.add = MagicMock()
    service = admin_job_actions.AdminJobActionsService(db)
    monkeypatch.setattr(admin_job_actions, "record_platform_audit", AsyncMock())

    result = await service.override_status(
        job.id, "pending_assignment", "cancelled", "admin_reopen",
        "Retry provider assignment", uuid.uuid4(), "platform_admin", None,
    )

    assert result["new_status"] == "pending_assignment"
    assert job.provider_offer_started_at >= now
    assert booking.status == "pending_assignment"
