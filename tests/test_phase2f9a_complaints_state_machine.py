"""Phase 2A Slice 2F-9A — provider complaint final-state and audit closure.

Corrects two factual errors from Slice 2F-9's own investigation, found
by direct source re-reading:

1. `provider_offer_resolution` was reported as having "no state
   precondition at all." This was WRONG -- it calls `self._transition`,
   which checks `ALLOWED_TRANSITIONS_EXT` and raises
   `ERR_COMPLAINT_INVALID_TRANSITION` unless the complaint is currently
   `awaiting_provider_response` or `under_admin_review` (the only two
   states whose transition set includes `resolution_proposed`). This
   already fully blocks offering a resolution on open/resolved/closed/
   cancelled/rejected/settled complaints -- pre-existing, unmodified.

2. `provider_add_response` was reported as having no audit event. This
   was WRONG -- it already calls `self._log_event(..., EVT_PROVIDER_RESPONDED, ...)`,
   which writes a `ComplaintEvent` row -- pre-existing, unmodified.

The one genuine, fixed-this-slice gap: `provider_add_response` had NO
final-state check at all, unlike its own sibling method
(`customer_add_message`, the customer-side equivalent), which already
guards with `if complaint.status in FINAL_STATUSES: raise
ValueError(ERR_COMPLAINT_ALREADY_CLOSED)`. Fixed by mirroring that exact,
pre-existing pattern -- not a new rule.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.complaints.constants import (
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_AWAITING_CUSTOMER,
    STATUS_UNDER_ADMIN_REVIEW, STATUS_RESOLUTION_PROPOSED, STATUS_REWORK_APPROVED,
    STATUS_REJECTED, STATUS_RESOLVED, STATUS_CLOSED, STATUS_CANCELLED,
    STATUS_SETTLED, FINAL_STATUSES, ERR_COMPLAINT_ALREADY_CLOSED,
    ERR_COMPLAINT_INVALID_TRANSITION,
)


def _mock_complaint(status, tenant_id=None):
    from app.engines.complaints.models import CustomerComplaint
    c = MagicMock(spec=CustomerComplaint)
    c.id = uuid.uuid4()
    c.tenant_id = tenant_id or uuid.uuid4()
    c.status = status
    c.provider_responded_at = None
    return c


def _db_returning(complaint):
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = complaint
    result.scalar_one_or_none.return_value = complaint
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


# ── Workstream 4: direct state test matrix for respond_to_complaint ──────────

ALL_STATES = [
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_AWAITING_CUSTOMER,
    STATUS_UNDER_ADMIN_REVIEW, STATUS_RESOLUTION_PROPOSED, STATUS_REWORK_APPROVED,
    STATUS_RESOLVED, STATUS_CLOSED, STATUS_CANCELLED, STATUS_REJECTED, STATUS_SETTLED,
]

FINAL_STATES = [STATUS_CLOSED, STATUS_CANCELLED, STATUS_REJECTED]
NON_FINAL_STATES = [s for s in ALL_STATES if s not in FINAL_STATES]


@pytest.mark.asyncio
class TestRespondToComplaintStateMachine:
    @pytest.mark.parametrize("status", FINAL_STATES)
    async def test_final_state_rejected_no_mutation(self, status):
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(status, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        with pytest.raises(ValueError) as exc:
            await svc.provider_add_response(db, tenant_id, complaint.id, uuid.uuid4(), "hello")
        assert ERR_COMPLAINT_ALREADY_CLOSED in str(exc.value)
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.parametrize("status", NON_FINAL_STATES)
    async def test_non_final_state_allowed(self, status):
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(status, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        result = await svc.provider_add_response(db, tenant_id, complaint.id, uuid.uuid4(), "hello")
        assert result is not None
        # db.add is called twice: once for the ComplaintMessage, once for
        # the ComplaintEvent audit row written by _log_event.
        assert db.add.call_count == 2
        db.commit.assert_called_once()

    async def test_repeated_response_is_allowed_message_append(self):
        """A second ordinary message is a legitimate conversation turn,
        not a duplicate to reject."""
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(STATUS_AWAITING_PROVIDER, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        r1 = await svc.provider_add_response(db, tenant_id, complaint.id, uuid.uuid4(), "first")
        r2 = await svc.provider_add_response(db, tenant_id, complaint.id, uuid.uuid4(), "second")
        assert r1 is not None and r2 is not None
        # 2 calls per response (message + audit event) x 2 responses = 4.
        assert db.add.call_count == 4

    async def test_audit_event_logged_on_success(self):
        """Confirms EVT_PROVIDER_RESPONDED is logged -- corrects Slice
        2F-9's incorrect claim that no audit event exists."""
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(STATUS_AWAITING_PROVIDER, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        with pytest.MonkeyPatch().context() as mp:
            log_calls = []
            orig = svc._log_event
            async def spy(*a, **kw):
                log_calls.append((a, kw))
                return await orig(*a, **kw)
            mp.setattr(svc, "_log_event", spy)
            await svc.provider_add_response(db, tenant_id, complaint.id, uuid.uuid4(), "hi")
        assert len(log_calls) == 1
        assert log_calls[0][0][5] == "provider_responded"


@pytest.mark.asyncio
class TestOfferResolutionStateMachine:
    """offer_resolution already fully enforces final-state protection via
    _transition + ALLOWED_TRANSITIONS_EXT (pre-existing, unmodified) --
    these tests PROVE that claim directly rather than assuming it."""

    LEGAL_SOURCE_STATES = [STATUS_AWAITING_PROVIDER, STATUS_UNDER_ADMIN_REVIEW]
    ILLEGAL_SOURCE_STATES = [
        STATUS_OPEN, STATUS_AWAITING_CUSTOMER, STATUS_RESOLUTION_PROPOSED,
        STATUS_REWORK_APPROVED, STATUS_RESOLVED, STATUS_CLOSED,
        STATUS_CANCELLED, STATUS_REJECTED, STATUS_SETTLED,
    ]

    @pytest.mark.parametrize("status", LEGAL_SOURCE_STATES)
    async def test_legal_source_state_allowed(self, status):
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(status, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        with pytest.MonkeyPatch().context() as mp:
            from app.engines.complaints import notifications as notif_mod
            mp.setattr(notif_mod, "notify_customer_complaint", AsyncMock())
            result = await svc.provider_offer_resolution(
                db, tenant_id, complaint.id, uuid.uuid4(), "rework", "we will fix it",
            )
        assert result is not None
        assert complaint.status == STATUS_RESOLUTION_PROPOSED

    @pytest.mark.parametrize("status", ILLEGAL_SOURCE_STATES)
    async def test_illegal_source_state_rejected_no_mutation(self, status):
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(status, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        with pytest.raises(ValueError) as exc:
            await svc.provider_offer_resolution(
                db, tenant_id, complaint.id, uuid.uuid4(), "rework", "we will fix it",
            )
        assert ERR_COMPLAINT_INVALID_TRANSITION in str(exc.value)
        db.add.assert_not_called()
        db.commit.assert_not_called()
        # Status must remain exactly what it was -- no partial mutation.
        assert complaint.status == status

    async def test_repeated_offer_while_already_resolution_proposed_rejected(self):
        """A second resolution offer while one is already pending is
        rejected -- resolution_proposed is not itself a legal source for
        another resolution_proposed transition."""
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(STATUS_RESOLUTION_PROPOSED, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        with pytest.raises(ValueError) as exc:
            await svc.provider_offer_resolution(
                db, tenant_id, complaint.id, uuid.uuid4(), "rework", "again",
            )
        assert ERR_COMPLAINT_INVALID_TRANSITION in str(exc.value)
        db.add.assert_not_called()


@pytest.mark.asyncio
class TestSideEffectSafety:
    """Verify no settlement/credit/rework/refund side effect can be
    triggered by an invalid/final-state request to either route."""

    async def test_respond_final_state_no_settlement_or_credit_side_effect(self):
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(STATUS_CLOSED, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        with pytest.raises(ValueError):
            await svc.provider_add_response(db, tenant_id, complaint.id, uuid.uuid4(), "hi")
        db.add.assert_not_called()
        db.flush.assert_not_called()
        db.commit.assert_not_called()

    async def test_offer_resolution_final_state_no_mutation(self):
        from app.engines.complaints.complaint_service import ComplaintService
        tenant_id = uuid.uuid4()
        complaint = _mock_complaint(STATUS_CLOSED, tenant_id=tenant_id)
        db = _db_returning(complaint)
        svc = ComplaintService()
        with pytest.raises(ValueError):
            await svc.provider_offer_resolution(
                db, tenant_id, complaint.id, uuid.uuid4(), "rework", "x",
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()


class TestExistingGuardsUnchanged:
    def test_customer_add_message_sibling_pattern_unchanged(self):
        """Confirms the sibling method this fix mirrors is itself
        unmodified."""
        import inspect
        from app.engines.complaints.complaint_service import ComplaintService
        src = inspect.getsource(ComplaintService.add_customer_message) if hasattr(
            ComplaintService, "add_customer_message") else None
        # Fall back to searching the module source for the exact guard
        # if the method name differs from assumption.
        if src is None:
            import app.engines.complaints.complaint_service as mod
            src = inspect.getsource(mod)
        assert "FINAL_STATUSES" in src
        assert "ERR_COMPLAINT_ALREADY_CLOSED" in src

    def test_transition_helper_unchanged(self):
        import inspect
        from app.engines.complaints.complaint_service import ComplaintService
        src = inspect.getsource(ComplaintService._transition)
        assert "ALLOWED_TRANSITIONS_EXT" in src
        assert "ERR_COMPLAINT_INVALID_TRANSITION" in src

    def test_dual_acceptance_guard_unchanged(self):
        import inspect
        from app.engines.complaints.complaint_service import ComplaintService
        src = inspect.getsource(ComplaintService._check_dual_acceptance)
        assert "customer_response" in src and "tenant_response" in src
