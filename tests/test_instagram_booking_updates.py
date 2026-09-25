"""A cancelled provider offer must notify only its booking's Instagram sender."""
import uuid
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.messaging_gateway import booking_updates


@pytest.mark.asyncio
async def test_final_assignment_failure_uses_captured_sender(monkeypatch):
    import app.database

    customer_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    job = NS(
        id=uuid.uuid4(), booking_id=booking_id, tenant_id=uuid.uuid4(),
        status="cancelled",
        failure_reason="Closed because no alternative provider was available after 15 minutes.",
    )
    booking = NS(
        id=booking_id, customer_id=customer_id, booking_number="BK-15",
        source_channel="instagram", source_actor_id="igsid-booker",
    )
    thread = NS(
        id=uuid.uuid4(), customer_id=customer_id, channel_user_id="igsid-booker",
        blocked_until=None, last_outbound_at=None,
    )
    db = AsyncMock()
    db.scalar.side_effect = [True, None]  # advisory lock, no sent marker
    db.get.side_effect = [job, booking]
    result = MagicMock()
    result.scalars.return_value.first.return_value = thread
    db.execute.return_value = result
    db.add = MagicMock()
    context = AsyncMock()
    context.__aenter__.return_value = db
    monkeypatch.setattr(app.database, "get_session_factory", lambda: lambda: context)
    monkeypatch.setattr(
        booking_updates.messaging_channel_config_service, "get",
        AsyncMock(return_value={"access_token": "test"}),
    )
    send = AsyncMock(return_value={"sent": True})
    monkeypatch.setattr(booking_updates.meta_client, "send_text", send)

    assert await booking_updates.send_assignment_cancelled(job.id) is True
    assert send.call_args.args[0] == "igsid-booker"
    assert "BK-15" in send.call_args.args[1]
    assert "no other available provider" in send.call_args.args[1]
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unrelated_cancellation_never_sends_timeout_reason(monkeypatch):
    import app.database

    db = AsyncMock()
    db.scalar.return_value = True
    db.get.return_value = NS(status="cancelled", failure_reason="Customer cancelled")
    context = AsyncMock()
    context.__aenter__.return_value = db
    monkeypatch.setattr(app.database, "get_session_factory", lambda: lambda: context)
    send = AsyncMock()
    monkeypatch.setattr(booking_updates.meta_client, "send_text", send)

    assert await booking_updates.send_assignment_cancelled(uuid.uuid4()) is False
    send.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_cancellation_is_delivered_once_after_commit(monkeypatch):
    import app.database

    job_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    job = NS(
        id=job_id, booking_id=booking_id, tenant_id=uuid.uuid4(),
        assigned_staff_id=None, status="cancelled",
        failure_reason="No technician available",
    )
    booking = NS(
        id=booking_id, booking_number="BK-200", source_channel="instagram",
        source_actor_id="igsid-booker",
    )
    cancellation = NS(notes="No technician available")
    db = AsyncMock()
    db.scalar.side_effect = [True, None, cancellation]
    db.get.side_effect = [job, booking]
    db.add = MagicMock()
    context = AsyncMock()
    context.__aenter__.return_value = db
    monkeypatch.setattr(app.database, "get_session_factory", lambda: lambda: context)
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(booking_updates, "send_provider_cancelled", send)

    assert await booking_updates.send_provider_cancelled_once(job_id) is True
    send.assert_awaited_once_with(db, job, "No technician available")
    marker = db.add.call_args.args[0]
    assert marker.event_type == booking_updates.PROVIDER_CANCELLED_EVENT_TYPE
    assert marker.job_id == job_id
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_provider_cancellation_delivery_marker_prevents_duplicate(monkeypatch):
    import app.database

    job_id = uuid.uuid4()
    job = NS(id=job_id, status="cancelled")
    db = AsyncMock()
    db.scalar.side_effect = [True, uuid.uuid4()]
    db.get.return_value = job
    context = AsyncMock()
    context.__aenter__.return_value = db
    monkeypatch.setattr(app.database, "get_session_factory", lambda: lambda: context)
    send = AsyncMock()
    monkeypatch.setattr(booking_updates, "send_provider_cancelled", send)

    assert await booking_updates.send_provider_cancelled_once(job_id) is True
    send.assert_not_awaited()
    db.commit.assert_not_awaited()


def test_provider_cancellation_recovery_worker_is_registered():
    from pathlib import Path

    main = Path("app/main.py").read_text(encoding="utf-8")
    assert "instagram_cancellation_followups_loop" in main
    assert '("instagram_cancellation_followups", instagram_cancellation_followups_loop)' in main
