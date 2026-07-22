"""Phase 2A Slice 2F-14F — manual customer authority and tenant relationship
closure for FieldOpsService.create_job.

Ratified secure interim policy: a tenant may manually create a field_ops.Job
for a customer only when a same-tenant relationship already exists (a
Booking-referenced or parent-Job-derived creation intrinsically proves this;
standalone manual creation requires an existing same-tenant Booking or Job
for that customer). A completely unrelated global customer, or one known only
to a DIFFERENT tenant, is rejected with a single uniform error that never
discloses which case applies or any other tenant's identity.

Also closes: deleted/deactivated customer accounts cannot be newly associated
with a Job (mirrors the existing staff.is_active check pattern already used
by Booking.convert_to_job).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.field_ops.service import FieldOpsService
from app.exceptions import ServiceOSException


def _customer_user(**overrides):
    u = MagicMock()
    u.role = overrides.get("role", "customer")
    u.is_active = overrides.get("is_active", True)
    u.deleted_at = overrides.get("deleted_at", None)
    return u


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


@pytest.mark.asyncio
class TestStandaloneManualCustomerAuthority:
    async def test_customer_with_prior_tenant_booking_succeeds(self):
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        prior_booking_id = uuid.uuid4()
        # customer lookup, then relationship query (Booking match found)
        db = _db_returning(customer_user, prior_booking_id)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "customer_id": str(customer_id),
        })
        assert result is not None

    async def test_customer_with_prior_tenant_job_succeeds(self):
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        # customer lookup, then relationship query: no Booking, but a Job match found
        db = _db_returning(customer_user, None, uuid.uuid4())
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "customer_id": str(customer_id),
        })
        assert result is not None

    async def test_completely_unrelated_customer_rejected(self):
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        # customer lookup, then relationship query: no Booking, no Job
        db = _db_returning(customer_user, None, None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(customer_id),
            })
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()

    async def test_customer_known_only_to_another_tenant_rejected_same_error(self):
        """Same uniform error as 'completely unrelated' -- the relationship
        query is scoped to THIS tenant, so a customer with a booking/job only
        under a different tenant produces identical, non-disclosing results."""
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        db = _db_returning(customer_user, None, None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(customer_id),
            })
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"

    async def test_wrong_role_user_rejected_before_relationship_check(self):
        tenant_id = uuid.uuid4()
        non_customer_user = _customer_user(role="tenant_owner")
        db = _db_returning(non_customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "FOREIGN_CUSTOMER"
        db.add.assert_not_called()

    async def test_deactivated_customer_rejected(self):
        tenant_id = uuid.uuid4()
        customer_user = _customer_user(is_active=False)
        db = _db_returning(customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "FOREIGN_CUSTOMER"
        db.add.assert_not_called()

    async def test_deleted_customer_rejected(self):
        import datetime
        tenant_id = uuid.uuid4()
        customer_user = _customer_user(deleted_at=datetime.datetime(2025, 1, 1))
        db = _db_returning(customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "FOREIGN_CUSTOMER"
        db.add.assert_not_called()

    async def test_no_customer_id_does_not_trigger_relationship_check(self):
        """Standalone creation with no customer_id at all is unaffected --
        the relationship guard only runs when customer_id is supplied."""
        tenant_id = uuid.uuid4()
        db = _db_returning()
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {"title": "t", "service_type_id": ""})
        assert result is not None


@pytest.mark.asyncio
class TestBookingParentModesUnaffectedByRelationshipGuard:
    """Booking-referenced and parent-Job-derived creation intrinsically prove
    the relationship -- no extra relationship query should ever run for them."""

    async def test_booking_referenced_creation_does_not_query_relationship(self):
        from app.engines.booking.constants import BS
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        booking = MagicMock(tenant_id=tenant_id, customer_id=customer_id,
                             service_type_id="ac_repair", converted_job_id=None, status=BS.CONFIRMED)
        catalog_item = MagicMock(is_active=True)
        customer_user = _customer_user()
        # Exactly: catalog lookup, booking lookup, no existing job for
        # booking, creation-actor check ("customer" -- skips the Slice
        # 2F-15A independent-relationship-evidence sub-query), customer
        # lookup. If an unexpected extra query ran, this would raise
        # StopAsyncIteration.
        db = _db_returning(catalog_item, booking, None, "customer", customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "ac_repair",
            "booking_id": str(uuid.uuid4()), "customer_id": str(customer_id),
        })
        assert result is not None

    async def test_parent_derived_creation_does_not_query_relationship(self):
        from app.engines.field_ops.constants import JobType, JS
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        parent = MagicMock(tenant_id=tenant_id, customer_id=customer_id,
                            job_type=JobType.REPAIR, status=JS.CLOSED)
        customer_user = _customer_user()
        # Exactly: parent lookup, customer lookup. No relationship query.
        db = _db_returning(parent, customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "job_type": JobType.SERVICE,
            "parent_job_id": str(uuid.uuid4()), "customer_id": str(customer_id),
        })
        assert result is not None
