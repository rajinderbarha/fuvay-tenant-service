"""Help & Support Hub phase.

Covers the one real backend fix made this phase: `CustomerComplaint.
to_customer_dict()` (`app/engines/complaints/models.py`) leaked
`assigned_admin_user_id` -- the internal admin's user id -- to the
customer app; only `internal_admin_notes` was ever stripped. No DB
session is needed since this is a pure in-memory model-method check.
"""
import uuid

from app.engines.complaints.models import CustomerComplaint


def _complaint(**overrides) -> CustomerComplaint:
    c = CustomerComplaint(
        customer_id=uuid.uuid4(), tenant_id=uuid.uuid4(), category_id=uuid.uuid4(),
        record_type="service_booking", record_id=uuid.uuid4(),
        complaint_type="service_quality", description="test", status="open", priority="normal",
    )
    c.id = uuid.uuid4()
    c.complaint_number = "CMP-TEST-1"
    c.assigned_admin_user_id = uuid.uuid4()
    c.internal_admin_notes = "internal reviewer note"
    for k, v in overrides.items():
        setattr(c, k, v)
    return c


def test_to_customer_dict_strips_assigned_admin_user_id():
    d = _complaint().to_customer_dict()
    assert "assigned_admin_user_id" not in d


def test_to_customer_dict_strips_internal_admin_notes():
    d = _complaint().to_customer_dict()
    assert "internal_admin_notes" not in d


def test_to_customer_dict_still_includes_customer_safe_fields():
    d = _complaint().to_customer_dict()
    for field in ("id", "complaint_number", "status", "complaint_type", "description",
                  "record_type", "record_id", "created_at"):
        assert field in d


def test_to_dict_itself_still_computes_assigned_admin_user_id():
    """Confirms the fix is a customer-view allowlist change, not a removal
    of the underlying admin-facing field (admin_router.py's own responses
    still need it)."""
    d = _complaint().to_dict()
    assert "assigned_admin_user_id" in d
    assert d["assigned_admin_user_id"] is not None


def test_to_provider_dict_unaffected_by_this_fix():
    """The provider view was never leaking assigned_admin_user_id in scope
    for this phase -- confirms the fix is scoped to the customer view only,
    not a broader behavior change."""
    d = _complaint().to_provider_dict()
    assert "internal_admin_notes" not in d
