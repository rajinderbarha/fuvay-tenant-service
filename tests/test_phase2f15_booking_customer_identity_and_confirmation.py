"""Phase 2A Slice 2F-15 — Booking customer identity, assisted-booking and
confirmation-provenance closure.

Findings and fixes:

1. **`create_booking`'s tenant-assisted path accepted an arbitrary
   client-supplied `customer_id` with ZERO existence validation.** A
   `tenant_owner` could name any UUID (real or fabricated) as the customer.
   Fixed: when the acting persona is not `customer` (i.e. the assisted-booking
   override), `customer_id` must now resolve to a real, active, non-deleted
   `customer`-role account -- mirrors `FieldOpsService.create_job`'s own
   validation pattern (Slice 2F-14C).
2. **Assisted-booking creation had no relationship requirement at all** --
   this was the exact residual vulnerability disclosed in Slice 2F-14G: a
   `tenant_owner` could fabricate a Booking naming an unrelated real customer,
   confirm it themselves, and use it as `field_ops` relationship evidence.
   Fixed: assisted-booking creation (non-customer actor) now requires an
   existing same-tenant relationship for that customer -- a confirmed-or-later
   Booking, or a source-derived `field_ops.Job` -- reusing the exact
   qualifying rule `FieldOpsService._assert_tenant_customer_relationship`
   already applies (Slice 2F-14G). Customer self-booking is unaffected --
   it is the legitimate "first contact" path this policy exists to preserve.
3. **`create_booking`/`confirm_booking`/`reject_booking`/`convert_to_job`
   router guards were `require_permission`, not access-scope-aware.** Upgraded
   to `require_tenant_mutation_permission` -- the same fix pattern already
   established across the field_ops series (Slices 2F-14/14A/14B).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.booking.constants import BS
from app.exceptions import ServiceOSException


def _customer_user(**overrides):
    u = MagicMock()
    u.role = overrides.get("role", "customer")
    u.is_active = overrides.get("is_active", True)
    u.deleted_at = overrides.get("deleted_at", None)
    return u


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


def _svc(db, actor_role="tenant_owner", actor_tenant_id=None):
    from app.engines.booking.service import BookingService
    return BookingService(db=db, actor_id=uuid.uuid4(), actor_role=actor_role,
                           actor_tenant_id=actor_tenant_id or uuid.uuid4())


# ── customer existence validation (assisted booking) ─────────────────────────

@pytest.mark.asyncio
class TestAssistedBookingCustomerValidation:
    async def test_foreign_customer_rejected(self):
        db = _db_returning(None)  # User lookup returns None
        svc = _svc(db)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_booking(customer_id=uuid.uuid4(), address_id=uuid.uuid4(),
                                      service_id=uuid.uuid4(), job_type="repair")
        assert ei.value.error_code == "FOREIGN_CUSTOMER"
        db.add.assert_not_called()

    async def test_wrong_role_account_rejected(self):
        db = _db_returning(_customer_user(role="tenant_owner"))
        svc = _svc(db)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_booking(customer_id=uuid.uuid4(), address_id=uuid.uuid4(),
                                      service_id=uuid.uuid4(), job_type="repair")
        assert ei.value.error_code == "FOREIGN_CUSTOMER"
        db.add.assert_not_called()

    async def test_disabled_customer_rejected(self):
        db = _db_returning(_customer_user(is_active=False))
        svc = _svc(db)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_booking(customer_id=uuid.uuid4(), address_id=uuid.uuid4(),
                                      service_id=uuid.uuid4(), job_type="repair")
        assert ei.value.error_code == "FOREIGN_CUSTOMER"

    async def test_deleted_customer_rejected(self):
        import datetime
        db = _db_returning(_customer_user(deleted_at=datetime.datetime(2025, 1, 1)))
        svc = _svc(db)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_booking(customer_id=uuid.uuid4(), address_id=uuid.uuid4(),
                                      service_id=uuid.uuid4(), job_type="repair")
        assert ei.value.error_code == "FOREIGN_CUSTOMER"

    async def test_customer_self_booking_skips_validation_entirely(self):
        """Customer self-booking never reaches the User-lookup/relationship
        check at all -- customer_id is already server-derived."""
        db = MagicMock()
        db.execute = AsyncMock(side_effect=AssertionError("db.execute should not be called"))
        from app.engines.booking.service import BookingService
        svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
        with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
            mi = AsyncMock()
            mi._resolve_service_type_id = AsyncMock(side_effect=ServiceOSException("X", "x"))
            MockSvc.return_value = mi
            with pytest.raises(ServiceOSException) as ei:
                await svc.create_booking(customer_id=uuid.uuid4(), address_id=uuid.uuid4(),
                                          service_id=uuid.uuid4(), job_type="repair")
        # Fails downstream (service resolution), never at the customer-validation
        # gate -- proving that gate was never reached/triggered for self-booking.
        assert ei.value.error_code == "SERVICE_NOT_FOUND"


# ── tenant/customer relationship requirement (bootstrap closure) ────────────

@pytest.mark.asyncio
class TestAssistedBookingRelationshipRequirement:
    async def _run_with_matched_tenant(self, db, svc, matched_tenant_id):
        matches = [{"tenant_id": str(matched_tenant_id), "matched_area_id": str(uuid.uuid4()),
                    "service_area_service_id": str(uuid.uuid4()), "coverage_match_level": "exact",
                    "estimated_sla_minutes": 60, "base_price": 500}]
        with patch("app.engines.serviceability.service.ServiceabilityService") as MockSvc:
            mi = AsyncMock()
            mi._resolve_service_type_id = AsyncMock(return_value=("ac_service", "AC", "hvac"))
            mi._resolve_location_full = AsyncMock(
                return_value=("Mumbai", "MH", "400001", None, None, uuid.uuid4()))
            mi.match_tenants_for_location = AsyncMock(return_value=matches)
            MockSvc.return_value = mi
            return await svc.create_booking(customer_id=uuid.uuid4(), address_id=uuid.uuid4(),
                                             service_id=uuid.uuid4(), job_type="repair")

    async def test_bootstrap_attack_no_relationship_rejected(self):
        """The exact Slice 2F-14G disclosed exploit: tenant_owner creates a
        Booking for a completely unrelated real customer -- customer exists
        and is valid, but no same-tenant Booking/Job relationship exists."""
        matched_tenant_id = uuid.uuid4()
        customer_user = _customer_user()
        # customer lookup succeeds; relationship queries (booking, then job) both find nothing
        db = _db_returning(customer_user, None, None)
        svc = _svc(db, actor_tenant_id=matched_tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await self._run_with_matched_tenant(db, svc, matched_tenant_id)
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()

    async def test_assisted_booking_with_existing_relationship_succeeds(self):
        matched_tenant_id = uuid.uuid4()
        customer_user = _customer_user()
        qualifying_booking_id = uuid.uuid4()
        db = _db_returning(customer_user, qualifying_booking_id)
        svc = _svc(db, actor_tenant_id=matched_tenant_id)
        with patch("app.engines.booking.service.BookingService._run_legacy_preflight",
                   new_callable=AsyncMock) as mock_preflight, \
             patch("app.engines.booking.service.BookingService._publish", new_callable=AsyncMock), \
             patch("app.engines.booking.service.BookingService._write_history", new_callable=AsyncMock):
            mock_preflight.return_value = {"passed": True, "blocking_check": None,
                                            "blocking_reason": None, "allowed_transitions": []}
            svc.redis = AsyncMock()
            svc.redis.get = AsyncMock(return_value=None)
            svc.redis.setex = AsyncMock()
            result = await self._run_with_matched_tenant(db, svc, matched_tenant_id)
        assert result is not None
        assert str(result["tenant_id"]) == str(matched_tenant_id)


# ── router guard source verification ─────────────────────────────────────────

class TestBookingRouterGuardSources:
    def _read(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "app", "engines", "booking", "router.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_create_booking_uses_tenant_mutation_permission(self):
        src = self._read()
        body = src.split("async def create_booking(")[1].split("\n@router")[0]
        assert "require_tenant_mutation_permission" in body

    def test_confirm_reject_convert_use_tenant_mutation_permission(self):
        src = self._read()
        for fn in ("confirm_booking", "reject_booking", "convert_to_job"):
            body = src.split(f"async def {fn}(")[1].split("\n@router")[0]
            assert "require_tenant_mutation_permission" in body, fn
