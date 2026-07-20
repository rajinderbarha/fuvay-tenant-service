"""Phase 2A Slice 2F-14B — field_ops creation, conversion and quote
authorization closure.

Findings and fixes:

1. **`create_job` accepted a client-supplied `tenant_id` with no check against
   the actor's own tenant.** Any tenant_owner/staff/technician could create a
   Job under a different tenant_id. Fixed: `tenant_id` is now pinned to
   `actor_tenant_id` for tenant-scoped roles; router guard upgraded to
   `require_tenant_mutation_permission`.
2. **`convert_to_repair`'s router guard was permission-only, not access-scope
   aware** (object ownership via `_get_job_for_assignment` was already
   correct). Upgraded to `require_tenant_mutation_permission`.
3. **`spawn_repair_from_consultation` had NO ownership check at all** (a
   cross-tenant IDOR) **and no duplicate-repair guard** (repeated calls could
   create unlimited duplicate repair jobs). Fixed by reusing
   `_get_job_for_assignment` and mirroring `convert_to_repair`'s existing
   duplicate-repair check.
4. **`create_quote` had NO ownership check at all** (any authenticated user
   could quote any job in any tenant). Fixed by reusing
   `_get_job_for_quote_management`.
5. **`_get_job_for_quote_management` never denied `actor_role == "customer"`**
   — a customer could administer (create/send) a provider-authored quote on
   any job. Fixed with an explicit customer denial.
6. **`respond_to_quote` was a customer-impersonation defect** — any
   non-customer authenticated caller could supply an arbitrary `customer_id`
   in the request body and have the service record an approve/reject decision
   indistinguishable from a genuine customer response. Fixed: the route now
   requires `require_customer`; `customer_id` is always derived from the
   authenticated principal, never the request body.
7. **`approve_job_quote`/`reject_job_quote`'s inline customer-only checks**
   were tool-invisible; converted to the named `require_customer` dependency
   for consistency (identical policy).
8. **`create_job_quote`/`send_job_quote`/`create_quote` had zero router-level
   persona dependency** (`get_current_user` only) — upgraded to
   `require_staff_or_above` (excludes customer) for tool-visible
   defense-in-depth in front of the (now-hardened) service-level ownership
   check.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.service import FieldOpsService
from app.exceptions import ServiceOSException, NotFoundException


def _job(**overrides):
    j = MagicMock()
    j.id = overrides.get("id", uuid.uuid4())
    j.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    j.assigned_staff_id = overrides.get("assigned_staff_id", uuid.uuid4())
    j.customer_id = overrides.get("customer_id", uuid.uuid4())
    j.status = overrides.get("status", JS.ARRIVED)
    j.job_type = overrides.get("job_type", JobType.REPAIR)
    j.parent_job_id = overrides.get("parent_job_id", None)
    return j


def _quote(**overrides):
    q = MagicMock()
    q.id = overrides.get("id", uuid.uuid4())
    q.job_id = overrides.get("job_id", uuid.uuid4())
    q.customer_id = overrides.get("customer_id", uuid.uuid4())
    q.status = overrides.get("status", "pending")
    q.expires_at = overrides.get("expires_at", None)
    return q


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


# ── create_job tenant_id override ────────────────────────────────────────────

@pytest.mark.asyncio
class TestCreateJobTenantPinning:
    async def test_tenant_owner_cannot_override_tenant_id(self):
        principal_tenant = uuid.uuid4()
        foreign_tenant = uuid.uuid4()
        db = _db_returning()
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=principal_tenant)
        result = await svc.create_job(foreign_tenant, {
            "title": "t", "service_type_id": "",
        })
        added_job = db.add.call_args[0][0]
        assert str(added_job.tenant_id) == str(principal_tenant)

    async def test_super_admin_tenant_id_not_overridden(self):
        explicit_tenant = uuid.uuid4()
        db = _db_returning()
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin",
                               actor_tenant_id=None)
        await svc.create_job(explicit_tenant, {"title": "t", "service_type_id": ""})
        added_job = db.add.call_args[0][0]
        assert str(added_job.tenant_id) == str(explicit_tenant)


# ── spawn_repair ownership + duplicate guard ─────────────────────────────────

@pytest.mark.asyncio
class TestSpawnRepairOwnership:
    async def test_cross_tenant_owner_denied(self):
        job = _job(tenant_id=uuid.uuid4(), job_type=JobType.CONSULTATION)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as ei:
            await svc.spawn_repair_from_consultation(job.id)
        assert ei.value.error_code == "JOB_NOT_FOUND"

    async def test_duplicate_spawn_rejected(self):
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, job_type=JobType.CONSULTATION)
        existing_repair = MagicMock()
        db = _db_returning(job, existing_repair)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.spawn_repair_from_consultation(job.id)
        assert ei.value.error_code == "CONSULTATION_ALREADY_CONVERTED"

    async def test_wrong_job_type_rejected(self):
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, job_type=JobType.REPAIR)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.spawn_repair_from_consultation(job.id)
        assert ei.value.error_code == "INVALID_JOB_TYPE"


# ── create_quote ownership ───────────────────────────────────────────────────

@pytest.mark.asyncio
class TestCreateQuoteOwnership:
    async def test_foreign_job_rejected(self):
        db = _db_returning(None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_quote(uuid.uuid4(), Decimal("100"), [], None, None)
        assert ei.value.error_code == "JOB_NOT_FOUND"

    async def test_cross_tenant_owner_denied(self):
        job = _job(tenant_id=uuid.uuid4(), status=JS.ASSESSMENT_COMPLETE)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=uuid.uuid4())
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_quote(job.id, Decimal("100"), [], None, None)
        assert ei.value.error_code == "JOB_NOT_FOUND"

    async def test_unassigned_technician_denied(self):
        job = _job(assigned_staff_id=uuid.uuid4(), status=JS.ASSESSMENT_COMPLETE)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="technician",
                               actor_tenant_id=job.tenant_id)
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_quote(job.id, Decimal("100"), [], None, None)
        assert ei.value.error_code == "STAFF_NOT_ASSIGNED_TO_JOB"


# ── quote administration denies customer ─────────────────────────────────────

@pytest.mark.asyncio
class TestQuoteManagementDeniesCustomer:
    async def test_customer_denied_create_job_quote(self):
        me = uuid.uuid4()
        job = _job(customer_id=me, status=JS.ASSESSMENT_COMPLETE)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_job_quote(job.id, {"recommended_work": "x"})
        assert ei.value.error_code == "QUOTE_ACCESS_DENIED"

    async def test_customer_denied_create_quote(self):
        me = uuid.uuid4()
        job = _job(customer_id=me, status=JS.ASSESSMENT_COMPLETE)
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        with pytest.raises(ServiceOSException) as ei:
            await svc.create_quote(job.id, Decimal("100"), [], None, None)
        assert ei.value.error_code == "QUOTE_ACCESS_DENIED"

    async def test_tenant_owner_can_create_job_quote(self):
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, status=JS.ASSESSMENT_COMPLETE)
        job.recommended_work = "existing findings"
        job.assessment_findings = None
        job.findings = None
        job.recommendation = None
        job.pre_approval_limit = None
        db = _db_returning(job)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                               actor_tenant_id=tenant_id)
        result = await svc.create_job_quote(job.id, {})
        assert result is not None


# ── respond_to_quote: no impersonation possible ──────────────────────────────

@pytest.mark.asyncio
class TestRespondToQuoteIdentity:
    async def test_correct_customer_can_respond(self):
        me = uuid.uuid4()
        quote = _quote(customer_id=me, status="pending")
        job = _job(id=quote.job_id, job_type=JobType.REPAIR, status=JS.QUOTE_PENDING)
        db = _db_returning(quote, job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        result = await svc.respond_to_quote(quote.id, me, True)
        assert quote.status == "approved"

    async def test_foreign_customer_denied(self):
        real_customer = uuid.uuid4()
        wrong_customer = uuid.uuid4()
        quote = _quote(customer_id=real_customer, status="pending")
        db = _db_returning(quote)
        svc = FieldOpsService(db=db, actor_id=wrong_customer, actor_role="customer")
        with pytest.raises(NotFoundException):
            await svc.respond_to_quote(quote.id, wrong_customer, True)
        assert quote.status == "pending"  # unchanged

    async def test_repeated_response_rejected(self):
        me = uuid.uuid4()
        quote = _quote(customer_id=me, status="approved")
        db = _db_returning(quote)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="customer")
        with pytest.raises(ServiceOSException) as ei:
            await svc.respond_to_quote(quote.id, me, True)
        assert ei.value.error_code == "CONFLICT"

    async def test_foreign_quote_id_rejected(self):
        db = _db_returning(None)
        svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="customer")
        with pytest.raises(NotFoundException):
            await svc.respond_to_quote(uuid.uuid4(), uuid.uuid4(), True)


# ── source-level guard verification ──────────────────────────────────────────

class TestRouterGuardSources:
    def _read(self):
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "app", "engines", "field_ops", "router.py")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_create_job_uses_tenant_mutation_permission(self):
        src = self._read()
        body = src.split('@router.post("", summary="Create job from booking"')[1].split("\n@router")[0]
        assert "require_tenant_mutation_permission" in body

    def test_convert_to_repair_uses_tenant_mutation_permission(self):
        src = self._read()
        body = src.split("async def convert_to_repair")[1].split("\n@router")[0]
        assert "require_tenant_mutation_permission" in body

    def test_spawn_repair_uses_tenant_mutation_permission(self):
        src = self._read()
        body = src.split("async def spawn_repair(")[1].split("\n@router")[0]
        assert "require_tenant_mutation_permission" in body

    def test_respond_to_quote_uses_require_customer(self):
        src = self._read()
        body = src.split("async def respond_to_quote")[1].split("\n@router")[0]
        assert "require_customer" in body
        assert 'body["customer_id"]' not in body

    def test_quote_admin_routes_use_require_staff_or_above(self):
        src = self._read()
        for fn in ("create_job_quote", "send_job_quote", "create_quote"):
            body = src.split(f"async def {fn}(")[1].split("\n@router")[0]
            assert "require_staff_or_above_mutation" in body, fn

    def test_approve_reject_quote_use_require_customer(self):
        src = self._read()
        for fn in ("approve_job_quote", "reject_job_quote"):
            body = src.split(f"async def {fn}(")[1].split("\n@router")[0]
            assert "require_customer" in body, fn
