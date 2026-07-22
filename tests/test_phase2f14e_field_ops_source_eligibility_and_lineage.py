"""Phase 2A Slice 2F-14E — create_job Booking/parent source eligibility and
booking/parent-lineage coexistence closure.

Findings and fixes:

1. **Booking status eligibility.** `booking_id`'s existing customer/service
   cross-check and duplicate-conversion guard (Slice 2F-14D) make it an
   AUTHORITATIVE_LINEAGE_REFERENCE, not merely informational -- so the same
   source-state prerequisite `Booking.convert_to_job` already enforces
   (`BS.CONFIRMED`) is now enforced here too. A draft/pending/cancelled/
   rejected/expired/voided/already-converted booking can no longer be
   referenced by `create_job`.
2. **Parent Job status eligibility (CONSULTATION -> REPAIR only).** Where
   `create_job` with a CONSULTATION parent + REPAIR job_type is semantically
   equivalent to `convert_to_repair`'s own dedicated capability, the identical
   source-state prerequisite (`JS.QUOTE_APPROVED`) is now enforced -- mirroring
   convert_to_repair's established policy, not inventing a new one. No status
   gate is imposed on other parent/child job_type combinations.
3. **booking_id + parent_job_id coexistence.** No safe combined semantics for
   supplying both fields at once have ever been established anywhere in this
   codebase. Simultaneous use is now rejected before persistence
   (`AMBIGUOUS_JOB_SOURCE`, 422).
4. **Manual customer authority** was investigated (Workstream 5/6) and found
   to have NO established tenant/customer relationship model or rule anywhere
   in this codebase (no CRM, directory, invitation system). Requiring a prior
   Booking/Job relationship would be circular -- it would make it impossible
   to ever create the FIRST manual job for a legitimately new customer, since
   no other customer-onboarding path exists in this codebase. This is recorded
   as PRODUCT_DECISION_REQUIRED (see manual-customer-authority.md), not fixed
   with an invented relationship rule. Final status reflects this as a
   customer-authority product-policy block, not a security gap.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.booking.constants import BS
from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.service import FieldOpsService
from app.exceptions import ServiceOSException


def _job(**overrides):
    j = MagicMock()
    j.id = overrides.get("id", uuid.uuid4())
    j.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    j.customer_id = overrides.get("customer_id", uuid.uuid4())
    j.job_type = overrides.get("job_type", JobType.CONSULTATION)
    j.status = overrides.get("status", JS.QUOTE_APPROVED)
    return j


def _booking(**overrides):
    b = MagicMock()
    b.id = overrides.get("id", uuid.uuid4())
    b.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    b.customer_id = overrides.get("customer_id", uuid.uuid4())
    b.service_type_id = overrides.get("service_type_id", "ac_repair")
    b.converted_job_id = overrides.get("converted_job_id", None)
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


# ── Booking status eligibility ───────────────────────────────────────────────

@pytest.mark.asyncio
class TestBookingStatusEligibility:
    @pytest.mark.parametrize("status", [
        BS.DRAFT, BS.PENDING_CONFIRMATION, BS.PENDING, BS.REJECTED,
        BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS, BS.COMPLETED,
        BS.CANCELLED, BS.EXPIRED, BS.VOIDED, BS.CONVERTED_TO_JOB,
    ])
    async def test_non_confirmed_booking_rejected(self, status):
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id, status=status)
        db = _db_returning(booking)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "booking_id": str(booking.id),
            })
        assert ei.value.error_code == "BOOKING_INVALID_STATUS_TRANSITION"
        db.add.assert_not_called()

    async def test_confirmed_booking_accepted(self):
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id, status=BS.CONFIRMED)
        db = _db_returning(booking, None, "customer")  # booking lookup, no existing job, creation actor
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "booking_id": str(booking.id),
        })
        assert result is not None


# ── Parent job status eligibility (CONSULTATION -> REPAIR only) ─────────────

@pytest.mark.asyncio
class TestParentStatusEligibility:
    @pytest.mark.parametrize("status", [
        JS.DRAFT, JS.PENDING_ASSIGNMENT, JS.ASSIGNED, JS.ARRIVED,
        JS.ASSESSMENT_STARTED, JS.ASSESSMENT_COMPLETE, JS.QUOTE_PENDING,
        JS.QUOTE_REJECTED, JS.CANCELLED, JS.VOIDED, JS.CLOSED, JS.COMPLETED,
    ])
    async def test_non_quote_approved_consultation_rejected_as_repair_source(self, status):
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, job_type=JobType.CONSULTATION, status=status)
        db = _db_returning(parent)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "", "job_type": JobType.REPAIR,
                "parent_job_id": str(parent.id),
            })
        assert ei.value.error_code == "CONSULTATION_CONVERSION_NOT_ALLOWED"
        db.add.assert_not_called()

    async def test_quote_approved_consultation_accepted_as_repair_source(self):
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, job_type=JobType.CONSULTATION, status=JS.QUOTE_APPROVED)
        db = _db_returning(parent, None)  # parent lookup, no existing repair
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "job_type": JobType.REPAIR,
            "parent_job_id": str(parent.id),
        })
        assert result is not None

    async def test_non_consultation_parent_status_not_gated(self):
        """No status eligibility rule exists for non-CONSULTATION parents --
        MULTIPLE_CHILDREN_ALLOWED / no gate, per evidenced policy only."""
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, job_type=JobType.REPAIR, status=JS.CLOSED)
        db = _db_returning(parent)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "job_type": JobType.SERVICE,
            "parent_job_id": str(parent.id),
        })
        assert result is not None


# ── booking_id + parent_job_id coexistence ───────────────────────────────────

@pytest.mark.asyncio
class TestBookingParentCoexistence:
    async def test_both_supplied_rejected(self):
        tenant_id = uuid.uuid4()
        db = _db_returning()
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "booking_id": str(uuid.uuid4()), "parent_job_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "AMBIGUOUS_JOB_SOURCE"
        db.add.assert_not_called()

    async def test_booking_only_unaffected(self):
        tenant_id = uuid.uuid4()
        booking = _booking(tenant_id=tenant_id)
        db = _db_returning(booking, None, "customer")
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "booking_id": str(booking.id),
        })
        assert result is not None

    async def test_parent_only_unaffected(self):
        tenant_id = uuid.uuid4()
        parent = _job(tenant_id=tenant_id, job_type=JobType.REPAIR)
        db = _db_returning(parent)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job(tenant_id, {
            "title": "t", "service_type_id": "", "parent_job_id": str(parent.id),
        })
        assert result is not None


# ── source-level guard verification (route-security regression) ─────────────

class TestRouteSecurityRegression:
    def test_create_job_still_uses_tenant_mutation_permission(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "app", "engines", "field_ops", "router.py")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        body = src.split('@router.post("", summary="Create job from booking"')[1].split("\n@router")[0]
        assert "require_tenant_mutation_permission" in body
