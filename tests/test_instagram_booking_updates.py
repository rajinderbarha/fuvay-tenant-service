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
