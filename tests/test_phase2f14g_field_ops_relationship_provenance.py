"""Phase 2A Slice 2F-14G — tenant-customer relationship provenance and
legacy-row closure for FieldOpsService._assert_tenant_customer_relationship.

Findings and fixes:

1. **Booking status trust.** `BookingService.create_booking` lets a
   `tenant_owner` supply an arbitrary client-side `customer_id` with no
   existence/ownership validation at all (confirmed via source audit) --
   a malicious tenant_owner could "self-mint" qualifying relationship
   evidence for a real, unrelated customer by creating a throwaway Booking
   naming them, which previously (Slice 2F-14F) qualified regardless of
   status. Fixed: only Booking statuses that are UNREACHABLE except by first
   passing through `BS.CONFIRMED` now qualify (`confirmed`, `scheduled`,
   `dispatching`, `in_progress`, `completed`, `converted_to_job`).
   `draft`/`pending`/`pending_confirmation`/`rejected`/`expired`/`cancelled`/
   `voided` no longer qualify (`cancelled`/`voided` are excluded too, since
   the transition graph allows reaching them from a non-confirmed state as
   well, so current status alone cannot prove prior confirmation).
2. **Legacy Job-row trust.** A "generic" standalone Job (both `booking_id`
   and `parent_job_id` null) carries no field distinguishing a
   post-hardening, already-validated standalone creation from an arbitrary
   pre-hardening row. Fixed: only Job rows with a non-null `booking_id` or
   `parent_job_id` now qualify as relationship evidence -- these are
   structurally derived from an already-validated Booking or parent Job and
   carry that trust forward; excluding generic Jobs does not break any
   legitimately-established relationship, since a legitimately-created
   generic Job could only have been created because OTHER qualifying
   evidence already existed at that time.

Residual, disclosed risk (NOT fixed this slice, out of scope): a
`tenant_owner` can still create a Booking naming an arbitrary real customer
AND unilaterally confirm it themselves (`confirm_booking` requires no
customer participation) -- reaching a now-qualifying status without genuine
customer contact. Closing this would require modifying
`BookingService.create_booking`/`confirm_booking` in the booking engine,
outside this slice's scope (confined to the `create_job` relationship
helper). See known-limitations.md.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.booking.constants import BS
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
class TestBookingBootstrapRejected:
    @pytest.mark.parametrize("status", [
        BS.DRAFT, BS.PENDING_CONFIRMATION, BS.PENDING, BS.REJECTED,
        BS.EXPIRED, BS.CANCELLED, BS.VOIDED,
    ])
    async def test_low_trust_booking_does_not_establish_relationship(self, status):
        """Bootstrap attack: tenant creates a low-trust Booking for an
        unrelated customer, then attempts standalone create_job for them."""
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        # customer lookup succeeds, but the relationship queries (booking
        # status-filtered, then job booking_id/parent_job_id-filtered) find
        # nothing qualifying -- simulated by returning None for both, since
        # the SQL-level status/null filter would exclude the low-trust row
        # even if one exists in the "real" table.
        db = _db_returning(customer_user, None, None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(customer_id),
            })
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"
        db.add.assert_not_called()

    @pytest.mark.parametrize("status", [
        BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS,
        BS.COMPLETED, BS.CONVERTED_TO_JOB,
    ])
    async def test_qualifying_booking_status_establishes_relationship(self, status):
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


@pytest.mark.asyncio
class TestLegacyJobRowTrust:
    async def test_generic_standalone_job_does_not_qualify(self):
        """A Job with neither booking_id nor parent_job_id (a 'generic' row --
        indistinguishable pre/post hardening) must not establish relationship
        evidence on its own."""
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        # No qualifying booking; the Job query (which SQL-filters on
        # booking_id/parent_job_id not null) also finds nothing, even though
        # a generic Job row might exist in the real table.
        db = _db_returning(customer_user, None, None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "customer_id": str(customer_id),
            })
        assert ei.value.error_code == "CUSTOMER_TENANT_RELATIONSHIP_REQUIRED"

    async def test_booking_derived_job_qualifies(self):
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        customer_user = _customer_user()
        qualifying_job_id = uuid.uuid4()
        db = _db_returning(customer_user, None, qualifying_job_id)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "customer_id": str(customer_id),
        })
        assert result is not None


class TestRelationshipQuerySourceVerification:
    """Source-level proof that the SQL filters were actually added (not just
    behaviorally coincidental) -- confirms the query construction itself."""

    def _read(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "app", "engines", "field_ops", "service.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_booking_query_filters_by_qualifying_status(self):
        src = self._read()
        body = src.split("async def _assert_tenant_customer_relationship")[1].split(
            "\n    async def ")[0]
        assert "QUALIFYING_BOOKING_STATUSES" in body
        assert "Booking.status.in_(QUALIFYING_BOOKING_STATUSES)" in body

    def test_job_query_filters_by_booking_or_parent_lineage(self):
        src = self._read()
        body = src.split("async def _assert_tenant_customer_relationship")[1].split(
            "\n    async def ")[0]
        assert "Job.booking_id.isnot(None)" in body
        assert "Job.parent_job_id.isnot(None)" in body
