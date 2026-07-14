"""MODULE-L5-02 bug #42 — the customer & provider were never notified.

The dual-acceptance flow needs each party to act in turn, but only ADMINS were
notified (bug #40). The customer was never told a resolution/settlement awaited
their accept/reject, and the provider was never told a complaint had been filed
against their job — so the flow silently waited on someone with no idea it was
their move.
"""
import inspect
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_helpers_target_the_right_recipient():
    from app.engines.complaints import notifications
    cust = inspect.getsource(notifications.notify_customer_complaint)
    assert "complaint.customer_id" in cust and "/customer/complaints/" in cust
    prov = inspect.getsource(notifications.notify_provider_complaint)
    assert "_tenant_owner_ids" in prov and "/provider/complaints/" in prov
    owners = inspect.getsource(notifications._tenant_owner_ids)
    assert 'role == "tenant_owner"' in owners


@pytest.mark.asyncio
async def test_provider_notify_is_one_per_owner():
    from app.engines.complaints import notifications
    db = MagicMock(); db.add = MagicMock()
    complaint = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), complaint_number="CMP-1")
    with patch.object(notifications, "_tenant_owner_ids",
                      AsyncMock(return_value=[uuid.uuid4(), uuid.uuid4()])):
        n = await notifications.notify_provider_complaint(
            db, complaint, notification_type="complaint.filed", title="t", body="b")
    assert n == 2 and db.add.call_count == 2


def test_hand_off_points_are_wired():
    from app.engines.complaints.complaint_service import ComplaintService
    from app.engines.complaints import ai_settlement_service
    # customer files -> provider told
    assert "notify_provider_complaint" in inspect.getsource(ComplaintService.create_complaint)
    # provider offers a resolution -> customer told
    assert "notify_customer_complaint" in inspect.getsource(ComplaintService.provider_offer_resolution)
    # a settlement proposal -> the counterparty told
    prop = inspect.getsource(ComplaintService.create_settlement_proposal)
    assert "notify_customer_complaint" in prop and "notify_provider_complaint" in prop
    # AI proposal -> both told
    ai = inspect.getsource(ai_settlement_service.AISettlementService.analyze_and_propose)
    assert "notify_customer_complaint" in ai and "notify_provider_complaint" in ai
    # credits actually issued -> customer told
    assert "complaint.settlement_paid" in inspect.getsource(ComplaintService._execute_settlement_payout)
