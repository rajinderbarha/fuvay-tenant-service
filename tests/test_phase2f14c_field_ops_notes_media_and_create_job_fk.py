"""Phase 2A Slice 2F-14C — field_ops final mutation enforcement (add_note/
add_media) and create_job foreign-key/linked-record closure.

Findings and fixes:

1. **`add_note`/`add_media` had no router-level persona dependency at all**
   (`get_current_user` only) — the real object-ownership fix from Slice
   2F-14A (`_assert_can_access_job` + customer denial, service-side) was
   never tool-visible because nothing at the router named a persona/scope
   dependency. Fixed: both routes now require `require_staff_or_above_mutation`
   (excludes customer, denies read-only tenant access-scope) — the router
   establishes persona/scope, the unmodified service-level checks still
   establish object ownership. This closes `field_ops.router` to 28/28
   tool-verified routes.
2. **`create_job` accepted `service_type_id`, `parent_job_id`, `booking_id`,
   `customer_id` with no ownership validation** — a database FK existing (or
   not existing at all, since none of these are even DB-FK-constrained) is
   not sufficient; a valid record belonging to a DIFFERENT tenant (or a
   nonexistent/wrong-type reference) must still be rejected. Fixed:
   `service_type_id` is now always tenant-validated (and required active) via
   the existing `ServiceCatalogService`; `parent_job_id` and `booking_id` are
   validated for existence + tenant match against the (already server-pinned)
   tenant_id; `customer_id` is validated to reference an existing user with
   `role == "customer"`. No adapter between Job and ServiceJob/Booking was
   built — these are read-only ownership checks against existing models.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.field_ops.constants import JS
from app.engines.field_ops.service import FieldOpsService
from app.exceptions import ServiceOSException, NotFoundException


def _job(**overrides):
    j = MagicMock()
    j.id = overrides.get("id", uuid.uuid4())
    j.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    j.assigned_staff_id = overrides.get("assigned_staff_id", uuid.uuid4())
    j.customer_id = overrides.get("customer_id", uuid.uuid4())
    j.status = overrides.get("status", JS.ARRIVED)
    return j


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


# ── router-level source verification for add_note/add_media ─────────────────

class TestNoteMediaRouterGuardSources:
    def _read(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "app", "engines", "field_ops", "router.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_add_note_uses_staff_or_above_mutation(self):
        src = self._read()
        body = src.split("async def add_note(")[1].split("\n@router")[0]
        assert "require_staff_or_above_mutation" in body

    def test_add_media_uses_staff_or_above_mutation(self):
        src = self._read()
        body = src.split("async def add_media(")[1].split("\n@router")[0]
        assert "require_staff_or_above_mutation" in body


# ── add_note / add_media: unaffected object-ownership re-verification ───────

@pytest.mark.asyncio
class TestNoteMediaOwnershipStillEnforced:
    """Re-verifies the Slice 2F-14A service-level checks remain intact
    underneath the new router-level guard."""

    async def test_unassigned_technician_still_denied_add_note(self):
        job = _job(assigned_staff_id=uuid.uuid4())
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician")
        with pytest.raises(NotFoundException):
            await svc.add_note(job.id, "x", "staff_note", True)

    async def test_customer_still_denied_add_media(self):
        me = uuid.uuid4()
        job = _job(customer_id=me)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        with pytest.raises(ServiceOSException) as ei:
            await svc.add_media(job.id, None, "photo", None, None)
        assert ei.value.error_code == "MEDIA_ACCESS_DENIED"


# ── create_job FK/linked-record validation ───────────────────────────────────

@pytest.mark.asyncio
class TestCreateJobLinkedRecordOwnership:
    async def test_foreign_service_type_rejected(self):
        tenant_id = uuid.uuid4()
        db = _db_returning(None)  # ServiceCatalogItem lookup returns None
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {"title": "t", "service_type_id": "svc-1"})
        assert ei.value.error_code == "FOREIGN_SERVICE_TYPE"

    async def test_inactive_service_type_rejected(self):
        tenant_id = uuid.uuid4()
        inactive_cat = MagicMock(is_active=False)
        db = _db_returning(inactive_cat)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {"title": "t", "service_type_id": "svc-1"})
        assert ei.value.error_code == "INACTIVE_SERVICE_TYPE"

    async def test_foreign_parent_job_rejected(self):
        tenant_id = uuid.uuid4()
        foreign_parent = _job(tenant_id=uuid.uuid4())
        db = _db_returning(foreign_parent)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "parent_job_id": str(foreign_parent.id),
            })
        assert ei.value.error_code == "FOREIGN_PARENT_JOB"

    async def test_missing_parent_job_rejected(self):
        tenant_id = uuid.uuid4()
        db = _db_returning(None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "parent_job_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "FOREIGN_PARENT_JOB"

    async def test_foreign_booking_rejected(self):
        tenant_id = uuid.uuid4()
        foreign_booking = MagicMock(tenant_id=uuid.uuid4())
        db = _db_returning(foreign_booking)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "booking_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "FOREIGN_BOOKING"

    async def test_foreign_customer_rejected(self):
        tenant_id = uuid.uuid4()
        non_customer_user = MagicMock(role="tenant_owner")
        db = _db_returning(non_customer_user)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "customer_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "FOREIGN_CUSTOMER"

    async def test_missing_customer_rejected(self):
        tenant_id = uuid.uuid4()
        db = _db_returning(None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job(tenant_id, {
                "title": "t", "service_type_id": "",
                "customer_id": str(uuid.uuid4()),
            })
        assert ei.value.error_code == "FOREIGN_CUSTOMER"

    async def test_no_job_created_on_rejection(self):
        tenant_id = uuid.uuid4()
        db = _db_returning(None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException):
            await svc.create_job(tenant_id, {"title": "t", "service_type_id": "svc-1"})
        db.add.assert_not_called()
