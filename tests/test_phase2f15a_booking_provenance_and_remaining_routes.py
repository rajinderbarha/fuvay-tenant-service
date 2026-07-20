"""Phase 2A Slice 2F-15A — remaining Booking mutation enforcement and legacy
provenance closure.

Findings and fixes:

1. **`add_note`, `cancel_booking`, `request_reschedule`, `accept_reschedule`,
   `reject_reschedule` router guards were unprotected/access-scope-unaware.**
   `add_note` had zero persona dependency (`get_current_user` only, despite
   the pre-existing `_assert_can_access_booking` service-level check already
   being correct) -- fixed with `require_staff_or_above_mutation` (no live
   customer-note caller exists; matches the field_ops add_note precedent).
   `cancel_booking`/`request_reschedule` legitimately support BOTH customer
   and tenant_owner (confirmed via `ROLE_PERMISSIONS`) -- fixed with
   `require_tenant_mutation_permission` (admits both, denies read-only tenant
   scope, does not affect customer accounts). `accept_reschedule`/
   `reject_reschedule` are tenant-only -- same fix.
2. **`booking_preflight` reclassified as a mutation-method FALSE_POSITIVE** --
   confirmed zero `db.add`/`db.commit` calls anywhere in
   `run_booking_preflight`; added to the runtime tool's existing
   `CONFIRMED_FALSE_POSITIVE_ROUTES` exemption set. `booking.router` now
   verifies at 0/0 unverified (exit 0).
3. **`_assert_tenant_customer_relationship` (field_ops) and
   `create_booking`'s own relationship check both tightened**: a
   qualifying-status Booking is no longer sufficient by itself -- it must
   also be CUSTOMER-originated (its creation-history row's
   `changed_by_role == "customer"`, read from the existing, unmodified
   `BookingStatusHistory` table). Provider-created Bookings can no longer
   directly establish relationship authority, closing the legacy-row risk
   Slice 2F-15 could not fully resolve (a chain of provider-created
   assisted bookings bootstrapping each other, or a pre-fix legacy
   provider-created Booking with no genuine customer participation).
4. **`Booking.convert_to_job`** now requires INDEPENDENT prior relationship
   evidence (excluding the Booking being converted) when that Booking was
   provider-created -- closing the "confirm a legacy/fabricated Booking, then
   convert it" path.
5. **Direct `field_ops.create_job` with `booking_id`** now applies the
   identical independent-evidence requirement for provider-created Bookings
   -- closing the same risk via the generic `create_job` endpoint, which
   would otherwise bypass `convert_to_job`'s new protection entirely.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.booking.constants import BS
from app.engines.field_ops.constants import JobType
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


# ── field_ops relationship predicate now requires customer-originated Booking ─

@pytest.mark.asyncio
class TestFieldOpsRelationshipRequiresCustomerProvenance:
    async def test_provider_created_qualifying_booking_no_longer_qualifies(self):
        from app.engines.field_ops.service import FieldOpsService
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        # customer lookup succeeds; the JOIN-based booking query finds no
        # customer-originated qualifying row (query itself filters this out
        # at the SQL level -- simulated here by returning None); no
        # source-derived Job either.
        db = _db_returning(customer_user, None, None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(customer_id),
            })
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()

    async def test_customer_created_qualifying_booking_still_qualifies(self):
        from app.engines.field_ops.service import FieldOpsService
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        qualifying_booking_id = uuid.uuid4()
        db = _db_returning(customer_user, qualifying_booking_id)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "customer_id": str(customer_id),
        })
        assert result is not None


# ── create_booking's own relationship check requires customer provenance ────

@pytest.mark.asyncio
class TestCreateBookingRequiresCustomerProvenance:
    async def test_chain_of_provider_created_bookings_cannot_bootstrap(self):
        """A provider-created booking cannot be used as evidence to create
        ANOTHER assisted booking -- the query itself excludes non-customer-
        originated rows."""
        from app.engines.booking.service import BookingService
        from unittest.mock import patch
        tenant_id = uuid.uuid4()
        customer_user = _customer_user()
        db = _db_returning(customer_user, None, None)
        svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                              actor_tenant_id=tenant_id)
        matches = [{"tenant_id": str(tenant_id), "matched_area_id": str(uuid.uuid4()),
                    "service_area_service_id": str(uuid.uuid4()), "coverage_match_level": "exact",
                    "estimated_sla_minutes": 60, "base_price": 500}]
        with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
            mi = AsyncMock()
            mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC", "hvac"))
            mi._resolve_location_full = AsyncMock(
                return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
            mi.match_tenants_for_location = AsyncMock(return_value=matches)
            MockSvc.return_value = mi
            with pytest.raises(ServiceOSException) as ei:
                await svc.create_booking(customer_id=uuid.uuid4(), address_id=uuid.uuid4(),
                                          service_id=uuid.uuid4(), job_type="repair")
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()


# ── Booking.convert_to_job independent-relationship-proof ───────────────────

@pytest.mark.asyncio
class TestConvertToJobIndependentProof:
    async def _booking(self, **overrides):
        b = MagicMock()
        b.id = overrides.get("id", uuid.uuid4())
        b.tenant_id = overrides.get("tenant_id", uuid.uuid4())
        b.customer_id = overrides.get("customer_id", uuid.uuid4())
        b.status = overrides.get("status", BS.CONFIRMED)
        b.converted_job_id = None
        return b

    async def test_provider_created_booking_without_independent_evidence_rejected(self):
        from app.engines.booking.service import BookingService
        tenant_id = uuid.uuid4()
        booking = await self._booking(tenant_id=tenant_id)
        # Slice 2F-15C: creator_r's query now returns an id-or-None (actor
        # bound to booking.customer_id) rather than a raw role string --
        # None means "not customer-originated" here.
        db = _db_returning(booking, None, None, None, None)
        svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                              actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.convert_to_job(booking.id)
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()

    async def test_customer_created_booking_converts_normally(self):
        from app.engines.booking.service import BookingService
        tenant_id = uuid.uuid4()
        booking = await self._booking(tenant_id=tenant_id)
        db = _db_returning(booking, None, "customer")
        svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                              actor_tenant_id=tenant_id)
        # A customer-originated booking passes the provenance gate outright
        # (no independent-evidence sub-query even executes) and conversion
        # proceeds to completion.
        result = await svc.convert_to_job(booking.id)
        assert result is not None

    async def test_provider_created_booking_with_independent_evidence_passes_gate(self):
        from app.engines.booking.service import BookingService
        tenant_id = uuid.uuid4()
        booking = await self._booking(tenant_id=tenant_id)
        independent_booking_id = uuid.uuid4()
        db = _db_returning(booking, None, None, independent_booking_id)
        svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                              actor_tenant_id=tenant_id)
        try:
            await svc.convert_to_job(booking.id)
        except ServiceOSException as e:
            assert e.error_code != "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"


# ── router guard source verification ─────────────────────────────────────────

class TestRemainingBookingRouterGuardSources:
    def _read(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "app", "engines", "booking", "router.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_add_note_uses_staff_or_above_mutation(self):
        src = self._read()
        body = src.split("async def add_note(")[1].split("\n@router")[0]
        assert "require_staff_or_above_mutation" in body

    def test_cancel_and_reschedule_use_tenant_mutation_permission(self):
        src = self._read()
        for fn in ("cancel_booking", "request_reschedule", "accept_reschedule", "reject_reschedule"):
            body = src.split(f"async def {fn}(")[1].split("\n@router")[0]
            assert "require_tenant_mutation_permission" in body, fn
