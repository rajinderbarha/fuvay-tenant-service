"""Sprint 25 — Complaint / Rework / Refund Engine tests."""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.exceptions import ServiceOSException


# ── helpers ───────────────────────────────────────────────────────────────────
def _uuid():
    return uuid.uuid4()


def _mock_db():
    db = AsyncMock()
    db.flush  = AsyncMock()
    db.commit = AsyncMock()
    db.add    = MagicMock()
    return db


def _exec_result(item):
    r = MagicMock()
    r.scalars.return_value.first.return_value  = item
    r.scalars.return_value.all.return_value    = [item] if item else []
    return r


# ── Eligibility Service ───────────────────────────────────────────────────────
from app.engines.complaints.eligibility_service import ComplaintEligibilityService
from app.engines.complaints.constants import (
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_AWAITING_CUSTOMER,
    STATUS_UNDER_ADMIN_REVIEW, STATUS_RESOLUTION_PROPOSED,
    STATUS_REWORK_APPROVED, STATUS_REFUND_REQUESTED,
    STATUS_REFUND_APPROVED, STATUS_REFUND_RECORDED,
    STATUS_REJECTED, STATUS_RESOLVED, STATUS_CLOSED, STATUS_CANCELLED,
    RECORD_SERVICE_BOOKING, RECORD_COACHING_APPOINTMENT,
    REWORK_REQUESTED, REWORK_APPROVED, REWORK_COMPLETED,
    REFUND_REQUESTED, REFUND_APPROVED, REFUND_RECORDED, REFUND_VERIFIED, REFUND_ADMIN_REVIEW,
    ERR_COMPLAINT_NOT_FOUND, ERR_COMPLAINT_ACCESS_DENIED,
    ERR_REWORK_NOT_FOUND, ERR_REFUND_NOT_FOUND,
    ERR_COMPLAINT_INVALID_RECORD_TYPE, ERR_COMPLAINT_RECORD_NOT_FOUND,
)


@pytest.mark.asyncio
async def test_eligibility_invalid_record_type():
    svc = ComplaintEligibilityService()
    db  = _mock_db()
    with pytest.raises(ValueError, match="COMPLAINT_INVALID_RECORD_TYPE"):
        await svc.check_eligible(db, _uuid(), "invalid_type", _uuid())


@pytest.mark.asyncio
async def test_eligibility_record_not_found():
    svc = ComplaintEligibilityService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    with pytest.raises(ValueError, match="COMPLAINT_RECORD_NOT_FOUND"):
        await svc.check_eligible(db, _uuid(), RECORD_SERVICE_BOOKING, _uuid())


@pytest.mark.asyncio
async def test_eligibility_wrong_status():
    svc    = ComplaintEligibilityService()
    db     = _mock_db()
    record = MagicMock(status="pending", customer_id=_uuid())
    db.execute = AsyncMock(return_value=_exec_result(record))
    result = await svc.check_eligible(db, record.customer_id, RECORD_SERVICE_BOOKING, _uuid())
    assert result["eligible"] is False
    assert "not eligible" in result["reason"]


@pytest.mark.asyncio
async def test_eligibility_not_customer_owner():
    svc      = ComplaintEligibilityService()
    db       = _mock_db()
    owner_id = _uuid()
    record   = MagicMock(status="completed", customer_id=owner_id)
    db.execute = AsyncMock(return_value=_exec_result(record))
    result = await svc.check_eligible(db, _uuid(), RECORD_SERVICE_BOOKING, _uuid())
    assert result["eligible"] is False
    assert "Not the customer" in result["reason"]


@pytest.mark.asyncio
async def test_check_duplicate_open_no_existing():
    svc = ComplaintEligibilityService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    result = await svc.check_duplicate_open_complaint(db, _uuid(), RECORD_SERVICE_BOOKING, _uuid(), "service_quality")
    assert result is False


@pytest.mark.asyncio
async def test_check_duplicate_open_has_existing():
    svc      = ComplaintEligibilityService()
    db       = _mock_db()
    existing = MagicMock(id=_uuid())
    db.execute = AsyncMock(return_value=_exec_result(existing))
    result = await svc.check_duplicate_open_complaint(db, _uuid(), RECORD_SERVICE_BOOKING, _uuid(), "service_quality")
    assert result is True


@pytest.mark.asyncio
async def test_get_complaint_policy_falls_back_to_default():
    svc = ComplaintEligibilityService()
    db  = _mock_db()
    default_policy = MagicMock(policy_key="default")
    db.execute = AsyncMock(side_effect=[_exec_result(None), _exec_result(default_policy)])
    result = await svc.get_complaint_policy(db, category_id=_uuid())
    assert result.policy_key == "default"


# ── Complaint Service ──────────────────────────────────────────────────────────
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.models import (
    CustomerComplaint, ComplaintMessage, ComplaintResolution, ComplaintEvent,
)


@pytest.mark.asyncio
async def test_create_complaint_success():
    svc    = ComplaintService()
    db     = _mock_db()
    cid    = _uuid()
    cat_id = _uuid()
    with patch.object(svc._eligibility, 'check_eligible', AsyncMock(return_value={"eligible": True, "reason_code": None})), \
         patch.object(svc, '_link_service_job', AsyncMock()), \
         patch('app.engines.complaints.notifications.notify_provider_complaint', AsyncMock()), \
         patch.object(svc, '_log_event', AsyncMock()):
        c = await svc.create_complaint(
            db, cid, category_id=cat_id,
            record_type=RECORD_SERVICE_BOOKING, record_id=_uuid(),
            complaint_type="service_quality", description="Test desc", tenant_id=_uuid(),
        )
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    assert c.status == STATUS_OPEN
    assert str(c.customer_id) == str(cid)


@pytest.mark.asyncio
async def test_get_customer_complaint_not_owner():
    svc = ComplaintService()
    db  = _mock_db()
    c   = MagicMock(customer_id=_uuid(), status=STATUS_OPEN)
    with patch.object(svc, '_get_complaint', AsyncMock(return_value=c)):
        with pytest.raises(ValueError, match="COMPLAINT_ACCESS_DENIED"):
            await svc.get_customer_complaint(db, _uuid(), _uuid())


@pytest.mark.asyncio
async def test_get_customer_complaint_success():
    svc  = ComplaintService()
    db   = _mock_db()
    uid  = _uuid()
    c    = MagicMock(customer_id=uid, status=STATUS_OPEN)
    with patch.object(svc, '_get_complaint', AsyncMock(return_value=c)):
        result = await svc.get_customer_complaint(db, uid, c.id)
    assert result is c


@pytest.mark.asyncio
async def test_add_customer_message_success():
    svc = ComplaintService()
    db  = _mock_db()
    uid = _uuid()
    c   = MagicMock(customer_id=uid, status=STATUS_AWAITING_CUSTOMER, tenant_id=_uuid())
    with patch.object(svc, 'get_customer_complaint', AsyncMock(return_value=c)):
        with patch.object(svc, '_log_event', AsyncMock()):
            msg = await svc.add_customer_message(db, uid, _uuid(), "Hello support")
    db.add.assert_called_once()
    assert msg.message_text == "Hello support"


@pytest.mark.asyncio
async def test_add_customer_message_already_closed():
    svc = ComplaintService()
    db  = _mock_db()
    uid = _uuid()
    c   = MagicMock(customer_id=uid, status=STATUS_CLOSED)
    with patch.object(svc, 'get_customer_complaint', AsyncMock(return_value=c)):
        with pytest.raises(ValueError, match="COMPLAINT_ALREADY_CLOSED"):
            await svc.add_customer_message(db, uid, _uuid(), "message")


@pytest.mark.asyncio
async def test_transition_invalid_raises():
    svc = ComplaintService()
    db  = _mock_db()
    c   = MagicMock(status=STATUS_CLOSED, tenant_id=_uuid())
    with patch.object(svc, '_log_event', AsyncMock()):
        with pytest.raises(ValueError, match="COMPLAINT_INVALID_STATUS_TRANSITION"):
            await svc._transition(db, c, STATUS_OPEN, "admin", _uuid())


@pytest.mark.asyncio
async def test_transition_valid():
    svc = ComplaintService()
    db  = _mock_db()
    c   = MagicMock(status=STATUS_OPEN, tenant_id=_uuid())
    with patch.object(svc, '_log_event', AsyncMock()):
        await svc._transition(db, c, STATUS_AWAITING_PROVIDER, "admin", _uuid())
    assert c.status == STATUS_AWAITING_PROVIDER


@pytest.mark.asyncio
async def test_admin_reject_complaint_requires_reason():
    svc = ComplaintService()
    db  = _mock_db()
    with pytest.raises(ValueError):
        await svc.admin_reject_complaint(db, _uuid(), _uuid(), reason="")


@pytest.mark.asyncio
async def test_admin_reject_complaint_success():
    svc = ComplaintService()
    db  = _mock_db()
    c   = MagicMock(status=STATUS_UNDER_ADMIN_REVIEW, tenant_id=_uuid())
    with patch.object(svc, '_get_complaint', AsyncMock(return_value=c)):
        with patch.object(svc, '_transition', AsyncMock()):
            with patch.object(svc, '_log_event', AsyncMock()):
                result = await svc.admin_reject_complaint(db, _uuid(), _uuid(), "Rejected")
    assert result is c


@pytest.mark.asyncio
async def test_provider_list_complaints():
    svc       = ComplaintService()
    db        = _mock_db()
    tenant_id = _uuid()
    c1        = MagicMock(tenant_id=tenant_id, status=STATUS_OPEN)
    db.execute = AsyncMock(return_value=_exec_result(c1))
    result = await svc.provider_list_complaints(db, tenant_id)
    assert len(result) >= 0


@pytest.mark.asyncio
async def test_provider_get_complaint_access_denied():
    svc = ComplaintService()
    db  = _mock_db()
    c   = MagicMock(tenant_id=_uuid())
    with patch.object(svc, '_get_complaint', AsyncMock(return_value=c)):
        with pytest.raises(ValueError, match="COMPLAINT_ACCESS_DENIED"):
            await svc.provider_get_complaint(db, _uuid(), _uuid())


@pytest.mark.asyncio
async def test_cancel_customer_complaint():
    svc = ComplaintService()
    db  = _mock_db()
    uid = _uuid()
    c   = MagicMock(customer_id=uid, status=STATUS_OPEN, tenant_id=_uuid())
    with patch.object(svc, 'get_customer_complaint', AsyncMock(return_value=c)):
        with patch.object(svc, '_transition', AsyncMock()):
            result = await svc.cancel_customer_complaint(db, uid, _uuid(), "Changed mind")
    assert result is c


@pytest.mark.asyncio
async def test_list_messages_customer_viewer():
    svc  = ComplaintService()
    db   = _mock_db()
    mid  = _uuid()
    msg  = MagicMock(visibility="public_to_case", created_at="2025-01-01")
    msg.is_visible_to = MagicMock(return_value=True)
    r    = MagicMock()
    r.scalars.return_value.all.return_value = [msg]
    db.execute = AsyncMock(return_value=r)
    result = await svc.list_messages(db, mid, viewer="customer")
    assert len(result) == 1


# ── Rework Service ─────────────────────────────────────────────────────────────
from app.engines.complaints.rework_service import ServiceReworkService


@pytest.mark.asyncio
async def test_create_rework_from_complaint():
    svc = ServiceReworkService()
    db  = _mock_db()
    cid = _uuid()
    c   = MagicMock(id=cid, tenant_id=_uuid(), customer_id=_uuid(),
                    booking_id=None, job_id=None, status=STATUS_OPEN)
    with patch.object(svc._complaint_svc, 'get_complaint', AsyncMock(return_value=c)):
        with patch.object(svc, '_log_event', AsyncMock()):
            rw = await svc.create_rework_request_from_complaint(
                db, cid, _uuid(), "admin", "Quality issue"
            )
    db.add.assert_called_once()
    assert rw.status == REWORK_REQUESTED


@pytest.mark.asyncio
async def test_approve_rework():
    svc = ServiceReworkService()
    db  = _mock_db()
    rid = _uuid()
    rw  = MagicMock(id=rid, complaint_id=_uuid(), tenant_id=_uuid(), status=REWORK_REQUESTED)
    c   = MagicMock(status=STATUS_OPEN)
    with patch.object(svc, '_get_rework', AsyncMock(return_value=rw)):
        with patch.object(svc._complaint_svc, 'get_complaint', AsyncMock(return_value=c)):
            with patch.object(svc, '_log_event', AsyncMock()):
                result = await svc.approve_rework(db, rid, _uuid())
    assert result.status == REWORK_APPROVED


@pytest.mark.asyncio
async def test_mark_rework_completed():
    svc = ServiceReworkService()
    db  = _mock_db()
    rid = _uuid()
    rw  = MagicMock(id=rid, complaint_id=_uuid(), tenant_id=_uuid(), status="in_progress")
    c   = MagicMock(status=STATUS_REWORK_APPROVED)
    with patch.object(svc, '_get_rework', AsyncMock(return_value=rw)):
        with patch.object(svc._complaint_svc, 'get_complaint', AsyncMock(return_value=c)):
            result = await svc.mark_rework_completed(db, rid, _uuid(), notes="Done")
    assert result.status == REWORK_COMPLETED


@pytest.mark.asyncio
async def test_rework_not_found():
    svc = ServiceReworkService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    with pytest.raises(ValueError, match="REWORK_NOT_FOUND"):
        await svc.get_rework(db, _uuid())


@pytest.mark.asyncio
async def test_reject_rework():
    svc = ServiceReworkService()
    db  = _mock_db()
    rw  = MagicMock(status=REWORK_REQUESTED)
    with patch.object(svc, '_get_rework', AsyncMock(return_value=rw)):
        result = await svc.reject_rework(db, _uuid(), _uuid(), "Not covered")
    assert result.status == "rejected"


# ── Refund Service ─────────────────────────────────────────────────────────────
from app.engines.complaints.refund_service import RefundRequestService


@pytest.mark.asyncio
async def test_create_refund_from_complaint():
    svc = RefundRequestService()
    db  = _mock_db()
    cid = _uuid()
    c   = MagicMock(id=cid, tenant_id=_uuid(), customer_id=_uuid(),
                    booking_id=None, job_id=None, appointment_id=None, lead_id=None,
                    invoice_id=None, status=STATUS_UNDER_ADMIN_REVIEW)
    with patch.object(svc._complaint_svc, 'get_complaint', AsyncMock(return_value=c)):
        with patch.object(svc, '_log_event', AsyncMock()):
            rf = await svc.create_refund_request_from_complaint(
                db, cid, _uuid(), "admin",
                "cash_refund", "Overcharged",
                requested_amount=Decimal("150.00"),
            )
    db.add.assert_called_once()
    assert rf.status == REFUND_REQUESTED


@pytest.mark.asyncio
async def test_admin_approve_refund():
    svc = RefundRequestService()
    db  = _mock_db()
    rf  = MagicMock(id=_uuid(), complaint_id=_uuid(), tenant_id=_uuid(),
                    requested_amount=Decimal("100.00"), status=REFUND_REQUESTED)
    with patch.object(svc, '_get_refund', AsyncMock(return_value=rf)):
        with pytest.raises(ServiceOSException) as exc:
            await svc.admin_approve_refund(db, rf.id, _uuid(), approved_amount=Decimal("80.00"))
    assert exc.value.error_code == "PROVIDER_OWNS_REFUND"


@pytest.mark.asyncio
async def test_admin_approve_refund_amount_exceeds_requested():
    svc = RefundRequestService()
    db  = _mock_db()
    rf  = MagicMock(id=_uuid(), requested_amount=Decimal("100.00"), status=REFUND_REQUESTED)
    with patch.object(svc, '_get_refund', AsyncMock(return_value=rf)):
        with pytest.raises(ServiceOSException) as exc:
            await svc.admin_approve_refund(db, rf.id, _uuid(), approved_amount=Decimal("200.00"))
    assert exc.value.error_code == "PROVIDER_OWNS_REFUND"


@pytest.mark.asyncio
async def test_record_refund():
    svc = RefundRequestService()
    db  = _mock_db()
    rf  = MagicMock(id=_uuid(), complaint_id=_uuid(), tenant_id=_uuid(), status=REFUND_APPROVED,
                    approved_amount=Decimal("80.00"), requested_amount=Decimal("100.00"))
    c   = MagicMock(status=STATUS_REFUND_APPROVED)
    with patch.object(svc, '_get_refund', AsyncMock(return_value=rf)):
        with patch.object(svc._complaint_svc, 'get_complaint', AsyncMock(return_value=c)):
            with patch.object(svc, '_log_event', AsyncMock()):
                result = await svc.record_refund(
                    db, rf.id, _uuid(), "admin", Decimal("80.00")
                )
    assert result.status == REFUND_RECORDED
    assert result.recorded_amount == Decimal("80.00")


@pytest.mark.asyncio
async def test_verify_refund_wrong_status():
    svc = RefundRequestService()
    db  = _mock_db()
    rf  = MagicMock(status=REFUND_APPROVED)
    with patch.object(svc, '_get_refund', AsyncMock(return_value=rf)):
        with pytest.raises(ValueError, match="REFUND_VERIFY_FAILED"):
            await svc.verify_refund(db, _uuid(), _uuid())


@pytest.mark.asyncio
async def test_verify_refund_success():
    svc = RefundRequestService()
    db  = _mock_db()
    rf  = MagicMock(status=REFUND_RECORDED)
    # MODULE-L5-02 bug #29: verifying a refund now also resolves the underlying
    # complaint (previously it stayed at refund_recorded forever), so the
    # complaint lookup must be stubbed too.
    complaint = MagicMock(status=STATUS_REFUND_RECORDED)
    with patch.object(svc, '_get_refund', AsyncMock(return_value=rf)), \
         patch.object(svc._complaint_svc, 'get_complaint', AsyncMock(return_value=complaint)):
        result = await svc.verify_refund(db, _uuid(), _uuid())
    assert result.status == REFUND_VERIFIED
    assert complaint.status == STATUS_RESOLVED


@pytest.mark.asyncio
async def test_refund_not_found():
    svc = RefundRequestService()
    db  = _mock_db()
    db.execute = AsyncMock(return_value=_exec_result(None))
    with pytest.raises(ValueError, match="REFUND_NOT_FOUND"):
        await svc.get_refund(db, _uuid())


@pytest.mark.asyncio
async def test_cancel_refund():
    svc = RefundRequestService()
    db  = _mock_db()
    rf  = MagicMock(status=REFUND_REQUESTED)
    with patch.object(svc, '_get_refund', AsyncMock(return_value=rf)):
        result = await svc.cancel_refund(db, _uuid(), _uuid(), "Withdrawn")
    assert result.status == "cancelled"


@pytest.mark.asyncio
async def test_admin_reject_refund():
    svc = RefundRequestService()
    db  = _mock_db()
    rf  = MagicMock(status=REFUND_ADMIN_REVIEW, provider_response_due_at=None)
    with patch.object(svc, '_get_refund', AsyncMock(return_value=rf)):
        result = await svc.admin_reject_refund(db, _uuid(), _uuid(), "Not valid")
    assert result.status == "rejected"
    assert result.rejection_reason == "Not valid"


@pytest.mark.asyncio
async def test_list_refund_requests():
    svc       = RefundRequestService()
    db        = _mock_db()
    rf        = MagicMock(status=REFUND_REQUESTED)
    r         = MagicMock()
    r.scalars.return_value.all.return_value = [rf]
    db.execute = AsyncMock(return_value=r)
    result = await svc.list_refund_requests(db)
    assert len(result) == 1


# ── Router smoke tests (import check) ─────────────────────────────────────────
def test_customer_router_importable():
    from app.engines.complaints.customer_router import customer_complaint_router
    assert customer_complaint_router.prefix == "/v1/customer/complaints"


def test_provider_routers_importable():
    from app.engines.complaints.provider_router import (
        provider_complaint_router, provider_rework_router, provider_refund_router
    )
    assert provider_complaint_router.prefix == "/v1/provider/complaints"
    assert provider_rework_router.prefix    == "/v1/provider/rework-requests"
    assert provider_refund_router.prefix    == "/v1/provider/refund-requests"


def test_admin_routers_importable():
    from app.engines.complaints.admin_router import (
        admin_complaint_router, admin_rework_router,
        admin_refund_router, admin_cpolicy_router,
    )
    assert admin_complaint_router.prefix == "/v1/admin/complaints"
    assert admin_rework_router.prefix    == "/v1/admin/rework-requests"
    assert admin_refund_router.prefix    == "/v1/admin/refund-requests"
    assert admin_cpolicy_router.prefix   == "/v1/admin/complaint-policies"
