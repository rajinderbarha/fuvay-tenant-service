"""Sprint 22 — Quote Approval + Checklist Engine tests.

Covers:
- Constants / status machine (5 tests)
- Quote creation (5 tests)
- Quote item management (5 tests)
- Quote workflow: send→approve/reject/revision (8 tests)
- Status sync (4 tests)
- Checklist management (7 tests)
- Security (4 tests)
- Swagger route registration (7 tests)
"""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest

TENANT_ID    = uuid.uuid4()
OTHER_TENANT = uuid.uuid4()
USER_ID      = uuid.uuid4()
STAFF_ID     = uuid.uuid4()
CUSTOMER_ID  = uuid.uuid4()
JOB_ID       = uuid.uuid4()
BOOKING_ID   = uuid.uuid4()
QUOTE_ID     = uuid.uuid4()
ITEM_ID      = uuid.uuid4()
CHECKLIST_ID = uuid.uuid4()
TEMPLATE_ID  = uuid.uuid4()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_job(status="quote_required"):
    from app.engines.final_records.models import ServiceJob
    j = MagicMock(spec=ServiceJob)
    j.id          = JOB_ID
    j.booking_id  = BOOKING_ID
    j.tenant_id   = TENANT_ID
    j.customer_id = CUSTOMER_ID
    j.status      = status
    j.updated_at  = None
    j.to_dict     = lambda: {"id": str(JOB_ID), "status": j.status}
    return j


def _mock_quote(status="draft", customer_id=None, locked_at=None):
    from app.engines.quote_checklist.models import ServiceJobQuote
    q = MagicMock(spec=ServiceJobQuote)
    q.id              = QUOTE_ID
    q.quote_number    = "QT-ABCDEF1234"
    q.booking_id      = BOOKING_ID
    q.job_id          = JOB_ID
    q.tenant_id       = TENANT_ID
    q.customer_id     = customer_id or CUSTOMER_ID
    q.status          = status
    q.idempotency_key = None
    q.locked_at       = locked_at
    q.to_dict         = lambda: {"id": str(QUOTE_ID), "status": q.status, "tenant_id": str(TENANT_ID)}
    return q


def _mock_quote_item():
    from app.engines.quote_checklist.models import ServiceJobQuoteItem
    i = MagicMock(spec=ServiceJobQuoteItem)
    i.id                = ITEM_ID
    i.quote_id          = QUOTE_ID
    i.job_id            = JOB_ID
    i.tenant_id         = TENANT_ID
    i.item_type         = "labour"
    i.item_name         = "Labour charge"
    i.quantity          = Decimal("1")
    i.unit_price        = Decimal("500")
    i.line_total        = Decimal("500")
    i.is_customer_visible = True
    i.to_dict           = lambda: {"id": str(ITEM_ID), "item_type": "labour", "line_total": "500"}
    return i


def _mock_checklist(status="pending"):
    from app.engines.quote_checklist.models import ServiceJobChecklist
    cl = MagicMock(spec=ServiceJobChecklist)
    cl.id              = CHECKLIST_ID
    cl.job_id          = JOB_ID
    cl.booking_id      = BOOKING_ID
    cl.tenant_id       = TENANT_ID
    cl.status          = status
    cl.checklist_type  = "inspection"
    cl.to_dict         = lambda: {"id": str(CHECKLIST_ID), "status": cl.status}
    return cl


def _mock_cl_item():
    from app.engines.quote_checklist.models import ServiceJobChecklistItem
    i = MagicMock(spec=ServiceJobChecklistItem)
    i.id           = uuid.uuid4()
    i.checklist_id = CHECKLIST_ID
    i.job_id       = JOB_ID
    i.item_label   = "Check filter"
    i.input_type   = "checkbox"
    i.is_required  = False
    i.status       = "pending"
    i.to_dict      = lambda: {"id": str(i.id), "status": i.status}
    return i


def _mock_template():
    from app.engines.quote_checklist.models import SjChecklistTemplate
    t = MagicMock(spec=SjChecklistTemplate)
    t.id            = TEMPLATE_ID
    t.template_name = "AC Inspection"
    t.template_type = "inspection"
    t.applies_to    = "offering"
    t.is_active     = True
    t.to_dict       = lambda: {"id": str(TEMPLATE_ID), "template_name": "AC Inspection"}
    return t


def _scalars_result(items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    r.scalar_one_or_none.return_value = items[0] if items else None
    return r


def _mock_db(*execute_results):
    db = MagicMock()

    # Yields the supplied results in order, then a generic result for any
    # further query. A bare finite side_effect list raised StopIteration as
    # soon as the code under test made one more query than the test author
    # happened to anticipate -- which is how these tests silently depended on
    # the platform-fee charge call CRASHING before it reached the database.
    # (It was missing three required arguments; see
    # tests/test_monetization_charge_wiring.py.) These tests assert that a
    # query happened, not how many, so tolerating extra ones keeps their real
    # intent while no longer being coupled to a bug.
    _pending = list(execute_results)

    async def _execute(*_args, **_kwargs):
        return _pending.pop(0) if _pending else MagicMock()

    db.execute  = AsyncMock(side_effect=_execute)
    db.flush    = AsyncMock()
    db.commit   = AsyncMock()
    db.refresh  = AsyncMock()
    db.add      = MagicMock()
    db.delete   = AsyncMock()
    # MODULE-L5-21: quote transitions now fire best-effort notifications, which
    # look up the tenant owner / assigned staff via db.get. Return None so the
    # notify step finds no recipients and no-ops in these unit tests.
    db.get      = AsyncMock(return_value=None)
    return db


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_11_quote_statuses(self):
        from app.engines.quote_checklist import constants as c
        statuses = [
            c.QS_DRAFT, c.QS_SUBMITTED_TO_PROVIDER, c.QS_PROVIDER_APPROVED,
            c.QS_PROVIDER_REJECTED, c.QS_SENT_TO_CUSTOMER, c.QS_CUSTOMER_APPROVED,
            c.QS_CUSTOMER_REJECTED, c.QS_REVISION_REQUESTED, c.QS_REVISED,
            c.QS_EXPIRED, c.QS_CANCELLED,
        ]
        assert len(statuses) == 11

    def test_final_statuses_are_terminal(self):
        from app.engines.quote_checklist.constants import QUOTE_TRANSITIONS, QUOTE_FINAL_STATUSES
        for fs in QUOTE_FINAL_STATUSES:
            assert QUOTE_TRANSITIONS[fs] == set()

    def test_draft_can_reach_sent_to_customer(self):
        from app.engines.quote_checklist.constants import QUOTE_TRANSITIONS, QS_DRAFT, QS_SENT_TO_CUSTOMER
        assert QS_SENT_TO_CUSTOMER in QUOTE_TRANSITIONS[QS_DRAFT]

    def test_sent_to_customer_branches(self):
        from app.engines.quote_checklist.constants import (
            QUOTE_TRANSITIONS, QS_SENT_TO_CUSTOMER,
            QS_CUSTOMER_APPROVED, QS_CUSTOMER_REJECTED, QS_REVISION_REQUESTED,
        )
        allowed = QUOTE_TRANSITIONS[QS_SENT_TO_CUSTOMER]
        assert {QS_CUSTOMER_APPROVED, QS_CUSTOMER_REJECTED, QS_REVISION_REQUESTED}.issubset(allowed)

    def test_error_codes_defined(self):
        from app.engines.quote_checklist import constants as c
        assert c.ERR_QUOTE_NOT_FOUND
        assert c.ERR_QUOTE_ACCESS_DENIED
        assert c.ERR_QUOTE_INVALID_TRANSITION
        assert c.ERR_CHECKLIST_NOT_FOUND
        assert c.ERR_QUOTE_IDEMPOTENCY_CONFLICT


# ─────────────────────────────────────────────────────────────────────────────
# 2. Models
# ─────────────────────────────────────────────────────────────────────────────

class TestModels:
    def test_quote_model_tablename(self):
        from app.engines.quote_checklist.models import ServiceJobQuote
        assert ServiceJobQuote.__tablename__ == "service_job_quotes"

    def test_quote_item_model_tablename(self):
        from app.engines.quote_checklist.models import ServiceJobQuoteItem
        assert ServiceJobQuoteItem.__tablename__ == "service_job_quote_items"

    def test_checklist_template_uses_sj_prefix(self):
        from app.engines.quote_checklist.models import SjChecklistTemplate
        assert SjChecklistTemplate.__tablename__ == "sj_checklist_templates"

    def test_checklist_model_tablename(self):
        from app.engines.quote_checklist.models import ServiceJobChecklist
        assert ServiceJobChecklist.__tablename__ == "service_job_checklists"

    def test_quote_to_dict(self):
        q = _mock_quote()
        d = q.to_dict()
        assert d["id"] == str(QUOTE_ID)
        assert d["status"] == "draft"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Quote creation
# ─────────────────────────────────────────────────────────────────────────────

class TestQuoteCreation:
    @pytest.mark.asyncio
    async def test_create_quote_success(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        job = _mock_job()
        mock_quote = _mock_quote()

        # Phase 2A: create_quote now looks up any existing current quote for
        # the job first (to supersede it) -- none exists here.
        db = _mock_db(_scalars_result([]))
        db.flush  = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with patch.object(svc, "_log_event", AsyncMock()):
                with patch(
                    "app.engines.checklist_catalog.gate.assert_gate_satisfied",
                    AsyncMock(),
                ):
                    result = await svc.create_quote(
                        db, str(JOB_ID), str(TENANT_ID),
                        "repair_quote", str(USER_ID), str(STAFF_ID), "test notes", "rid-1",
                    )
        assert db.add.called

    @pytest.mark.asyncio
    async def test_create_quote_invalid_type_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ITEM_INVALID
        svc = ServiceJobQuoteService()
        job = _mock_job()
        db = MagicMock()
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ITEM_INVALID):
                await svc.create_quote(db, str(JOB_ID), str(TENANT_ID), "bad_type",
                                       str(USER_ID), None, None, None)

    @pytest.mark.asyncio
    async def test_create_quote_wrong_tenant_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ACCESS_DENIED
        svc = ServiceJobQuoteService()
        job = _mock_job()
        db = MagicMock()
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ACCESS_DENIED):
                await svc.create_quote(db, str(JOB_ID), str(OTHER_TENANT), "repair_quote",
                                       str(USER_ID), None, None, None)

    @pytest.mark.asyncio
    async def test_get_quote_not_found(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_NOT_FOUND
        svc = ServiceJobQuoteService()
        db = _mock_db(_scalars_result([]))
        with pytest.raises(ValueError, match=ERR_QUOTE_NOT_FOUND):
            await svc._get_quote(db, str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_list_quotes_for_job(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q1 = _mock_quote("draft")
        q2 = _mock_quote("sent_to_customer")
        res = MagicMock()
        res.scalars.return_value.all.return_value = [q1, q2]
        db = _mock_db(res)
        result = await svc.list_quotes_for_job(db, str(JOB_ID), str(TENANT_ID))
        assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 4. Quote item management
# ─────────────────────────────────────────────────────────────────────────────

class TestQuoteItems:
    @pytest.mark.asyncio
    async def test_add_item_success(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _mock_quote("draft")
        item = _mock_quote_item()
        items_res = MagicMock()
        items_res.scalars.return_value.all.return_value = [item]

        db = MagicMock()
        db.flush  = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add    = MagicMock()
        db.execute = AsyncMock(side_effect=[items_res, MagicMock()])

        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with patch.object(svc, "_log_event", AsyncMock()):
                result = await svc.add_item(
                    db, str(QUOTE_ID), str(TENANT_ID),
                    "labour", "Labour charge", None,
                    1.0, 500.0, True, True,
                    str(USER_ID), "rid-1",
                )
        assert db.add.called

    @pytest.mark.asyncio
    async def test_add_item_locked_quote_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ALREADY_LOCKED
        svc = ServiceJobQuoteService()
        q = _mock_quote("customer_approved", locked_at=datetime.now(timezone.utc))
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ALREADY_LOCKED):
                await svc.add_item(db, str(QUOTE_ID), str(TENANT_ID),
                                   "labour", "Test", None, 1.0, 100.0, True, True,
                                   str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_add_item_invalid_type_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ITEM_INVALID
        svc = ServiceJobQuoteService()
        q = _mock_quote("draft")
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ITEM_INVALID):
                await svc.add_item(db, str(QUOTE_ID), str(TENANT_ID),
                                   "bad_type", "Test", None, 1.0, 100.0, True, True,
                                   str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_remove_item_not_found_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ITEM_INVALID
        svc = ServiceJobQuoteService()
        q = _mock_quote("draft")
        res = _scalars_result([])
        db = _mock_db(res)
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ITEM_INVALID):
                await svc.remove_item(db, str(QUOTE_ID), str(uuid.uuid4()),
                                      str(TENANT_ID), str(USER_ID), None)

    def test_recalculate_totals(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        items = []
        for itype, amount in [("labour", 500), ("part", 200), ("discount", 50), ("tax", 25)]:
            i = MagicMock()
            i.item_type  = itype
            i.line_total = Decimal(str(amount))
            items.append(i)
        totals = svc._recalculate(items)
        assert totals["total_amount"] == Decimal("675")  # 500+200-50+25


# ─────────────────────────────────────────────────────────────────────────────
# 5. Quote workflow
# ─────────────────────────────────────────────────────────────────────────────

class TestQuoteWorkflow:
    @pytest.mark.asyncio
    async def test_send_to_customer_requires_items(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ITEM_REQUIRED
        svc = ServiceJobQuoteService()
        q = _mock_quote("draft")
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        db = _mock_db(res)
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ITEM_REQUIRED):
                await svc.send_to_customer(db, str(QUOTE_ID), str(TENANT_ID),
                                           None, str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_send_to_customer_bad_transition_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_INVALID_TRANSITION
        svc = ServiceJobQuoteService()
        q = _mock_quote("customer_approved")  # already final — can't send again
        item = _mock_quote_item()
        res = MagicMock()
        res.scalars.return_value.all.return_value = [item]
        db = _mock_db(res, MagicMock())
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_INVALID_TRANSITION):
                await svc.send_to_customer(db, str(QUOTE_ID), str(TENANT_ID),
                                           None, str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_customer_approve_success(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", customer_id=CUSTOMER_ID)
        db = _mock_db(MagicMock(), MagicMock())
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with patch.object(svc, "_sync_job_status", AsyncMock()):
                with patch.object(svc, "_log_event", AsyncMock()):
                    result = await svc.customer_approve(
                        db, str(QUOTE_ID), str(CUSTOMER_ID),
                        "idem-key-1", str(USER_ID), "rid-1",
                    )
        assert db.execute.called

    @pytest.mark.asyncio
    async def test_customer_approve_idempotent(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _mock_quote("customer_approved", customer_id=CUSTOMER_ID)
        q.idempotency_key = "idem-key-1"
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            result = await svc.customer_approve(
                db, str(QUOTE_ID), str(CUSTOMER_ID),
                "idem-key-1", str(USER_ID), None,
            )
        assert result["status"] == "customer_approved"
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_customer_approve_conflict_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_IDEMPOTENCY_CONFLICT
        svc = ServiceJobQuoteService()
        q = _mock_quote("customer_approved", customer_id=CUSTOMER_ID)
        q.idempotency_key = "different-key"
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_IDEMPOTENCY_CONFLICT):
                await svc.customer_approve(
                    db, str(QUOTE_ID), str(CUSTOMER_ID),
                    "idem-key-1", str(USER_ID), None,
                )

    @pytest.mark.asyncio
    async def test_customer_reject_no_reason_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_REJECTION_REASON_REQUIRED
        svc = ServiceJobQuoteService()
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=_mock_quote("sent_to_customer"))):
            with pytest.raises(ValueError, match=ERR_QUOTE_REJECTION_REASON_REQUIRED):
                await svc.customer_reject(db, str(QUOTE_ID), str(CUSTOMER_ID),
                                          "", str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_customer_reject_wrong_customer_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", customer_id=CUSTOMER_ID)
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED):
                await svc.customer_reject(db, str(QUOTE_ID), str(OTHER_TENANT),
                                          "not happy", str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_request_revision_no_reason_raises(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_REVISION_REASON_REQUIRED
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", customer_id=CUSTOMER_ID)
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_REVISION_REASON_REQUIRED):
                await svc.customer_request_revision(
                    db, str(QUOTE_ID), str(CUSTOMER_ID), "", str(USER_ID), None,
                )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Status sync
# ─────────────────────────────────────────────────────────────────────────────

class TestStatusSync:
    def test_job_status_constants_defined(self):
        from app.engines.quote_checklist.constants import (
            JOB_STATUS_AWAITING_QUOTE_APPROVAL,
            JOB_STATUS_QUOTE_APPROVED,
            JOB_STATUS_QUOTE_REJECTED,
            JOB_STATUS_QUOTE_REVISION,
        )
        assert JOB_STATUS_AWAITING_QUOTE_APPROVAL == "awaiting_customer_quote_approval"
        assert JOB_STATUS_QUOTE_APPROVED           == "quote_approved"
        assert JOB_STATUS_QUOTE_REJECTED           == "quote_rejected"
        assert JOB_STATUS_QUOTE_REVISION           == "quote_revision_requested"

    @pytest.mark.asyncio
    async def test_send_syncs_job_status(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _mock_quote("draft")
        item = _mock_quote_item()
        res = MagicMock()
        res.scalars.return_value.all.return_value = [item]
        db = _mock_db(res, MagicMock(), MagicMock())
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        synced = []
        async def fake_sync(db, job_id, st):
            synced.append(st)
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with patch.object(svc, "_sync_job_status", fake_sync):
                with patch.object(svc, "_log_event", AsyncMock()):
                    await svc.send_to_customer(db, str(QUOTE_ID), str(TENANT_ID),
                                               None, str(USER_ID), None)
        # Phase 2A fix: job-status sync now uses the SAME JS_* vocabulary the
        # execution engine's JOB_TRANSITIONS graph validates, not the
        # previously-disjoint JOB_STATUS_* strings that JOB_TRANSITIONS had
        # never heard of (a second, unvalidated status-write path).
        assert "quote_required" in synced

    @pytest.mark.asyncio
    async def test_approve_syncs_job_status(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", customer_id=CUSTOMER_ID)
        db = _mock_db(MagicMock(), MagicMock())
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        synced = []
        async def fake_sync(db, job_id, st):
            synced.append(st)
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with patch.object(svc, "_sync_job_status", fake_sync):
                with patch.object(svc, "_log_event", AsyncMock()):
                    await svc.customer_approve(
                        db, str(QUOTE_ID), str(CUSTOMER_ID),
                        "idem-1", str(USER_ID), None,
                    )
        # Phase 2A: approval no longer moves the job off JS_QUOTE_REQUIRED --
        # the work-start guard resolves whether THIS approved+current quote
        # authorizes work, rather than the job status alone carrying that fact.
        assert "quote_required" in synced

    @pytest.mark.asyncio
    async def test_reject_syncs_job_status(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", customer_id=CUSTOMER_ID)
        db = _mock_db(MagicMock(), MagicMock())
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        synced = []
        async def fake_sync(db, job_id, st):
            synced.append(st)
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with patch.object(svc, "_sync_job_status", fake_sync):
                with patch.object(svc, "_log_event", AsyncMock()):
                    await svc.customer_reject(
                        db, str(QUOTE_ID), str(CUSTOMER_ID),
                        "Too expensive", str(USER_ID), None,
                    )
        # Phase 2A (spec section 9): rejection now moves the job to a real
        # terminal status the execution engine's own JOB_TRANSITIONS graph
        # defines, instead of a string ("quote_rejected") that graph never
        # recognized.
        assert "closed_estimate_declined" in synced


# ─────────────────────────────────────────────────────────────────────────────
# 7. Checklists
# ─────────────────────────────────────────────────────────────────────────────

class TestChecklists:
    @pytest.mark.asyncio
    async def test_create_checklist_no_template(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        cl = _mock_checklist()
        db = MagicMock()
        db.flush  = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add    = MagicMock()
        db.execute = AsyncMock(return_value=_scalars_result([]))
        result = await svc.create_checklist(
            db, str(JOB_ID), str(BOOKING_ID), str(TENANT_ID),
            "inspection", None, str(USER_ID), None,
        )
        assert db.add.called

    @pytest.mark.asyncio
    async def test_create_template(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        db = MagicMock()
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        db.add     = MagicMock()
        await svc.create_template(
            db, "AC Filter Checklist", "inspection", "offering",
            None, None, None, False,
        )
        assert db.add.called

    @pytest.mark.asyncio
    async def test_get_checklist_not_found(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        from app.engines.quote_checklist.constants import ERR_CHECKLIST_NOT_FOUND
        svc = ServiceChecklistService()
        db = _mock_db(_scalars_result([]))
        with pytest.raises(ValueError, match=ERR_CHECKLIST_NOT_FOUND):
            await svc._get_checklist(db, str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_complete_checklist_already_completed_raises(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        from app.engines.quote_checklist.constants import ERR_CHECKLIST_ALREADY_COMPLETED
        svc = ServiceChecklistService()
        cl = _mock_checklist(status="completed")
        db = MagicMock()
        with patch.object(svc, "_get_checklist", AsyncMock(return_value=cl)):
            with pytest.raises(ValueError, match=ERR_CHECKLIST_ALREADY_COMPLETED):
                await svc.complete_checklist(db, str(CHECKLIST_ID), str(TENANT_ID), str(USER_ID))

    @pytest.mark.asyncio
    async def test_complete_checklist_success(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        cl = _mock_checklist("in_progress")
        db = _mock_db(MagicMock())
        db.commit  = AsyncMock()
        db.refresh = AsyncMock()
        with patch.object(svc, "_get_checklist", AsyncMock(return_value=cl)):
            result = await svc.complete_checklist(
                db, str(CHECKLIST_ID), str(TENANT_ID), str(USER_ID),
            )
        assert db.execute.called

    @pytest.mark.asyncio
    async def test_update_checklist_item_wrong_tenant_raises(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        from app.engines.quote_checklist.constants import ERR_CHECKLIST_ACCESS_DENIED
        svc = ServiceChecklistService()
        cl = _mock_checklist("pending")
        db = MagicMock()
        with patch.object(svc, "_get_checklist", AsyncMock(return_value=cl)):
            with pytest.raises(ValueError, match=ERR_CHECKLIST_ACCESS_DENIED):
                await svc.update_checklist_item(
                    db, str(CHECKLIST_ID), str(uuid.uuid4()),
                    str(OTHER_TENANT), str(USER_ID),
                    None, None, None, None, "completed",
                )

    @pytest.mark.asyncio
    async def test_list_checklists_for_job(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        svc = ServiceChecklistService()
        cl = _mock_checklist()
        res = MagicMock()
        res.scalars.return_value.all.return_value = [cl]
        db = _mock_db(res)
        result = await svc.list_checklists_for_job(db, str(JOB_ID), str(TENANT_ID))
        assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 8. Security
# ─────────────────────────────────────────────────────────────────────────────

class TestSecurity:
    @pytest.mark.asyncio
    async def test_provider_cannot_access_other_tenant_quote(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ACCESS_DENIED
        svc = ServiceJobQuoteService()
        q = _mock_quote("draft")
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ACCESS_DENIED):
                await svc.cancel_quote(db, str(QUOTE_ID), str(OTHER_TENANT),
                                       None, str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_customer_cannot_approve_other_customer_quote(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", customer_id=CUSTOMER_ID)
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED):
                await svc.customer_approve(
                    db, str(QUOTE_ID), str(OTHER_TENANT),
                    "idem-1", str(USER_ID), None,
                )

    @pytest.mark.asyncio
    async def test_locked_quote_rejects_item_add(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_ALREADY_LOCKED
        svc = ServiceJobQuoteService()
        q = _mock_quote("customer_approved", locked_at=datetime.now(timezone.utc))
        db = MagicMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_ALREADY_LOCKED):
                await svc.add_item(db, str(QUOTE_ID), str(TENANT_ID),
                                   "labour", "Test", None, 1, 100, True, True,
                                   str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_checklist_wrong_tenant_blocked(self):
        from app.engines.quote_checklist.checklist_service import ServiceChecklistService
        from app.engines.quote_checklist.constants import ERR_CHECKLIST_ACCESS_DENIED
        svc = ServiceChecklistService()
        cl = _mock_checklist()
        db = MagicMock()
        with patch.object(svc, "_get_checklist", AsyncMock(return_value=cl)):
            with pytest.raises(ValueError, match=ERR_CHECKLIST_ACCESS_DENIED):
                await svc.complete_checklist(db, str(CHECKLIST_ID), str(OTHER_TENANT), str(USER_ID))


# ─────────────────────────────────────────────────────────────────────────────
# 9. Swagger route registration
# ─────────────────────────────────────────────────────────────────────────────

class TestSwaggerRoutes:
    @pytest.fixture(scope="class")
    def routes(self):
        import json
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        return set(resp.json()["paths"].keys())

    def test_staff_create_quote_route(self, routes):
        assert "/staff/quotes" in routes

    def test_staff_send_to_customer_route(self, routes):
        assert "/staff/quotes/{quote_id}/send-to-customer" in routes

    def test_customer_approve_route(self, routes):
        assert "/customer/quotes/{quote_id}/approve" in routes

    def test_customer_reject_route(self, routes):
        assert "/customer/quotes/{quote_id}/reject" in routes

    def test_staff_checklist_create_route(self, routes):
        assert "/staff/checklists" in routes

    def test_admin_template_route(self, routes):
        assert "/admin/checklist-templates" in routes

    def test_admin_quote_route(self, routes):
        assert "/admin/quotes/jobs/{job_id}" in routes
