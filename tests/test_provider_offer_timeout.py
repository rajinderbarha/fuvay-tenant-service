"""An unanswered provider offer reroutes or closes at its own deadline."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.jobs import provider_assignment_timeout as timeout


@pytest.fixture
def offer(monkeypatch):
    from app.engines.tenant_engine import health
    from app.engines.vertical_monetization import runtime_operations

    now = datetime.now(timezone.utc)
    old_tenant = uuid.uuid4()
    job = NS(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), tenant_id=old_tenant,
        status="accepted", assignment_status="unassigned", assigned_staff_id=None,
        provider_offer_started_at=now - timedelta(minutes=16), updated_at=now - timedelta(minutes=1),
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
    monkeypatch.setattr(health, "refresh_provider_operational_health", AsyncMock())
    return NS(db=db, job=job, booking=booking, old_tenant=old_tenant)


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
    assert "provider_offer_started_at <=" in sql
    assert "updated_at <=" not in sql


@pytest.mark.asyncio
async def test_timeout_closes_when_no_other_provider_can_take_the_job(offer, monkeypatch):
    monkeypatch.setattr(timeout, "_find_replacement", AsyncMock(return_value=None))

    result = await timeout.sweep(offer.db)

    assert result["reassigned"] == 0 and result["closed"] == 1
    assert offer.job.status == "cancelled" and offer.booking.status == "cancelled"
    assert "no alternative provider" in offer.job.failure_reason
    assert offer.booking.failure_reason == offer.job.failure_reason
