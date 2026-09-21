"""Complaints must not get stuck waiting on a party who has stopped acting.

Before these fixes the only deadline on a complaint was the provider's first
reply. One message and the case had no clock at all; nothing ever wrote
`closed`, so resolved cases stayed in the provider's Open queue forever; a
declined refund left the case with no legal move; a proposed resolution the
customer never answered held the case open indefinitely; and accepting a
refund offer resolved the case without creating any refund.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.constants import (
    RESOLVED_OR_FINAL_STATUSES, STATUS_AWAITING_PROVIDER, STATUS_CLOSED, STATUS_OPEN,
    STATUS_REFUND_APPROVED, STATUS_REFUND_REQUESTED, STATUS_REJECTED,
    STATUS_RESOLUTION_PROPOSED, STATUS_RESOLVED, STATUS_REWORK_APPROVED,
)
from app.engines.complaints.models import ComplaintResolution, CustomerComplaint, RefundRequest
from app.exceptions import ServiceOSException

NOW = datetime.now(timezone.utc)


def _complaint(status=STATUS_OPEN, **fields) -> CustomerComplaint:
    values = dict(
        id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        category_id=uuid.uuid4(), record_type="service_job", record_id=uuid.uuid4(),
        complaint_type="service_quality", description="The tap still leaks",
        complaint_number="CMP-00000001", status=status, sla_status="on_time",
        provider_response_required=True,
    )
    values.update(fields)
    return CustomerComplaint(**values)


def _service() -> ComplaintService:
    svc = ComplaintService()
    svc._eligibility.get_complaint_policy = AsyncMock(return_value=None)
    return svc


def _db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture(autouse=True)
def _silence_notifications(monkeypatch):
    from app.engines.complaints import notifications
    for name in ("notify_customer_complaint", "notify_provider_complaint",
                 "notify_customer_complaint_channel"):
        monkeypatch.setattr(notifications, name, AsyncMock(return_value=1))


# ── Which clock is running ───────────────────────────────────────────────────

class TestRunningDeadline:
    def test_first_response_clock_runs_until_the_provider_replies(self):
        c = _complaint(tenant_first_response_due_at=NOW + timedelta(hours=2),
                       provider_action_due_at=NOW + timedelta(hours=70))
        assert ComplaintService.running_provider_deadline(c)[1] == "first_response"

    def test_resolution_clock_takes_over_after_the_reply(self):
        """The gap that let complaints sit forever: after one reply, nothing ran."""
        c = _complaint(tenant_first_response_due_at=NOW - timedelta(hours=2),
                       provider_responded_at=NOW - timedelta(hours=1),
                       provider_action_due_at=NOW + timedelta(hours=10))
        due, clock = ComplaintService.running_provider_deadline(c)
        assert clock == "resolution" and due == c.provider_action_due_at

    @pytest.mark.parametrize("status", [STATUS_RESOLUTION_PROPOSED, STATUS_RESOLVED, STATUS_CLOSED])
    def test_no_provider_clock_while_waiting_on_customer_or_done(self, status):
        c = _complaint(status, provider_responded_at=NOW,
                       provider_action_due_at=NOW - timedelta(hours=5))
        assert ComplaintService.running_provider_deadline(c) == (None, None)

    def test_rework_in_progress_is_still_on_the_providers_clock(self):
        c = _complaint(STATUS_REWORK_APPROVED, provider_responded_at=NOW,
                       provider_action_due_at=NOW - timedelta(minutes=1))
        assert ComplaintService.running_provider_deadline(c)[1] == "resolution"


@pytest.mark.asyncio
class TestSlaStatus:
    async def test_unresolved_case_breaches_after_the_first_reply(self):
        c = _complaint(provider_responded_at=NOW - timedelta(days=3),
                       tenant_first_response_due_at=NOW - timedelta(days=3),
                       provider_action_due_at=NOW - timedelta(hours=2))
        db = _db()
        await _service().check_and_update_sla(db, c)
        assert c.sla_status == "breached"
        event = db.add.call_args.args[0]
        assert event.event_type == "sla_breached" and event.new_value["clock"] == "resolution"

    async def test_escalates_a_day_after_the_resolution_deadline(self):
        c = _complaint(provider_responded_at=NOW - timedelta(days=5),
                       provider_action_due_at=NOW - timedelta(hours=25))
        await _service().check_and_update_sla(_db(), c)
        assert c.sla_status == "escalated"

    async def test_warning_window_is_configurable(self):
        c = _complaint(provider_responded_at=NOW,
                       provider_action_due_at=NOW + timedelta(hours=6))
        await _service().check_and_update_sla(_db(), c, warning_hours=8)
        assert c.sla_status == "at_risk"

    async def test_resolved_case_is_never_marked_late(self):
        c = _complaint(STATUS_RESOLVED, tenant_first_response_due_at=NOW - timedelta(days=4))
        db = _db()
        await _service().check_and_update_sla(db, c)
        assert c.sla_status == "on_time"
        db.flush.assert_not_awaited()


# ── Status side effects ──────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestEnterStatus:
    async def test_returning_to_the_provider_restarts_the_clock_from_policy(self):
        svc = _service()
        svc._eligibility.get_complaint_policy = AsyncMock(
            return_value=MagicMock(default_resolution_hours=48))
        c = _complaint(STATUS_AWAITING_PROVIDER, provider_responded_at=NOW, sla_status="breached")
        await svc.enter_status(_db(), c, STATUS_AWAITING_PROVIDER)
        assert c.provider_action_due_at > NOW + timedelta(hours=47)
        assert c.provider_action_due_at < NOW + timedelta(hours=49)
        assert c.sla_status == "on_time"

    async def test_waiting_on_the_customer_stops_the_clock(self):
        c = _complaint(STATUS_RESOLUTION_PROPOSED, provider_responded_at=NOW,
                       provider_action_due_at=NOW + timedelta(hours=3))
        await _service().enter_status(_db(), c, STATUS_RESOLUTION_PROPOSED)
        assert c.provider_action_due_at is None

    async def test_resolving_and_closing_stamp_their_times(self):
        """Accepting a resolution never stamped resolved_at before."""
        c = _complaint(STATUS_RESOLVED)
        svc = _service()
        await svc.enter_status(_db(), c, STATUS_RESOLVED)
        assert c.resolved_at is not None
        await svc.enter_status(_db(), c, STATUS_CLOSED)
        assert c.closed_at is not None


# ── Offers the engine can carry out ──────────────────────────────────────────

@pytest.mark.asyncio
class TestOfferValidation:
    async def test_unmodelled_remedy_is_refused(self):
        """"partial_refund" and "credit" used to resolve the case with no remedy."""
        svc = _service()
        c = _complaint()
        svc.provider_get_complaint = AsyncMock(return_value=c)
        with pytest.raises(ServiceOSException) as exc:
            await svc.provider_offer_resolution(_db(), c.tenant_id, c.id, uuid.uuid4(),
                                                "partial_refund", "half back")
        assert exc.value.error_code == "RESOLUTION_TYPE_NOT_ALLOWED"
        assert c.status == STATUS_OPEN

    async def test_refund_offer_needs_an_amount(self):
        svc = _service()
        c = _complaint()
        svc.provider_get_complaint = AsyncMock(return_value=c)
        with pytest.raises(ServiceOSException) as exc:
            await svc.provider_offer_resolution(_db(), c.tenant_id, c.id, uuid.uuid4(),
                                                "refund", "money back")
        assert exc.value.error_code == "RESOLUTION_AMOUNT_REQUIRED"

    async def test_policy_can_switch_rework_off(self):
        svc = _service()
        svc._eligibility.get_complaint_policy = AsyncMock(
            return_value=MagicMock(allow_rework=False, allow_refund_request=True))
        c = _complaint()
        svc.provider_get_complaint = AsyncMock(return_value=c)
        with pytest.raises(ServiceOSException):
            await svc.provider_offer_resolution(_db(), c.tenant_id, c.id, uuid.uuid4(),
                                                "rework", "we will return")

    async def test_proposing_counts_as_the_providers_response(self):
        """Otherwise a provider who answered with an offer paid the no-reply penalty."""
        svc = _service()
        c = _complaint(tenant_first_response_due_at=NOW + timedelta(hours=5))
        svc.provider_get_complaint = AsyncMock(return_value=c)
        await svc.provider_offer_resolution(_db(), c.tenant_id, c.id, uuid.uuid4(),
                                            "apology", "Sorry about the mess")
        assert c.status == STATUS_RESOLUTION_PROPOSED
        assert c.provider_responded_at is not None
        assert c.provider_response_required is False


# ── Accepting a refund offer creates a refund ────────────────────────────────

@pytest.mark.asyncio
class TestRefundOfferAcceptance:
    async def test_accepting_a_refund_offer_creates_an_approved_refund(self, monkeypatch):
        from app.engines.complaints import refund_service
        svc = _service()
        c = _complaint(STATUS_RESOLUTION_PROPOSED, provider_responded_at=NOW)
        resolution = ComplaintResolution(
            id=uuid.uuid4(), complaint_id=c.id, resolution_type="refund", status="proposed",
            proposed_by_type="provider", description="Refund the call-out", amount=Decimal("300.00"),
        )
        svc.get_customer_complaint = AsyncMock(return_value=c)
        svc._get_resolution = AsyncMock(return_value=resolution)
        create = AsyncMock()
        monkeypatch.setattr(refund_service.RefundRequestService, "create_accepted_offer_refund", create)

        await svc.customer_accept_resolution(_db(), c.customer_id, c.id, resolution.id)

        create.assert_awaited_once()
        assert c.status == STATUS_REFUND_APPROVED
        assert c.provider_action_due_at is not None  # recording the repayment is now owed

    async def test_an_offer_that_is_no_longer_open_cannot_be_accepted(self):
        svc = _service()
        c = _complaint(STATUS_RESOLUTION_PROPOSED)
        resolution = ComplaintResolution(
            id=uuid.uuid4(), complaint_id=c.id, resolution_type="apology", status="cancelled",
            proposed_by_type="provider", description="Sorry",
        )
        svc.get_customer_complaint = AsyncMock(return_value=c)
        svc._get_resolution = AsyncMock(return_value=resolution)
        with pytest.raises(ValueError):
            await svc.customer_accept_resolution(_db(), c.customer_id, c.id, resolution.id)
        assert c.status == STATUS_RESOLUTION_PROPOSED

    async def test_offered_refund_starts_approved_for_the_offered_amount(self):
        from app.engines.complaints.refund_service import RefundRequestService
        svc = RefundRequestService()
        svc._invoice_for_complaint = AsyncMock(return_value=None)
        svc._log_event = AsyncMock()
        db = _db()
        db.scalar = AsyncMock(return_value=None)
        c = _complaint(STATUS_RESOLUTION_PROPOSED)
        resolution = ComplaintResolution(
            id=uuid.uuid4(), complaint_id=c.id, resolution_type="refund", status="proposed",
            proposed_by_type="provider", proposed_by_user_id=uuid.uuid4(),
            description="Refund", amount=Decimal("300.00"),
        )
        refund = await svc.create_accepted_offer_refund(db, c, resolution)
        assert refund.status == "approved"
        assert refund.approved_amount == Decimal("300.00")


# ── A declined refund moves the case on ──────────────────────────────────────

@pytest.mark.asyncio
class TestDeclinedRefund:
    async def _decline(self, complaint_type):
        from app.engines.complaints.refund_service import RefundRequestService
        svc = RefundRequestService()
        c = _complaint(STATUS_REFUND_REQUESTED, complaint_type=complaint_type)
        refund = RefundRequest(id=uuid.uuid4(), complaint_id=c.id, customer_id=c.customer_id,
                               tenant_id=c.tenant_id, status="requested",
                               refund_type="service_refund", reason="leak")
        svc._get_refund = AsyncMock(return_value=refund)
        svc._complaint_svc = _service()
        svc._complaint_svc.get_complaint = AsyncMock(return_value=c)
        svc._log_event = AsyncMock()
        await svc.provider_decide_refund(_db(), refund.id, c.tenant_id, uuid.uuid4(),
                                         approve=False, reason="Work was done correctly")
        return c

    async def test_refund_only_case_ends_rejected(self):
        c = await self._decline("refund_request")
        assert c.status == STATUS_REJECTED
        assert c.closed_at is not None

    async def test_other_complaints_go_back_to_the_provider_on_a_fresh_clock(self):
        c = await self._decline("service_quality")
        assert c.status == STATUS_AWAITING_PROVIDER
        assert c.provider_action_due_at is not None
        assert c.provider_responded_at is not None


# ── Settlements never promise money ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_monetary_settlement_is_refused_before_anything_is_written():
    svc = _service()
    c = _complaint()
    svc.provider_get_complaint = AsyncMock(return_value=c)
    db = _db()
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_settlement_proposal(db, c.id, "provider", uuid.uuid4(), "full_refund",
                                             "all of it", tenant_id=c.tenant_id)
    assert exc.value.error_code == "SETTLEMENT_MONETARY_REMEDY_NOT_ALLOWED"
    db.add.assert_not_called()


# ── Queue counts ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolved_cases_are_not_counted_as_open():
    rows = [_complaint(STATUS_OPEN), _complaint(STATUS_RESOLVED), _complaint("settled")]
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    db = _db()
    db.execute = AsyncMock(return_value=result)
    summary = await _service().tenant_queue_summary(db, uuid.uuid4())
    assert summary["open"] == 1 and summary["total"] == 3


def test_duplicate_check_treats_every_unresolved_status_as_open():
    """Rework or refund in progress used to let the same complaint be filed again."""
    import inspect
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService
    src = inspect.getsource(ComplaintEligibilityService.check_duplicate_open_complaint)
    assert "notin_(list(RESOLVED_OR_FINAL_STATUSES))" in src
    assert STATUS_REWORK_APPROVED not in RESOLVED_OR_FINAL_STATUSES


# ── Deadlines at filing come from the admin policy ───────────────────────────

@pytest.mark.asyncio
class TestFilingDeadlines:
    async def _file(self, policy, **kwargs):
        svc = _service()
        svc._eligibility.check_eligible = AsyncMock(return_value={"eligible": True, "policy": policy})
        svc._resolve_tenant_for_record = AsyncMock(return_value=uuid.uuid4())
        svc._link_service_job = AsyncMock()
        db = _db()
        await svc.create_complaint(db, uuid.uuid4(), uuid.uuid4(), "service_job", uuid.uuid4(),
                                   kwargs.pop("complaint_type", "service_quality"), "broken",
                                   commit=False, **kwargs)
        return next(a.args[0] for a in db.add.call_args_list
                    if isinstance(a.args[0], CustomerComplaint))

    async def test_policy_hours_set_both_deadlines(self):
        c = await self._file({"default_provider_response_hours": 6, "default_resolution_hours": 30})
        assert timedelta(hours=5) < c.tenant_first_response_due_at - NOW < timedelta(hours=7)
        assert timedelta(hours=29) < c.provider_action_due_at - NOW < timedelta(hours=31)

    async def test_provider_opened_case_has_no_reply_deadline(self):
        c = await self._file(None, complaint_type="payment_issue",
                             internal_payment_dispute=True, created_by_actor_type="provider")
        assert c.tenant_first_response_due_at is None
        assert c.provider_action_due_at is not None

    async def test_reply_deadline_can_be_switched_off(self):
        c = await self._file({"require_provider_response": False})
        assert c.tenant_first_response_due_at is None


# ── Scheduler ────────────────────────────────────────────────────────────────

class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return list(self._rows)

    def scalar_one_or_none(self):
        return None


class _Session:
    def __init__(self, rows):
        self.rows = rows
        self.added = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, *args, **kwargs):
        return _Result(self.rows)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass


@pytest.fixture
def job(monkeypatch):
    import app.database
    from app.jobs import complaint_sla
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    state = {"rows": []}
    monkeypatch.setattr(app.database, "get_session_factory",
                        lambda: (lambda: _Session(state["rows"])))
    monkeypatch.setattr(complaint_sla, "_sla_warning_hours", AsyncMock(return_value=4))
    monkeypatch.setattr(ComplaintEligibilityService, "get_complaint_policy",
                        AsyncMock(return_value=None))
    charge = AsyncMock(return_value={"idempotent": False, "credit_delta": Decimal("-50")})
    monkeypatch.setattr(complaint_sla, "_charge_sla_penalty", charge)
    return complaint_sla, state, charge


@pytest.mark.asyncio
class TestScheduler:
    async def test_overdue_resolution_is_penalised_once_per_provider_turn(self, job):
        complaint_sla, state, charge = job
        due = NOW - timedelta(hours=1)
        c = _complaint(STATUS_AWAITING_PROVIDER, provider_responded_at=NOW - timedelta(days=4),
                       provider_action_due_at=due)
        state["rows"] = [c]

        await complaint_sla.run_sla_check()
        await complaint_sla.run_sla_check()

        charge.assert_awaited_once()
        kwargs = charge.await_args.kwargs
        assert kwargs["source_type"] == "complaint_resolution"
        assert kwargs["source_id"] == f"{c.id}:{due.strftime('%Y%m%dT%H%M')}"
        assert c.sla_status == "breached"

    async def test_reply_penalty_is_not_charged_on_the_resolution_clock(self, job):
        """A provider-opened case has no reply deadline to miss."""
        complaint_sla, state, charge = job
        c = _complaint(STATUS_OPEN, provider_action_due_at=NOW - timedelta(hours=1))
        state["rows"] = [c]
        await complaint_sla.run_sla_check()
        assert [call.kwargs["source_type"] for call in charge.await_args_list] == ["complaint_resolution"]
        assert c.provider_sla_penalized_at is None

    async def test_resolved_cases_close_after_the_follow_up_window(self, job):
        complaint_sla, state, _charge = job
        old = _complaint(STATUS_RESOLVED, resolved_at=NOW - timedelta(hours=80))
        recent = _complaint(STATUS_RESOLVED, resolved_at=NOW - timedelta(hours=10))
        state["rows"] = [old, recent]
        counts = await complaint_sla.run_auto_close()
        assert counts["closed"] == 1
        assert old.status == STATUS_CLOSED and old.closed_at is not None
        assert recent.status == STATUS_RESOLVED

    async def test_unanswered_offer_resolves_the_case(self, job, monkeypatch):
        complaint_sla, state, _charge = job
        c = _complaint(STATUS_RESOLUTION_PROPOSED, provider_responded_at=NOW - timedelta(days=9))
        offer = ComplaintResolution(
            id=uuid.uuid4(), complaint_id=c.id, resolution_type="apology", status="proposed",
            proposed_by_type="provider", description="Sorry",
            created_at=NOW - timedelta(days=8),
        )
        monkeypatch.setattr(ComplaintService, "list_resolutions", AsyncMock(return_value=[offer]))
        state["rows"] = [c]
        counts = await complaint_sla.run_customer_response_check()
        assert counts["expired"] == 1
        assert c.status == STATUS_RESOLVED
        assert offer.status == "cancelled"  # can no longer be accepted

    async def test_customer_is_reminded_before_the_offer_expires(self, job, monkeypatch):
        complaint_sla, state, _charge = job
        c = _complaint(STATUS_RESOLUTION_PROPOSED, provider_responded_at=NOW - timedelta(days=3))
        offer = ComplaintResolution(
            id=uuid.uuid4(), complaint_id=c.id, resolution_type="rework", status="proposed",
            proposed_by_type="provider", description="Free visit",
            created_at=NOW - timedelta(hours=50),
        )
        monkeypatch.setattr(ComplaintService, "list_resolutions", AsyncMock(return_value=[offer]))
        state["rows"] = [c]
        counts = await complaint_sla.run_customer_response_check()
        assert counts == {"checked": 1, "reminded": 1, "expired": 0}
        assert c.status == STATUS_RESOLUTION_PROPOSED


# ── Provider workspace copy ──────────────────────────────────────────────────

def test_workspace_tells_the_provider_what_they_still_owe():
    from app.engines.complaints.tenant_router import _available_actions, _blocked_reason
    assert _available_actions(STATUS_RESOLVED) == ["SEND_MESSAGE"]
    assert _available_actions(STATUS_CLOSED) == []
    reason = _blocked_reason(STATUS_REWORK_APPROVED, _available_actions(STATUS_REWORK_APPROVED))
    assert "rework" in reason.lower() and "Refunds & Warranty" in reason
    assert "closes automatically" in _blocked_reason(STATUS_RESOLVED, ["SEND_MESSAGE"])


# ── Penalty amount lookup ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_penalty_amount_comes_from_the_typed_policy_resolver(monkeypatch):
    """The raw SQL here used `:category_id IS NULL`, which asyncpg rejects
    ("could not determine data type of parameter"). Complaints always carry a
    category, so every penalty raised and the whole sweep rolled back."""
    import inspect
    from app.jobs import complaint_sla
    from app.engines.complaints.eligibility_service import ComplaintEligibilityService

    lookup = AsyncMock(return_value=MagicMock(provider_sla_breach_penalty=Decimal("75.00")))
    monkeypatch.setattr(ComplaintEligibilityService, "get_complaint_policy", lookup)
    tenant, category = uuid.uuid4(), uuid.uuid4()
    amount = await complaint_sla._resolve_penalty_amount(AsyncMock(), str(tenant), category)
    assert amount == Decimal("75.00")
    assert lookup.await_args.args[1:] == (category, tenant)
    assert "text(" not in inspect.getsource(complaint_sla._resolve_penalty_amount)


# ── Second pass: remaining ways a case could stall ───────────────────────────

def test_refund_requests_stay_on_the_resolution_clock():
    """The refund's one-off 24h penalty left an "under review" refund free to sit."""
    c = _complaint(STATUS_REFUND_REQUESTED, provider_responded_at=NOW,
                   provider_action_due_at=NOW - timedelta(minutes=5))
    assert ComplaintService.running_provider_deadline(c)[1] == "resolution"


@pytest.mark.asyncio
async def test_a_provider_turn_case_without_a_deadline_gets_one(job):
    complaint_sla, state, charge = job
    c = _complaint(STATUS_REFUND_REQUESTED, provider_responded_at=NOW)
    state["rows"] = [c]
    counts = await complaint_sla.run_sla_check()
    assert counts["deadline_stamped"] == 1
    assert c.provider_action_due_at > NOW
    charge.assert_not_awaited()


@pytest.mark.asyncio
class TestReworkCancel:
    def _svc(self, complaint, rework):
        from app.engines.complaints.rework_service import ServiceReworkService
        svc = ServiceReworkService()
        svc._complaint_svc = _service()
        svc._complaint_svc.get_complaint = AsyncMock(return_value=complaint)
        svc._get_rework = AsyncMock(return_value=rework)
        svc._log_event = AsyncMock()
        return svc

    async def test_cancel_hands_the_case_back_on_a_fresh_clock(self):
        from app.engines.complaints.models import ServiceReworkRequest
        c = _complaint(STATUS_REWORK_APPROVED, provider_responded_at=NOW,
                       provider_action_due_at=NOW - timedelta(hours=3), sla_status="breached")
        rework = ServiceReworkRequest(id=uuid.uuid4(), complaint_id=c.id, tenant_id=c.tenant_id,
                                      customer_id=c.customer_id, status="scheduled", rework_reason="leak")
        svc = self._svc(c, rework)
        await svc.cancel_rework(_db(), rework.id, uuid.uuid4(),
                                "Customer refused access for the visit", tenant_id=c.tenant_id)
        assert rework.status == "cancelled"
        assert c.status == STATUS_AWAITING_PROVIDER
        assert c.provider_action_due_at > NOW and c.sla_status == "on_time"

    async def test_cancel_needs_a_reason(self):
        from app.engines.complaints.models import ServiceReworkRequest
        c = _complaint(STATUS_REWORK_APPROVED)
        rework = ServiceReworkRequest(id=uuid.uuid4(), complaint_id=c.id, tenant_id=c.tenant_id,
                                      customer_id=c.customer_id, status="approved", rework_reason="leak")
        with pytest.raises(ServiceOSException):
            await self._svc(c, rework).cancel_rework(_db(), rework.id, uuid.uuid4(), "no", tenant_id=c.tenant_id)
        assert rework.status == "approved"

    async def test_a_completed_rework_cannot_be_cancelled(self):
        from app.engines.complaints.models import ServiceReworkRequest
        c = _complaint(STATUS_RESOLVED)
        rework = ServiceReworkRequest(id=uuid.uuid4(), complaint_id=c.id, tenant_id=c.tenant_id,
                                      customer_id=c.customer_id, status="completed", rework_reason="leak")
        with pytest.raises(ServiceOSException):
            await self._svc(c, rework).cancel_rework(_db(), rework.id, uuid.uuid4(),
                                                     "Customer changed their mind", tenant_id=c.tenant_id)


def test_warranty_penalty_is_keyed_per_missed_deadline():
    from app.jobs.complaint_sla import warranty_penalty_source_id
    claim = uuid.uuid4()
    first = warranty_penalty_source_id(claim, NOW - timedelta(days=2))
    after_escalation = warranty_penalty_source_id(claim, NOW + timedelta(hours=24))
    assert first != after_escalation
    assert warranty_penalty_source_id(claim, NOW) == warranty_penalty_source_id(claim, NOW)


def test_an_early_warranty_reply_does_not_excuse_later_escalations():
    import inspect
    from app.engines.platform_commerce.service import CommerceService
    from app.jobs import complaint_sla
    escalate = inspect.getsource(CommerceService.escalate_claim)
    assert "provider_responded_at < c.escalated_at" in escalate
    assert 'Decimal("50.00")' not in escalate
    assert "WarrantyClaim.provider_responded_at < WarrantyClaim.escalated_at" in inspect.getsource(
        complaint_sla.run_remedy_sla_check)


def test_dashboards_share_one_definition_of_open():
    """Hand-written lists named statuses that do not exist, so counts read zero."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    stale = re.compile(r"'investigating'|'awaiting_provider'[^_]|'in_progress'\)|\"withdrawn\"|'withdrawn'")
    for rel in ("app/engines/analytics/provider_analytics.py", "app/engines/analytics/admin_analytics.py",
                "app/engines/analytics/intelligence_service.py",
                "app/engines/execution/home_services_dashboard_service.py",
                "app/engines/final_records/tenant_bookings_jobs_router.py"):
        src = (root / rel).read_text(encoding="utf-8")
        complaint_lines = [line for line in src.splitlines() if "complaint" in line.lower() or "status" in line]
        assert not any(stale.search(line) for line in complaint_lines), rel
