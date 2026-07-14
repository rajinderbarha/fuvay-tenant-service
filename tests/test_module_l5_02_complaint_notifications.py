"""MODULE-L5-02 bug #40 — the complaints engine notified nobody."""
import inspect
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_notify_helper_targets_super_admins_and_links_to_the_complaint():
    from app.engines.complaints import notifications
    src = inspect.getsource(notifications.notify_admins_complaint)
    assert "InAppNotification" in src
    assert "/admin/complaints/" in src            # deep-links to the case
    src2 = inspect.getsource(notifications._super_admin_ids)
    assert 'role == "super_admin"' in src2


@pytest.mark.asyncio
async def test_notify_creates_one_notification_per_admin():
    from app.engines.complaints import notifications
    db = MagicMock()
    db.add = MagicMock()
    complaint = MagicMock(id=uuid.uuid4(), complaint_number="CMP-1")
    with patch.object(notifications, "_super_admin_ids",
                      AsyncMock(return_value=[uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])):
        n = await notifications.notify_admins_complaint(
            db, complaint, notification_type="complaint.test",
            title="t", body="b", severity="warning")
    assert n == 3
    assert db.add.call_count == 3


def test_ai_escalation_notifies_admins():
    """When the AI refuses to settle (over cap / money / unpermitted) and hands
    the case to a human, the admins must be told — proven live for the SLA path;
    this asserts the AI path fires it too."""
    from app.engines.complaints import ai_settlement_service
    src = inspect.getsource(ai_settlement_service.AISettlementService.analyze_and_propose)
    esc = src.split("if not verdict.allowed")[1].split("return None")[0]
    assert "notify_admins_complaint" in esc
    assert "ai_settlement.escalated" in esc


def test_sla_escalation_notifies_admins():
    from app.jobs import complaint_sla
    src = inspect.getsource(complaint_sla.run_escalations)
    assert "notify_admins_complaint" in src
    assert "complaint.sla.escalated" in src
