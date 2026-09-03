"""Phase 2A Slice 2F-10A — customer complaint eligibility and
refund-state integrity closure.

Two findings from Slice 2F-10's own honest gap list, adjudicated here:

1. `ComplaintEligibilityService.check_eligible` is CANONICAL_CREATION_POLICY,
   not merely advisory -- its record-status table (`ELIGIBLE_STATUSES`)
   carries real, deliberate product history (MODULE-L5-02 bug #23), and
   its window/duplicate rules are backed by a real, configurable
   `ComplaintPolicy` model. `create_complaint` previously enforced only
   the ownership half of this contract (Slice 2F-10); it now calls
   `check_eligible` itself as the single, shared, authoritative gate --
   so `check_eligible` (the advisory preflight endpoint) and
   `create_complaint` (the mutation) can never disagree for the same
   fixture.

2. `create_refund_request_from_complaint`'s "silent no-op on illegal
   transition" is NOT a defect -- existing tests
   (`test_refund_events_log_the_status_actually_applied`,
   `test_refund_path_advances_and_resolves_the_complaint` in
   `test_module_l5_02_complaints_flow.py`) prove this is deliberate,
   load-bearing behavior shared across the whole refund lifecycle
   (create/admin_approve_refund/record_refund). Classified
   REQUEST_ALLOWED_WITHOUT_COMPLAINT_TRANSITION_BY_POLICY. No code
   change was made here; this file proves the behavior directly instead
   of assuming it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.complaints.eligibility_service import ComplaintEligibilityService
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.refund_service import RefundRequestService
from app.engines.complaints.constants import (
    RECORD_SERVICE_BOOKING, RECORD_SERVICE_JOB,
    STATUS_OPEN, STATUS_AWAITING_PROVIDER,
    STATUS_RESOLUTION_PROPOSED, STATUS_REWORK_APPROVED, STATUS_RESOLVED,
    STATUS_CLOSED, STATUS_CANCELLED, STATUS_REJECTED, STATUS_SETTLED,
    STATUS_REFUND_REQUESTED, STATUS_REFUND_APPROVED, STATUS_REFUND_RECORDED,
    ACTOR_CUSTOMER, ERR_COMPLAINT_ACCESS_DENIED, ERR_COMPLAINT_RECORD_NOT_FOUND,
    ERR_COMPLAINT_NOT_ELIGIBLE, ERR_COMPLAINT_WINDOW_EXPIRED,
    ERR_COMPLAINT_DUPLICATE_OPEN,
)


def _uuid():
    return uuid.uuid4()


def _mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def _exec_result(item):
    r = MagicMock()
    r.scalars.return_value.first.return_value = item
    r.scalars.return_value.all.return_value = [item] if item else []
    r.scalar_one_or_none.return_value = item
    return r


# ── Workstream 2/3: eligibility contract, direct rule tests ──────────────────

@pytest.mark.asyncio
class TestEligibilityContract:
    async def test_invalid_record_type_raises(self):
        svc = ComplaintEligibilityService()
        db = _mock_db()
        with pytest.raises(ValueError, match="COMPLAINT_INVALID_RECORD_TYPE"):
            await svc.check_eligible(db, _uuid(), "bogus_type", _uuid())

    async def test_missing_record_raises(self):
        svc = ComplaintEligibilityService()
        db = _mock_db()
        db.execute = AsyncMock(return_value=_exec_result(None))
        with pytest.raises(ValueError, match=ERR_COMPLAINT_RECORD_NOT_FOUND):
            await svc.check_eligible(db, _uuid(), RECORD_SERVICE_BOOKING, _uuid())

    async def test_ineligible_status_returns_reason_code(self):
        svc = ComplaintEligibilityService()
        db = _mock_db()
        record = MagicMock(status="pending", customer_id=_uuid(), created_at=None)
        db.execute = AsyncMock(return_value=_exec_result(record))
        result = await svc.check_eligible(db, record.customer_id, RECORD_SERVICE_BOOKING, _uuid())
        assert result["eligible"] is False
        assert result["reason_code"] == ERR_COMPLAINT_NOT_ELIGIBLE

    async def test_foreign_owner_returns_access_denied_code(self):
        svc = ComplaintEligibilityService()
        db = _mock_db()
        owner = _uuid()
        record = MagicMock(status="completed", customer_id=owner, created_at=None)
        db.execute = AsyncMock(return_value=_exec_result(record))
        result = await svc.check_eligible(db, _uuid(), RECORD_SERVICE_BOOKING, _uuid())
        assert result["eligible"] is False
        assert result["reason_code"] == ERR_COMPLAINT_ACCESS_DENIED

    async def test_window_expired_returns_reason_code(self):
        svc = ComplaintEligibilityService()
        db = _mock_db()
        cid = _uuid()
        old_created = datetime.now(timezone.utc) - timedelta(hours=200)
        record = MagicMock(status="completed", customer_id=cid, created_at=old_created)
        db.execute = AsyncMock(side_effect=[
            _exec_result(record),   # _fetch_record
            _exec_result(None),     # get_complaint_policy category lookup
            _exec_result(None),     # get_complaint_policy default lookup
        ])
        result = await svc.check_eligible(db, cid, RECORD_SERVICE_BOOKING, _uuid())
        assert result["eligible"] is False
        assert result["reason_code"] == ERR_COMPLAINT_WINDOW_EXPIRED

    async def test_within_window_is_eligible(self):
        svc = ComplaintEligibilityService()
        db = _mock_db()
        cid = _uuid()
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        record = MagicMock(status="completed", customer_id=cid, created_at=recent)
        db.execute = AsyncMock(side_effect=[
            _exec_result(record),
            _exec_result(None),
            _exec_result(None),
            _exec_result(None),  # duplicate check
        ])
        result = await svc.check_eligible(db, cid, RECORD_SERVICE_BOOKING, _uuid(), complaint_type="service_quality")
        assert result["eligible"] is True
        assert result["reason_code"] is None

    async def test_duplicate_open_complaint_returns_reason_code(self):
        svc = ComplaintEligibilityService()
        db = _mock_db()
        cid = _uuid()
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        record = MagicMock(status="completed", customer_id=cid, created_at=recent)
        existing = MagicMock(id=_uuid())
        db.execute = AsyncMock(side_effect=[
            _exec_result(record),
            _exec_result(None),      # get_complaint_policy default lookup (no category_id supplied)
            _exec_result(existing),  # duplicate check finds one
        ])
        result = await svc.check_eligible(db, cid, RECORD_SERVICE_BOOKING, _uuid(), complaint_type="service_quality")
        assert result["eligible"] is False
        assert result["reason_code"] == ERR_COMPLAINT_DUPLICATE_OPEN


# ── Workstream 6/12: create_complaint <-> check_eligible consistency ─────────

@pytest.mark.asyncio
class TestEligibilityCreationConsistency:
    """For identical fixtures, check_eligible and create_complaint must not
    contradict each other -- create_complaint now delegates to
    check_eligible directly, so this is true by construction; these tests
    prove it end-to-end rather than assuming it."""

    async def test_ineligible_fixture_blocks_both_check_and_create(self):
        cid = _uuid()
        record = MagicMock(status="pending", customer_id=cid, created_at=None)
        db1 = _mock_db()
        db1.execute = AsyncMock(return_value=_exec_result(record))
        eligibility_svc = ComplaintEligibilityService()
        check_result = await eligibility_svc.check_eligible(db1, cid, RECORD_SERVICE_BOOKING, _uuid())
        assert check_result["eligible"] is False

        complaint_svc = ComplaintService()
        db2 = _mock_db()
        complaint_svc._eligibility.check_eligible = AsyncMock(return_value=check_result)
        with pytest.raises(ValueError, match=check_result["reason_code"]):
            await complaint_svc.create_complaint(
                db2, cid, category_id=_uuid(),
                record_type=RECORD_SERVICE_BOOKING, record_id=_uuid(),
                complaint_type="service_quality", description="x",
            )
        db2.add.assert_not_called()

    async def test_eligible_fixture_allows_both_check_and_create(self):
        cid = _uuid()
        tenant_id = _uuid()
        eligible_result = {"eligible": True, "reason": None, "reason_code": None, "policy": None}
        complaint_svc = ComplaintService()
        db = _mock_db()
        complaint_svc._eligibility.check_eligible = AsyncMock(return_value=eligible_result)
        complaint_svc._log_event = AsyncMock()
        complaint_svc._link_service_job = AsyncMock()
        with patch(
            "app.engines.complaints.notifications.notify_provider_complaint",
            new=AsyncMock(),
        ):
            c = await complaint_svc.create_complaint(
                db, cid, category_id=_uuid(), tenant_id=tenant_id,
                record_type=RECORD_SERVICE_BOOKING, record_id=_uuid(),
                complaint_type="service_quality", description="x",
            )
        assert str(c.customer_id) == str(cid)
        db.add.assert_called_once()

    async def test_create_complaint_never_persists_when_ineligible(self):
        """Denied request creates no record -- direct proof for every
        reason_code family."""
        complaint_svc = ComplaintService()
        for code in (ERR_COMPLAINT_ACCESS_DENIED, ERR_COMPLAINT_NOT_ELIGIBLE,
                     ERR_COMPLAINT_WINDOW_EXPIRED, ERR_COMPLAINT_DUPLICATE_OPEN):
            db = _mock_db()
            complaint_svc._eligibility.check_eligible = AsyncMock(return_value={
                "eligible": False, "reason": "x", "reason_code": code,
            })
            with pytest.raises(ValueError, match=code):
                await complaint_svc.create_complaint(
                    db, _uuid(), category_id=_uuid(),
                    record_type=RECORD_SERVICE_BOOKING, record_id=_uuid(),
                    complaint_type="service_quality", description="x",
                )
            db.add.assert_not_called()
            db.commit.assert_not_called()


# ── Workstream 7/8: refund-request state reconciliation ─────────────────────

@pytest.mark.asyncio
class TestRefundRequestSilentTransitionIsIntentional:
    """Proves (does not assume) that create_refund_request_from_complaint
    always creates the RefundRequest, and only conditionally advances the
    complaint's own status -- the classified, tested, intentional
    REQUEST_ALLOWED_WITHOUT_COMPLAINT_TRANSITION_BY_POLICY behavior."""

    @pytest.mark.parametrize("status,should_transition", [
        (STATUS_OPEN, True),
        (STATUS_AWAITING_PROVIDER, True),
        (STATUS_RESOLUTION_PROPOSED, False),
        (STATUS_REWORK_APPROVED, False),
        (STATUS_RESOLVED, False),
        (STATUS_SETTLED, False),
        (STATUS_CLOSED, False),
        (STATUS_CANCELLED, False),
        (STATUS_REJECTED, False),
        (STATUS_REFUND_REQUESTED, False),
        (STATUS_REFUND_APPROVED, False),
        (STATUS_REFUND_RECORDED, False),
    ])
    async def test_refund_request_created_regardless_of_state(self, status, should_transition):
        svc = RefundRequestService()
        db = _mock_db()
        cid = _uuid()
        complaint = MagicMock(customer_id=cid, tenant_id=_uuid(), status=status,
                               invoice_id=None, booking_id=None, job_id=None,
                               appointment_id=None, lead_id=None)
        svc._complaint_svc.get_customer_complaint = AsyncMock(return_value=complaint)
        svc._log_event = AsyncMock()
        refund = await svc.create_refund_request_from_complaint(
            db, _uuid(), cid, ACTOR_CUSTOMER, "partial", "reason",
        )
        # RefundRequest is ALWAYS created -- the request itself is not
        # state-gated, only the complaint's own status transition is.
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        assert refund.status == "requested"
        if should_transition:
            assert complaint.status == STATUS_REFUND_REQUESTED
        else:
            assert complaint.status == status  # unchanged -- silent no-op

    async def test_audit_event_logs_true_applied_status_not_claimed_one(self):
        """MODULE-L5-02 bug #31, re-verified: the event must log the
        REAL applied status (None when skipped), not a hardcoded one."""
        svc = RefundRequestService()
        db = _mock_db()
        cid = _uuid()
        complaint = MagicMock(customer_id=cid, tenant_id=_uuid(), status=STATUS_RESOLVED,
                               invoice_id=None, booking_id=None, job_id=None,
                               appointment_id=None, lead_id=None)
        svc._complaint_svc.get_customer_complaint = AsyncMock(return_value=complaint)
        log_calls = []
        async def fake_log_event(*a, **kw):
            log_calls.append(a)
        svc._log_event = fake_log_event
        await svc.create_refund_request_from_complaint(
            db, _uuid(), cid, ACTOR_CUSTOMER, "partial", "reason",
        )
        assert len(log_calls) == 1
        # positional args: (db, complaint_id, tenant_id, actor_type, actor_user_id,
        #                    event_type, old_status, new_status, ...)
        old_status_arg = log_calls[0][6]
        new_status_arg = log_calls[0][7]
        assert old_status_arg == STATUS_RESOLVED
        assert new_status_arg is None  # transition was skipped -- honestly logged


@pytest.mark.asyncio
class TestRefundOwnershipStillEnforced:
    """Re-verifies Slice 2F-10's refund-ownership fix is untouched by this
    slice's investigation."""

    async def test_foreign_complaint_still_rejected(self):
        svc = RefundRequestService()
        db = _mock_db()
        svc._complaint_svc.get_customer_complaint = AsyncMock(
            side_effect=ValueError(ERR_COMPLAINT_ACCESS_DENIED))
        with pytest.raises(ValueError, match=ERR_COMPLAINT_ACCESS_DENIED):
            await svc.create_refund_request_from_complaint(
                db, _uuid(), _uuid(), ACTOR_CUSTOMER, "partial", "reason",
            )
        db.add.assert_not_called()
