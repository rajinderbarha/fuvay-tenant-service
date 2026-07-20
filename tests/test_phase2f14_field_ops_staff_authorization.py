"""Phase 2A Slice 2F-14 — field_ops.staff_router authorization, job
assignment, checklist execution and completion-gate closure.

Findings and fixes:

1. **`field_ops.staff_router`'s persona check was invisible to runtime
   guard-status verification.** All 6 mutations (`accept`, `reject-
   assignment`, `status`, `checklist/start`, `checklist/items/{id}`,
   `checklist/complete`) were correctly gated by an inline
   `if u.role not in ("staff", "technician")` check inside the shared
   `_svc` dependency factory -- a real, working guard, but embedded in a
   function body rather than a named `require_*` dependency, so the
   runtime mutation-inventory tool (which introspects dependency NAMES)
   reported all 6 as `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK`. Fixed by
   extracting the identical policy into a new, named
   `require_staff_or_technician_only` dependency
   (`app/dependencies/auth.py`) -- same behavior, now tool-visible.

2. **`app.engines.field_ops.router` (the tenant/provider-side `/v1/jobs`
   surface, 28 endpoints) has a directly-connected, same-record,
   same-capability alternate for 7 of staff_router's 6 mutations**
   (`accept_job`, `reject_assignment`, `start_checklist`,
   `update_checklist_item`, `complete_checklist`, the legacy
   `update_checklist`, and `submit_findings`) -- these call the IDENTICAL
   `FieldOpsService` methods as staff_router's aliases, on the same `Job`/
   `JobChecklistItem` records, but previously had **zero role check at
   all** (`get_current_user` only) -- weaker than staff_router's own
   inline check. Fixed with the same new `require_staff_or_technician_only`
   dependency (the established, existing in-file pattern already used by
   `accept_job`/`reject_assignment` in this same file, just not yet
   applied to the other 5).

3. **`update_status`/`assign_job` in `field_ops.router` were
   `PERMISSION_ONLY_NOT_SCOPE_AWARE`** (no tenant read-only-scope
   enforcement) -- fixed by swapping `require_permission` →
   `require_tenant_mutation_permission` (same permission, same role
   bundle, now scope-aware) -- the identical fix pattern established in
   Slice 2F-13 for `checklist_router`.

4. **`update_job_checklist_item` had no state guard at all** -- a
   technician could mutate a checklist item (including un-completing a
   required item) after `complete_job_checklist` had already moved the
   job to `CHECKLIST_COMPLETE` (or the job had progressed further),
   silently invalidating an already-finalized checklist with no
   re-validation of the completion gate. Fixed by requiring
   `job.status == JS.CHECKLIST_STARTED` before any item mutation --
   mirrors `complete_job_checklist`'s own existing precondition, not a
   new gate.

Object-layer ownership (`_get_job_for_staff_action`'s exact
`assigned_staff_id` match, `_assert_assigned`/`_assert_can_access_job`'s
tenant/customer/assignment scoping) was ALREADY correct and is
unmodified -- these fixes are persona-layer (who may even attempt the
call) and one state-integrity fix, sitting in front of/alongside the
pre-existing, correct object checks.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.engines.field_ops.constants import JS, JobType
from app.engines.field_ops.service import FieldOpsService
from app.exceptions import ServiceOSException, NotFoundException


def _user(role: str, user_id: str | None = None, tenant_id: str | None = None,
          access_scope: str | None = None) -> UserContext:
    return UserContext(
        user_id=user_id or str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id or str(uuid.uuid4()), full_name=role.title(), is_verified=True,
        access_scope=access_scope,
    )


def _override(u):
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


JOB_ID = "11111111-1111-1111-1111-111111111111"
ITEM_ID = "22222222-2222-2222-2222-222222222222"

STAFF_ROUTER_MUTATIONS = [
    ("POST", f"/v1/staff/me/jobs/{JOB_ID}/accept", {}),
    ("POST", f"/v1/staff/me/jobs/{JOB_ID}/reject-assignment", {"reason": "x"}),
    ("PUT", f"/v1/staff/me/jobs/{JOB_ID}/status", {"to_status": "accepted"}),
    ("POST", f"/v1/staff/me/jobs/{JOB_ID}/checklist/start", {}),
    ("PUT", f"/v1/staff/me/jobs/{JOB_ID}/checklist/items/{ITEM_ID}", {"is_completed": True}),
    ("POST", f"/v1/staff/me/jobs/{JOB_ID}/checklist/complete", {}),
]

FIELD_OPS_ROUTER_ALTERNATES = [
    ("POST", f"/v1/jobs/{JOB_ID}/accept", {}),
    ("POST", f"/v1/jobs/{JOB_ID}/reject-assignment", {"reason": "x"}),
    ("POST", f"/v1/jobs/{JOB_ID}/checklist/start", {}),
    ("PUT", f"/v1/jobs/{JOB_ID}/checklist/items/{ITEM_ID}", {"is_completed": True}),
    ("POST", f"/v1/jobs/{JOB_ID}/checklist/complete", {}),
    ("PUT", f"/v1/jobs/{JOB_ID}/checklist", {"items": []}),
    ("POST", f"/v1/jobs/{JOB_ID}/findings", {"findings": "x"}),
]


@pytest.mark.asyncio
class TestStaffRouterRoleGate:
    async def test_unauthenticated_denied(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for method, path, body in STAFF_ROUTER_MUTATIONS:
                resp = await client.request(method, path, json=body)
                assert resp.status_code in (401, 403), f"{method} {path}"

    @pytest.mark.parametrize("role", ["customer", "guest", "tenant_owner", "totally_bogus_role"])
    async def test_denied_role_rejected(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in STAFF_ROUTER_MUTATIONS:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()

    @pytest.mark.parametrize("role", ["staff", "technician"])
    async def test_staff_and_technician_clear_role_gate(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/v1/staff/me/jobs/{JOB_ID}/accept")
                body = resp.json()
                code = (body.get("error") or {}).get("code") or body.get("error_code")
                assert code not in ("STAFF_ACCESS_DENIED", "PERMISSION_DENIED"), (role, body)
        finally:
            _clear()


@pytest.mark.asyncio
class TestFieldOpsRouterAlternateRouteGate:
    """The directly-connected, same-record, same-capability alternate
    surface (`/v1/jobs/*`) -- previously weaker (no role check at all)
    than staff_router's own aliases, now matched."""

    async def test_unauthenticated_denied(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for method, path, body in FIELD_OPS_ROUTER_ALTERNATES:
                resp = await client.request(method, path, json=body)
                assert resp.status_code in (401, 403), f"{method} {path}"

    @pytest.mark.parametrize("role", ["customer", "guest", "totally_bogus_role"])
    async def test_denied_role_rejected_on_every_alternate(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in FIELD_OPS_ROUTER_ALTERNATES:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()

    async def test_tenant_owner_denied_from_execution_alternates(self):
        """tenant_owner is legitimately business-wide for assign/status
        (separate, permission-gated routes) but NOT for these
        staff/technician execution aliases -- matches staff_router's own
        persona boundary."""
        _override(_user("tenant_owner"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in FIELD_OPS_ROUTER_ALTERNATES:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"tenant_owner {method} {path}"
        finally:
            _clear()

    @pytest.mark.parametrize("role", ["staff", "technician"])
    async def test_staff_and_technician_clear_role_gate(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/v1/jobs/{JOB_ID}/accept")
                body = resp.json()
                code = (body.get("error") or {}).get("code") or body.get("error_code")
                assert code not in ("STAFF_ACCESS_DENIED", "PERMISSION_DENIED"), (role, body)
        finally:
            _clear()


@pytest.mark.asyncio
class TestUpdateStatusAndAssignAccessScope:
    """The 2F-13-style access-scope fix for update_status/assign_job."""

    async def test_readonly_tenant_owner_denied_update_status(self):
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(f"/v1/jobs/{JOB_ID}/status", json={"to_status": "accepted"})
                assert resp.status_code == 403
                body = resp.json()
                code = (body.get("error") or {}).get("code") or body.get("error_code")
                assert code == "PERMISSION_DENIED"
        finally:
            _clear()

    async def test_readonly_tenant_owner_denied_assign(self):
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/v1/jobs/{JOB_ID}/assign", json={"staff_id": str(uuid.uuid4())})
                assert resp.status_code == 403
        finally:
            _clear()

    async def test_full_scope_tenant_owner_clears_update_status_gate(self):
        _override(_user("tenant_owner"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(f"/v1/jobs/{JOB_ID}/status", json={"to_status": "accepted"})
                body = resp.json()
                code = (body.get("error") or {}).get("code") or body.get("error_code")
                assert code != "PERMISSION_DENIED", body
        finally:
            _clear()


# ── Direct unit test of the new named dependency ─────────────────────────────

class TestRequireStaffOrTechnicianOnlyGuard:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("role,allowed", [
        ("staff", True), ("technician", True),
        ("tenant_owner", False), ("super_admin", False),
        ("customer", False), ("guest", False), ("totally_bogus_role", False),
    ])
    async def test_role_admission(self, role, allowed):
        from app.dependencies.auth import require_staff_or_technician_only
        u = _user(role)
        if allowed:
            result = await require_staff_or_technician_only(u)
            assert result is u
        else:
            with pytest.raises(ServiceOSException):
                await require_staff_or_technician_only(u)


# ── Service-layer: object ownership re-verification (unmodified, pre-existing) ─

@pytest.mark.asyncio
class TestAssignmentOwnershipReVerified:
    """Re-verifies the pre-existing, unmodified object-ownership checks
    this slice's persona fixes sit in front of."""

    def _job(self, status="assigned", assigned_staff_id=None, tenant_id=None):
        j = MagicMock()
        j.id = uuid.uuid4()
        j.tenant_id = tenant_id or uuid.uuid4()
        j.assigned_staff_id = assigned_staff_id or uuid.uuid4()
        j.status = status
        j.customer_id = uuid.uuid4()
        return j

    def _db(self, job):
        db = MagicMock()
        r = MagicMock(); r.scalar_one_or_none.return_value = job
        db.execute = AsyncMock(return_value=r)
        db.add = MagicMock(); db.flush = AsyncMock()
        return db

    async def test_wrong_technician_denied_accept(self):
        real_staff = uuid.uuid4()
        wrong_staff = uuid.uuid4()
        job = self._job(status="assigned", assigned_staff_id=real_staff)
        db = self._db(job)
        svc = FieldOpsService(db=db, actor_id=wrong_staff, actor_role="technician")
        with pytest.raises(ServiceOSException) as ei:
            await svc.accept_job(job.id)
        assert ei.value.error_code == "STAFF_NOT_ASSIGNED_TO_JOB"
        assert job.status == "assigned"  # unchanged

    async def test_assigned_technician_allowed_accept(self):
        me = uuid.uuid4()
        job = self._job(status="assigned", assigned_staff_id=me)
        db = self._db(job)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        result = await svc.accept_job(job.id)
        assert job.status == JS.ACCEPTED


# ── Completion-gate integrity: the new state guard on item mutation ──────────

@pytest.mark.asyncio
class TestChecklistItemCompletionGateIntegrity:
    def _job(self, status, staff_id):
        j = MagicMock()
        j.id = uuid.uuid4()
        j.tenant_id = uuid.uuid4()
        j.assigned_staff_id = staff_id
        j.status = status
        return j

    def _item(self, job_id, **overrides):
        i = MagicMock()
        i.id = uuid.uuid4()
        i.job_id = job_id
        i.is_required = overrides.get("is_required", True)
        i.requires_note = overrides.get("requires_note", False)
        i.requires_photo = overrides.get("requires_photo", False)
        i.is_completed = overrides.get("is_completed", False)
        return i

    def _db(self, job, item):
        job_r = MagicMock(); job_r.scalar_one_or_none.return_value = job
        item_r = MagicMock(); item_r.scalar_one_or_none.return_value = item
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[job_r, item_r])
        return db

    async def test_cannot_mutate_item_after_checklist_complete(self):
        """The fixed defect: mutating an item once the checklist has
        already been finalized (CHECKLIST_COMPLETE) must be rejected."""
        me = uuid.uuid4()
        job = self._job(JS.CHECKLIST_COMPLETE, me)
        item = self._item(job.id, is_completed=True)
        db = self._db(job, item)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        with pytest.raises(ServiceOSException) as ei:
            await svc.update_job_checklist_item(job.id, item.id, False)
        assert ei.value.error_code == "CHECKLIST_NOT_ACTIVE"
        assert item.is_completed is True  # unchanged

    async def test_cannot_mutate_item_after_job_moved_past_checklist(self):
        me = uuid.uuid4()
        job = self._job(JS.WORK_COMPLETE, me)
        item = self._item(job.id, is_completed=True)
        db = self._db(job, item)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        with pytest.raises(ServiceOSException) as ei:
            await svc.update_job_checklist_item(job.id, item.id, False)
        assert ei.value.error_code == "CHECKLIST_NOT_ACTIVE"

    async def test_mutation_allowed_while_checklist_started(self):
        me = uuid.uuid4()
        job = self._job(JS.CHECKLIST_STARTED, me)
        item = self._item(job.id, is_completed=False, is_required=False)
        db = self._db(job, item)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        result = await svc.update_job_checklist_item(job.id, item.id, True)
        assert item.is_completed is True

    async def test_foreign_job_item_rejected(self):
        """Item belongs to a different job -- rejected regardless of
        checklist state."""
        me = uuid.uuid4()
        job = self._job(JS.CHECKLIST_STARTED, me)
        item = self._item(uuid.uuid4())  # different job_id
        db = self._db(job, item)
        svc = FieldOpsService(db=db, actor_id=me, actor_role="technician")
        with pytest.raises(ServiceOSException) as ei:
            await svc.update_job_checklist_item(job.id, item.id, True)
        assert ei.value.error_code == "CHECKLIST_ITEM_NOT_FOUND"


class TestSourceGuards:
    def test_staff_router_uses_named_dependency(self):
        import inspect
        from app.engines.field_ops import staff_router as sr
        src = inspect.getsource(sr)
        assert "require_staff_or_technician_only" in src
        assert 'if u.role not in ("staff", "technician")' not in src

    def test_field_ops_router_alternates_use_named_dependency(self):
        import inspect
        from app.engines.field_ops import router as fr
        src = inspect.getsource(fr)
        for fn_name in ("accept_job", "reject_assignment", "start_checklist",
                         "update_checklist_item", "complete_checklist",
                         "submit_findings", "update_checklist"):
            fn_src = src.split(f"async def {fn_name}(")[1].split("\n\n@router")[0]
            assert "require_staff_or_technician_only" in fn_src, fn_name

    def test_update_status_and_assign_are_scope_aware(self):
        import inspect
        from app.engines.field_ops import router as fr
        src = inspect.getsource(fr)
        assign_src = src.split("async def assign_job(")[1].split("\n\n@router")[0]
        status_src = src.split("async def update_status(")[1].split("\n\n@router")[0]
        assert "require_tenant_mutation_permission" in assign_src
        assert "require_tenant_mutation_permission" in status_src

    def test_update_job_checklist_item_has_state_guard(self):
        import inspect
        src = inspect.getsource(FieldOpsService.update_job_checklist_item)
        assert "CHECKLIST_STARTED" in src
        assert "CHECKLIST_NOT_ACTIVE" in src
