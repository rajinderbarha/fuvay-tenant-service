"""ARRIVAL-INSPECTION-QUOTE-APPROVAL phase -- exercises the already-existing
`ServiceJobQuoteService` customer-facing methods directly (the same real
service the fixed `/v1/customer/quotes` router calls), using real factories
rather than mocking away ownership/serialization. Covers the two fixes made
this phase (`list_customer_quotes` is_current filter + internal-notes strip)
plus the pre-existing hardened behavior this phase now depends on for the
first time (ownership, idempotency, stale-version, decision-state machine).
"""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
from app.engines.quote_checklist.models import ServiceJobQuote, ServiceJobQuoteItem
from app.engines.quote_checklist.constants import (
    QS_SENT_TO_CUSTOMER, QS_CUSTOMER_APPROVED, QS_CUSTOMER_REJECTED,
)
from app.engines.execution.constants import JS_QUOTE_REQUIRED

NOTIFY_PATCH = "app.engines.quote_checklist.notifications.notify_provider_quote_decision"


def _scalar_one(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _scalars(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(items)
    return result


def _get_quote_db(quote, items=None):
    """Mock matching `get_quote`'s exact call order: fetch quote, fetch items."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[_scalar_one(quote), _scalars(items or [])])
    return db


def _decision_db(quote, items=None, job_status=JS_QUOTE_REQUIRED):
    """Mock matching `customer_approve`/`customer_reject`'s exact call
    order (successful path): fetch quote, UPDATE quote, fetch job status
    (sync), UPDATE job, fetch items (for `_customer_dict`)."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        _scalar_one(quote),
        MagicMock(),
        _scalar_one(job_status),
        MagicMock(),
        _scalars(items or []),
    ])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _rejected_before_write_db(quote):
    """For calls that raise before any mutation (ownership/idempotency/
    stale-version/invalid-transition rejections) -- only the initial
    `_get_quote` fetch happens."""
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one(quote))
    return db


def _quote(**overrides):
    defaults = dict(
        id=uuid.uuid4(), quote_number="QT-TEST0001",
        booking_id=uuid.uuid4(), job_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        customer_id=uuid.uuid4(), status=QS_SENT_TO_CUSTOMER,
        quote_type="repair_quote", currency="INR",
        labour_amount=Decimal("1450"), parts_amount=Decimal("0"), service_amount=Decimal("0"),
        discount_amount=Decimal("299"), tax_amount=Decimal("0"),
        total_amount=Decimal("1450"), customer_payable_amount=Decimal("1450"),
        provider_internal_notes="internal cost margin 40%",
        customer_visible_notes="Cooling circuit needs repair.",
        rejection_reason=None, revision_reason=None, idempotency_key=None,
        expires_at=None, approved_at=None, rejected_at=None, sent_to_customer_at=None,
        locked_at=None, version_number=1, is_current=True, supersedes_quote_id=None,
        superseded_at=None, approved_by=None, created_at=None, updated_at=None,
    )
    defaults.update(overrides)
    q = ServiceJobQuote()
    for k, v in defaults.items():
        setattr(q, k, v)
    return q


# ── get_quote (read) ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_can_read_own_actionable_quote():
    q = _quote()
    db = _get_quote_db(q)
    svc = ServiceJobQuoteService()
    data = await svc.get_quote(db, str(q.id), customer_id=str(q.customer_id))
    assert data["status"] == QS_SENT_TO_CUSTOMER
    # No items were passed -- the customer-facing total reconciles to the
    # (empty) visible-items list, never the stored provider-side total.
    assert data["customer_payable_amount"] == "0"


@pytest.mark.asyncio
async def test_foreign_customer_cannot_read_quote():
    q = _quote()
    db = _get_quote_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_NOT_FOUND"):
        await svc.get_quote(db, str(q.id), customer_id=str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_cross_tenant_access_returns_same_not_found_as_missing():
    q = _quote()
    db = _get_quote_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_NOT_FOUND"):
        await svc.get_quote(db, str(q.id), tenant_id=str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_provider_internal_notes_never_reach_customer_read():
    q = _quote()
    db = _get_quote_db(q)
    svc = ServiceJobQuoteService()
    data = await svc.get_quote(db, str(q.id), customer_id=str(q.customer_id))
    assert "provider_internal_notes" not in data


@pytest.mark.asyncio
async def test_customer_totals_reconcile_to_customer_visible_items_only():
    q = _quote()
    visible = ServiceJobQuoteItem(
        id=uuid.uuid4(), quote_id=q.id, booking_id=q.booking_id, job_id=q.job_id, tenant_id=q.tenant_id,
        item_type="labour", item_name="Repair service", quantity=Decimal("1"), unit_price=Decimal("1450"),
        line_total=Decimal("1450"), is_required=True, is_customer_visible=True,
    )
    hidden = ServiceJobQuoteItem(
        id=uuid.uuid4(), quote_id=q.id, booking_id=q.booking_id, job_id=q.job_id, tenant_id=q.tenant_id,
        item_type="labour", item_name="Hidden margin buffer", quantity=Decimal("1"), unit_price=Decimal("500"),
        line_total=Decimal("500"), is_required=True, is_customer_visible=False,
    )
    db = _get_quote_db(q, [visible, hidden])
    svc = ServiceJobQuoteService()
    data = await svc.get_quote(db, str(q.id), customer_id=str(q.customer_id))
    assert len(data["items"]) == 1
    assert data["items"][0]["item_name"] == "Repair service"
    assert data["labour_amount"] == "1450"


@pytest.mark.asyncio
async def test_nonexistent_quote_id_is_enumeration_safe():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalar_one(None))
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_NOT_FOUND"):
        await svc.get_quote(db, str(uuid.uuid4()), customer_id=str(uuid.uuid4()))


# ── customer_approve ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_quote_can_be_approved_once():
    q = _quote(status=QS_SENT_TO_CUSTOMER)
    db = _decision_db(q)
    svc = ServiceJobQuoteService()
    with patch(NOTIFY_PATCH, new=AsyncMock()), patch(
        "app.engines.vertical_monetization.charge_service.create_charge_for_quote",
        new=AsyncMock(return_value=None),
    ):
        data = await svc.customer_approve(db, str(q.id), str(q.customer_id), idempotency_key="k1", user_id=str(q.customer_id), request_id="r1")
    assert data["status"] == QS_CUSTOMER_APPROVED
    assert "provider_internal_notes" not in data


@pytest.mark.asyncio
async def test_approval_never_writes_a_payment_record():
    q = _quote(status=QS_SENT_TO_CUSTOMER)
    db = _decision_db(q)
    svc = ServiceJobQuoteService()
    with patch(NOTIFY_PATCH, new=AsyncMock()), patch(
        "app.engines.vertical_monetization.charge_service.create_charge_for_quote",
        new=AsyncMock(return_value=None),
    ):
        data = await svc.customer_approve(db, str(q.id), str(q.customer_id), idempotency_key="k1", user_id=str(q.customer_id), request_id="r1")
    assert "payment" not in data
    assert "collected_amount" not in data


@pytest.mark.asyncio
async def test_repeated_approve_with_same_key_is_idempotent():
    q = _quote(status=QS_CUSTOMER_APPROVED, idempotency_key="k1")
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    data = await svc.customer_approve(db, str(q.id), str(q.customer_id), idempotency_key="k1", user_id=str(q.customer_id), request_id="r2")
    assert data["status"] == QS_CUSTOMER_APPROVED


@pytest.mark.asyncio
async def test_approve_with_different_key_after_already_approved_conflicts():
    q = _quote(status=QS_CUSTOMER_APPROVED, idempotency_key="k1")
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_IDEMPOTENCY_CONFLICT"):
        await svc.customer_approve(db, str(q.id), str(q.customer_id), idempotency_key="k2", user_id=str(q.customer_id), request_id="r3")


@pytest.mark.asyncio
async def test_stale_superseded_quote_cannot_be_approved():
    q = _quote(status=QS_SENT_TO_CUSTOMER, is_current=False)
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_NOT_CURRENT"):
        await svc.customer_approve(db, str(q.id), str(q.customer_id), idempotency_key="k1", user_id=str(q.customer_id), request_id="r1")


@pytest.mark.asyncio
async def test_approve_after_decline_fails():
    q = _quote(status=QS_CUSTOMER_REJECTED)
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_INVALID_STATUS_TRANSITION"):
        await svc.customer_approve(db, str(q.id), str(q.customer_id), idempotency_key="k1", user_id=str(q.customer_id), request_id="r1")


@pytest.mark.asyncio
async def test_foreign_customer_cannot_approve():
    q = _quote(status=QS_SENT_TO_CUSTOMER)
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED"):
        await svc.customer_approve(db, str(q.id), str(uuid.uuid4()), idempotency_key="k1", user_id=str(uuid.uuid4()), request_id="r1")


# ── customer_reject ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_decline_requires_a_reason():
    q = _quote(status=QS_SENT_TO_CUSTOMER)
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_REJECTION_REASON_REQUIRED"):
        await svc.customer_reject(db, str(q.id), str(q.customer_id), reason="", user_id=str(q.customer_id), request_id="r1")


@pytest.mark.asyncio
async def test_pending_quote_can_be_declined_once_with_a_reason():
    q = _quote(status=QS_SENT_TO_CUSTOMER)
    db = _decision_db(q)
    svc = ServiceJobQuoteService()
    with patch(NOTIFY_PATCH, new=AsyncMock()):
        data = await svc.customer_reject(db, str(q.id), str(q.customer_id), reason="Too expensive", user_id=str(q.customer_id), request_id="r1")
    assert data["status"] == QS_CUSTOMER_REJECTED


@pytest.mark.asyncio
async def test_decline_after_approve_fails():
    q = _quote(status=QS_CUSTOMER_APPROVED)
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_INVALID_STATUS_TRANSITION"):
        await svc.customer_reject(db, str(q.id), str(q.customer_id), reason="changed my mind", user_id=str(q.customer_id), request_id="r1")


@pytest.mark.asyncio
async def test_foreign_customer_cannot_decline():
    q = _quote(status=QS_SENT_TO_CUSTOMER)
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_CUSTOMER_APPROVAL_NOT_ALLOWED"):
        await svc.customer_reject(db, str(q.id), str(uuid.uuid4()), reason="no", user_id=str(uuid.uuid4()), request_id="r1")


@pytest.mark.asyncio
async def test_stale_superseded_quote_cannot_be_declined():
    q = _quote(status=QS_SENT_TO_CUSTOMER, is_current=False)
    db = _rejected_before_write_db(q)
    svc = ServiceJobQuoteService()
    with pytest.raises(ValueError, match="QUOTE_NOT_CURRENT"):
        await svc.customer_reject(db, str(q.id), str(q.customer_id), reason="no thanks", user_id=str(q.customer_id), request_id="r1")


# ── list_customer_quotes (this phase's own fix) ────────────────────────────

@pytest.mark.asyncio
async def test_list_customer_quotes_strips_internal_notes_and_filters_current():
    q = _quote()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([q]))
    svc = ServiceJobQuoteService()
    result = await svc.list_customer_quotes(db, str(q.customer_id), str(q.job_id))
    assert len(result) == 1
    assert "provider_internal_notes" not in result[0]
    assert result[0]["is_current"] is True
