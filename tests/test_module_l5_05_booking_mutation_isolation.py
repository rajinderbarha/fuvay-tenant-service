"""MODULE-L5-05 — booking MUTATION cross-tenant isolation.

request/accept/reject_reschedule, add_note, and void_booking previously loaded a
booking by id and mutated it with NO tenant/customer scope check (a tenant_owner
could mutate another tenant's booking; add_note was auth-only so ANY user could).
All now route through _assert_can_access_booking. Also enforced by
e2e/cross_tenant_isolation_guard.py's booking-mutation-coverage check.
"""
import uuid
from unittest.mock import MagicMock

import pytest

from app.engines.booking.service import BookingService
from app.exceptions import NotFoundException
import e2e.cross_tenant_isolation_guard as guard


def _staff_at(tenant_id):
    svc = BookingService(db=MagicMock(), actor_id=uuid.uuid4(), actor_role="staff",
                         actor_tenant_id=tenant_id)
    return svc


def test_add_note_blocks_cross_tenant():
    """add_note (endpoint is auth-only) must still confine to the booking's tenant."""
    svc = _staff_at(uuid.uuid4())
    b = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=uuid.uuid4())  # different tenant
    with pytest.raises(NotFoundException):
        svc._assert_can_access_booking(b)


def test_add_note_allows_own_tenant():
    tid = uuid.uuid4()
    svc = _staff_at(tid)
    b = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=tid)
    svc._assert_can_access_booking(b)  # no raise


def test_tenant_owner_cannot_mutate_other_tenant_booking():
    a, b_tenant = uuid.uuid4(), uuid.uuid4()
    svc = BookingService(db=MagicMock(), actor_id=uuid.uuid4(), actor_role="tenant_owner",
                         actor_tenant_id=a)
    booking = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=b_tenant)
    with pytest.raises(NotFoundException):
        svc._assert_can_access_booking(booking)


def test_guard_enforces_booking_mutation_coverage():
    assert guard.check() == []
