"""Phase 2A Slice 2F-14D — create_job relational consistency closure.

Slice 2F-14C validated customer_id/booking_id/parent_job_id/service_type_id
INDIVIDUALLY (existence + tenant ownership). It never proved these fields were
MUTUALLY CONSISTENT as one coherent Job creation request. This slice closes
that gap:

1. **booking_id is customer- and service-authoritative.** If `customer_id`/
   `service_type_id` are also explicitly supplied alongside a `booking_id`,
   they must match the booking's own `customer_id`/`service_type_id` --
   otherwise the created Job would claim a booking reference while showing
   different customer/service data, silently misleading any downstream
   consumer (billing, notifications, audit) that trusts `job.booking_id` to
   correlate with the real booking.
2. **booking_id duplicate-conversion guard.** `Booking.convert_to_job` (the
   canonical, atomic booking-conversion pipeline, in the booking engine, NOT
   modified this slice) already blocks converting an already-converted
   booking. `field_ops.router`'s own separate, generic `create_job` endpoint
   had no equivalent guard -- a caller could create a second Job referencing
   an already-converted booking. Fixed by mirroring the same
   `converted_job_id`/existing-Job-by-booking_id checks.
3. **parent_job_id is customer-authoritative** (service type is NOT
   cross-checked -- `convert_to_repair`'s own established policy already
   treats a differing repair service_type as legitimate, not a defect).
4. **parent_job_id duplicate-repair guard for CONSULTATION parents.**
   `convert_to_repair`/`spawn_repair` both already block creating a second
   repair job from the same consultation. `create_job`'s own separate,
   generic endpoint had no equivalent guard -- a caller holding create_job's
   own mutation-scope-aware permission could bypass that established
   uniqueness rule entirely by POSTing a REPAIR job directly with
   `parent_job_id` set to an already-converted consultation. Fixed by
   mirroring the identical guard.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.service import FieldOpsService
from app.exceptions import ServiceOSException


def _job(**overrides):
    j = MagicMock()
    j.id = overrides.get("id", uuid.uuid4())
    j.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    j.customer_id = overrides.get("customer_id", uuid.uuid4())
    j.job_type = overrides.get("job_type", JobType.REPAIR)
    # Slice 2F-14E: CONSULTATION parents now also need QUOTE_APPROVED status
    # to be eligible as a repair source (mirrors convert_to_repair's policy).
    j.status = overrides.get("status", JS.QUOTE_APPROVED)
    return j


def _booking(**overrides):
    from app.engines.booking.constants import BS
    b = MagicMock()
    b.id = overrides.get("id", uuid.uuid4())
    b.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    b.customer_id = overrides.get("customer_id", uuid.uuid4())
    b.service_type_id = overrides.get("service_type_id", "ac_repair")
    b.converted_job_id = overrides.get("converted_job_id", None)
    # Slice 2F-14E: bookings now also need BS.CONFIRMED status to be
    # eligible as a job source (mirrors Booking.convert_to_job's policy).
    b.status = overrides.get("status", BS.CONFIRMED)
    return b


def _db_returning(*results):
    import datetime
    db = MagicMock()
    rs = []
    for res in results:
        r = MagicMock()
        r.scalar_one_or_none.return_value = res
        rs.append(r)
    db.execute = AsyncMock(side_effect=rs)

    def _add(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.datetime(2026, 1, 1)
    db.add = MagicMock(side_effect=_add)
    db.flush = AsyncMock()
    return db


# ── booking relational consistency ───────────────────────────────────────────

@pytest.mark.asyncio
class TestBookingRelationalConsistency:
    async def test_matching_booking_customer_service_succeeds(self):
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id, customer_id=customer_id, service_type_id="ac_repair")
        catalog_item = MagicMock(is_active=True)
        customer_user = MagicMock(role="customer", is_active=True, deleted_at=None)
        # Slice 2F-15A: create_job now also checks the booking's own creation
        # actor (BookingStatusHistory.changed_by_role) before using it -- "customer"
        # skips the independent-relationship-evidence sub-query entirely.
        db = _db_returning(catalog_item, booking, None, "customer", customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "ac_repair",
            "booking_id": str(booking.id), "customer_id": str(customer_id),
        })
        assert result is not None

    async def test_customer_booking_mismatch_rejected(self):
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id, customer_id=uuid.uuid4())
        db = _db_returning(booking)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "booking_id": str(booking.id), "customer_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "CUSTOMER_BOOKING_MISMATCH"

    async def test_service_booking_mismatch_rejected(self):
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id, service_type_id="ac_repair")
        catalog_item = MagicMock(is_active=True)
        db = _db_returning(catalog_item, booking)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "different_service",
                "booking_id": str(booking.id),
            })
        assert ei.value.error_code == "SERVICE_BOOKING_MISMATCH"

    async def test_already_converted_booking_rejected(self):
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id, converted_job_id=uuid.uuid4())
        db = _db_returning(booking)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "booking_id": str(booking.id),
            })
        assert ei.value.error_code == "JOB_ALREADY_EXISTS_FOR_BOOKING"

    async def test_duplicate_job_for_booking_rejected(self):
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id)
        existing_job = MagicMock()
        db = _db_returning(booking, existing_job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "booking_id": str(booking.id),
            })
        assert ei.value.error_code == "JOB_ALREADY_EXISTS_FOR_BOOKING"


# ── parent job relational consistency ────────────────────────────────────────

@pytest.mark.asyncio
class TestParentJobRelationalConsistency:
    async def test_matching_parent_customer_succeeds(self):
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, customer_id=customer_id, job_type=JobType.REPAIR)
        customer_user = MagicMock(role="customer", is_active=True, deleted_at=None)
        db = _db_returning(parent, customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "",
            "parent_job_id": str(parent.id), "customer_id": str(customer_id),
        })
        assert result is not None

    async def test_customer_parent_mismatch_rejected(self):
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, customer_id=uuid.uuid4(), job_type=JobType.REPAIR)
        db = _db_returning(parent)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "parent_job_id": str(parent.id), "customer_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "CUSTOMER_PARENT_JOB_MISMATCH"

    async def test_duplicate_repair_from_consultation_rejected(self):
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, job_type=JobType.CONSULTATION)
        existing_repair = MagicMock()
        db = _db_returning(parent, existing_repair)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "job_type": JobType.REPAIR,
                "parent_job_id": str(parent.id),
            })
        assert ei.value.error_code == "CONSULTATION_ALREADY_CONVERTED"

    async def test_different_repair_service_from_consultation_allowed(self):
        """Service type MAY legitimately differ between a consultation and its
        spawned repair -- convert_to_repair's own established policy, not a
        defect. No SERVICE_PARENT_MISMATCH error exists for this reason."""
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, job_type=JobType.CONSULTATION)
        catalog_item = MagicMock(is_active=True)
        db = _db_returning(catalog_item, parent, None)  # catalog, parent, no existing repair
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "a_totally_different_service",
            "job_type": JobType.REPAIR, "parent_job_id": str(parent.id),
        })
        assert result is not None

    async def test_second_non_repair_child_from_same_parent_allowed(self):
        """Non-consultation-to-repair parent/child relationships are not
        restricted to one child -- MULTIPLE_CHILDREN_ALLOWED by policy (see
        duplicate-idempotency-policy.md); only the specific
        CONSULTATION->REPAIR uniqueness rule is enforced."""
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, job_type=JobType.REPAIR)
        db = _db_returning(parent)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "job_type": JobType.SERVICE,
            "parent_job_id": str(parent.id),
        })
        assert result is not None
