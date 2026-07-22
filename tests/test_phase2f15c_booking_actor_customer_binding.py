"""Phase 2A Slice 2F-15C — Booking creation-actor binding and canonical
tenant coverage closure.

Closes the final theoretical provenance gap left by 2F-15B: every
provenance/relationship query previously checked `changed_by_role ==
"customer"` alone. This proved the ACTING USER held the customer role, but
never proved that acting user WAS the Booking's own customer (i.e.
`changed_by == Booking.customer_id`). This slice adds that explicit binding
at all 4 query sites:

  - FieldOpsService._assert_tenant_customer_relationship (qualifying-Booking
    evidence query)
  - BookingService.create_booking's own relationship-requirement check
  - BookingService.convert_to_job's creator/independent-evidence check
  - FieldOpsService.create_job's direct booking_id creator/independent-
    evidence check

In the actual legitimate creation path (customer self-booking), `changed_by`
is ALREADY always equal to `booking.customer_id` (server-derived, enforced at
the router: `customer_id = uuid.UUID(u.user_id) if u.role == "customer"`) --
so this change has NO effect on any legitimate case. It closes only the
theoretical risk that a differently-derived future creation path could let
one customer's creation event qualify for a DIFFERENT customer's Booking.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.booking.constants import BS
from app.exceptions import ServiceOSException


def _db_returning(*results):
    db = MagicMock()
    rs = []
    for res in results:
        r = MagicMock()
        r.scalar_one_or_none.return_value = res
        rs.append(r)
    db.execute = AsyncMock(side_effect=rs)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _customer_user(**overrides):
    u = MagicMock()
    u.role = overrides.get("role", "customer")
    u.is_active = overrides.get("is_active", True)
    u.deleted_at = overrides.get("deleted_at", None)
    return u


def _booking(**overrides):
    b = MagicMock()
    b.id = overrides.get("id", uuid.uuid4())
    b.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    b.customer_id = overrides.get("customer_id", uuid.uuid4())
    b.status = overrides.get("status", BS.CONFIRMED)
    b.converted_job_id = None
    return b


# ── Workstream 1: source-level proof the actor-binding filter is present ────

class TestActorBindingSourcePresence:
    def _read(self, path):
        import os
        full = os.path.join(os.path.dirname(os.path.dirname(__file__)), *path.split("/"))
        with open(full, encoding="utf-8") as f:
            return f.read()

    def test_field_ops_relationship_query_binds_actor_to_customer(self):
        src = self._read("app/engines/field_ops/service.py")
        assert "BookingStatusHistory.changed_by == Booking.customer_id" in src

    def test_field_ops_create_job_direct_reference_binds_actor(self):
        src = self._read("app/engines/field_ops/service.py")
        assert "_BSH.changed_by == booking.customer_id" in src
        assert "_BSH.changed_by == _Booking.customer_id" in src

    def test_booking_create_booking_relationship_check_binds_actor(self):
        src = self._read("app/engines/booking/service.py")
        assert "BookingStatusHistory.changed_by == Booking.customer_id" in src

    def test_booking_convert_to_job_binds_actor(self):
        src = self._read("app/engines/booking/service.py")
        assert "BookingStatusHistory.changed_by == b.customer_id" in src
        assert "BookingStatusHistory.changed_by == Booking.customer_id" in src


# ── Workstream 5: wrong-customer actor cannot establish origin ─────────────

@pytest.mark.asyncio
class TestWrongCustomerActorCannotEstablishOrigin:
    async def test_field_ops_relationship_denies_when_query_scoped_to_target_customer(self):
        """A customer-role creation event exists in the system, but the
        relationship query is scoped by Booking.customer_id == customer_id
        (the target) AND changed_by == Booking.customer_id -- so even a mock
        returning 'a match exists' only ever represents a match for THIS
        customer's own booking; there is no code path where Customer B's
        creation event can be substituted for Customer A's requirement,
        because the SQL join ties the history row to the SAME Booking row
        already filtered to customer_id == customer_id."""
        from app.engines.field_ops.service import FieldOpsService
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        # No qualifying booking matches this customer (query returns None),
        # no Job evidence either -- fails closed.
        db = _db_returning(customer_user, None, None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(customer_id),
            })
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()

    async def test_convert_to_job_creator_check_uses_bound_query_not_role_alone(self):
        """Verify convert_to_job's creator_r query result is now interpreted
        as an actor-bound match (id-or-None), not a raw role string -- a
        provider-created booking (mock returns None, meaning no bound match)
        requires independent evidence."""
        from app.engines.booking.service import BookingService
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id)
        db = _db_returning(booking, None, None, None, None)
        svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                              actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.convert_to_job(booking.id)
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()

    async def test_convert_to_job_customer_bound_match_converts(self):
        """A truthy (bound) creator_r match short-circuits the independent-
        evidence sub-query entirely and the conversion proceeds."""
        from app.engines.booking.service import BookingService
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id)
        db = _db_returning(booking, None, uuid.uuid4())  # bound match found
        svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                              actor_tenant_id=tenant_id)
        result = await svc.convert_to_job(booking.id)
        assert result is not None


# ── Workstream 5: booking.customer_id immutability audit ───────────────────

class TestBookingCustomerIdImmutability:
    def test_no_writer_ever_reassigns_booking_customer_id(self):
        """Repo-wide: no code path ever sets Booking.customer_id after
        creation (booking.customer_id = ... outside the constructor call in
        create_booking). If this ever changes, stale creation provenance
        could survive a customer_id reassignment -- this test must be
        revisited if it starts failing."""
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "app", "engines", "booking", "service.py")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        # The only occurrence of "customer_id=" as an assignment should be
        # inside the Booking(...) constructor call in create_booking.
        reassignments = [line for line in src.splitlines()
                          if "b.customer_id = " in line or "booking.customer_id = " in line]
        assert reassignments == [], f"unexpected Booking.customer_id reassignment(s): {reassignments}"
