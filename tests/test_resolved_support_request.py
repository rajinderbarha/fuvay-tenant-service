"""Resolved Support Request and Customer Feedback phase.

Proves the two contract claims the frontend phase relies on:
  1. A `resolved` complaint still accepts customer messages (only
     closed/cancelled/rejected are truly read-only) -- confirms the
     frontend's divergence from the mockup's "always read-only when
     resolved" assumption is correct, not a guess.
  2. `to_customer_dict()` exposes the real customer-visible resolution
     fields (`customer_visible_summary`, `resolved_at`, `closed_at`)
     while still excluding internal-only fields.
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.constants import STATUS_RESOLVED, STATUS_CLOSED
from app.engines.complaints.models import CustomerComplaint


def _uuid():
    return uuid.uuid4()


def _mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_add_customer_message_allowed_when_resolved():
    """`resolved` is deliberately NOT in FINAL_STATUSES -- the customer can
    still message a resolved request. The details screen relies on this
    exact behavior to keep the composer visible for `resolved` instead of
    marking it read-only, per the real backend contract rather than the
    mockup's assumption."""
    svc = ComplaintService()
    db = _mock_db()
    uid = _uuid()
    c = MagicMock(customer_id=uid, status=STATUS_RESOLVED, tenant_id=_uuid())
    with patch.object(svc, "get_customer_complaint", AsyncMock(return_value=c)):
        with patch.object(svc, "_log_event", AsyncMock()):
            msg = await svc.add_customer_message(db, uid, _uuid(), "Thanks for the help")
    db.add.assert_called_once()
    assert msg.message_text == "Thanks for the help"


def test_to_customer_dict_exposes_resolution_fields_and_excludes_internal_ones():
    now = datetime.now(timezone.utc)
    c = CustomerComplaint(
        id=_uuid(), customer_id=_uuid(), category_id=_uuid(),
        record_type="service_booking", record_id=_uuid(),
        complaint_type="service_quality", status=STATUS_RESOLVED,
        description="Provider arrived late",
        customer_visible_summary="Your booking remains active.",
        resolved_at=now, closed_at=None,
    )
    d = c.to_customer_dict()

    # Customer-visible resolution contract this phase depends on.
    assert d["customer_visible_summary"] == "Your booking remains active."
    assert d["resolved_at"] == now.isoformat()
    assert d["closed_at"] is None

    # Never leak internal-only fields to the customer adapter.
    assert "internal_admin_notes" not in d
    assert "assigned_admin_user_id" not in d


def test_to_customer_dict_closed_state_exposes_closed_at():
    now = datetime.now(timezone.utc)
    c = CustomerComplaint(
        id=_uuid(), customer_id=_uuid(), category_id=_uuid(),
        record_type="service_booking", record_id=_uuid(),
        complaint_type="service_quality", status=STATUS_CLOSED,
        description="desc", closed_at=now,
    )
    d = c.to_customer_dict()
    assert d["closed_at"] == now.isoformat()
    assert d["status"] == STATUS_CLOSED
