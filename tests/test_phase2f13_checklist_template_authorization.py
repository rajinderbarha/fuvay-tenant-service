"""Phase 2A Slice 2F-13 — field_ops.checklist_router authorization,
tenant ownership and template-item integrity closure.

`checklist_router` is a **tenant checklist-TEMPLATE CRUD** router
(`/v1/tenant/checklist-templates`) operating on `ServiceChecklistTemplate`
+ `ServiceChecklistItem` (catalog-style, keyed to a `service_id` — NOT to
a job). Per-job checklist execution (`JobChecklistItem`, completion
gating, technician evidence) is a DISTINCT model mutated by the
out-of-scope `field_ops.service.py` / `staff_router`.

Two conclusively-proven defects fixed this slice:

1. **Access-scope gap (all 6 mutations)**: routes used
   `require_permission(P.FIELD_OPS_CHECKLIST_MANAGE)`, which enforces the
   permission but NOT tenant read-only access scope. A read-only
   tenant_owner (access_scope='customer_support_limited') carrying the
   permission could still mutate templates. Fixed to
   `require_tenant_mutation_permission(...)` on the 6 mutations (reads
   keep `require_permission` — read-only users must still read).

2. **Cross-tenant IDOR in `_get_template_for_tenant`**: the tenant
   ownership check fired ONLY when `actor_role == "tenant_owner"`.
   FIELD_OPS_CHECKLIST_MANAGE is tenant_owner-only by default grant, but a
   `staff` member granted it via a StaffPermission override would skip the
   tenant filter entirely and reach ANY tenant's template by ID. Fixed to
   enforce ownership for every tenant-scoped actor (all except
   super_admin), same fail-closed NOT_FOUND response.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.engines.field_ops.checklist_template_service import ChecklistTemplateService


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


TID = "11111111-1111-1111-1111-111111111111"
ITEM_ID = "22222222-2222-2222-2222-222222222222"

MUTATION_ROUTES = [
    ("POST", "/v1/tenant/checklist-templates", {"service_id": str(uuid.uuid4()), "name": "x"}),
    ("PUT", f"/v1/tenant/checklist-templates/{TID}", {"name": "y"}),
    ("DELETE", f"/v1/tenant/checklist-templates/{TID}", None),
    ("POST", f"/v1/tenant/checklist-templates/{TID}/items", {"title": "z"}),
    ("PUT", f"/v1/tenant/checklist-templates/{TID}/items/{ITEM_ID}", {"title": "z2"}),
    ("DELETE", f"/v1/tenant/checklist-templates/{TID}/items/{ITEM_ID}", None),
]

READ_ROUTES = [
    ("GET", "/v1/tenant/checklist-templates"),
    ("GET", f"/v1/tenant/checklist-templates/{TID}"),
    ("GET", f"/v1/tenant/checklist-templates/{TID}/items"),
]


@pytest.mark.asyncio
class TestPermissionAndScopeGate:
    async def test_unauthenticated_denied_on_every_mutation(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for method, path, body in MUTATION_ROUTES:
                resp = await client.request(method, path, json=body)
                assert resp.status_code in (401, 403), f"{method} {path} -> {resp.status_code}"

    @pytest.mark.parametrize("role", ["technician", "customer", "guest", "staff", "totally_bogus_role"])
    async def test_no_permission_role_denied_on_every_mutation(self, role):
        """Only tenant_owner (+super_admin) hold FIELD_OPS_CHECKLIST_MANAGE
        by default; staff/technician/customer/guest are denied."""
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in MUTATION_ROUTES:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()

    async def test_readonly_tenant_owner_denied_on_every_mutation(self):
        """The access-scope fix: a read-only tenant_owner holds the
        permission but must be denied every mutation."""
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in MUTATION_ROUTES:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}"
                    body_j = resp.json()
                    code = (body_j.get("error") or {}).get("code") or body_j.get("error_code")
                    assert code == "PERMISSION_DENIED", (method, path, body_j)
        finally:
            _clear()

    async def test_readonly_tenant_owner_retains_reads(self):
        """Reads keep require_permission (no scope block) -- a read-only
        tenant_owner must still be able to read templates."""
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path in READ_ROUTES:
                    resp = await client.request(method, path)
                    body_j = resp.json()
                    code = (body_j.get("error") or {}).get("code") or body_j.get("error_code")
                    # The read permission gate must NOT deny a read-only user.
                    assert code != "PERMISSION_DENIED", (method, path, body_j)
        finally:
            _clear()

    async def test_full_scope_tenant_owner_clears_mutation_gate(self):
        _override(_user("tenant_owner"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/v1/tenant/checklist-templates",
                                         json={"service_id": str(uuid.uuid4()), "name": "x"})
                body_j = resp.json()
                code = (body_j.get("error") or {}).get("code") or body_j.get("error_code")
                assert code != "PERMISSION_DENIED", body_j
        finally:
            _clear()


# ── Service-layer tenant-ownership IDOR (the _get_template_for_tenant fix) ────

def _mock_template(tenant_id):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.tenant_id = tenant_id
    t.deleted_at = None
    return t


def _svc_returning(template, item=None):
    svc = ChecklistTemplateService(
        db=MagicMock(), actor_id=uuid.uuid4(), actor_role="tenant_owner",
        actor_tenant_id=uuid.uuid4())
    tmpl_result = MagicMock()
    tmpl_result.scalar_one_or_none.return_value = template
    item_result = MagicMock()
    item_result.scalar_one_or_none.return_value = item
    # first execute -> template, second -> item
    svc.db.execute = AsyncMock(side_effect=[tmpl_result, item_result])
    return svc


@pytest.mark.asyncio
class TestTemplateTenantOwnershipIDOR:
    async def test_staff_cannot_reach_foreign_tenant_template(self):
        """The IDOR fix: a staff actor (granted the permission via
        override) must be blocked from a foreign-tenant template -- the
        old code skipped the check for non-tenant_owner roles."""
        foreign_tenant = uuid.uuid4()
        actor_tenant = uuid.uuid4()
        tmpl = _mock_template(foreign_tenant)
        svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                       actor_role="staff", actor_tenant_id=actor_tenant)
        r = MagicMock(); r.scalar_one_or_none.return_value = tmpl
        svc.db.execute = AsyncMock(return_value=r)
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as ei:
            await svc._get_template_for_tenant(tmpl.id)
        assert ei.value.error_code == "CHECKLIST_TEMPLATE_NOT_FOUND"

    async def test_tenant_owner_cannot_reach_foreign_tenant_template(self):
        """Preserved: tenant_owner ownership check still fires."""
        foreign_tenant = uuid.uuid4()
        tmpl = _mock_template(foreign_tenant)
        svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                       actor_role="tenant_owner", actor_tenant_id=uuid.uuid4())
        r = MagicMock(); r.scalar_one_or_none.return_value = tmpl
        svc.db.execute = AsyncMock(return_value=r)
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as ei:
            await svc._get_template_for_tenant(tmpl.id)
        assert ei.value.error_code == "CHECKLIST_TEMPLATE_NOT_FOUND"

    async def test_super_admin_may_reach_any_tenant_template(self):
        """Preserved exemption: platform admin is not tenant-scoped."""
        tmpl = _mock_template(uuid.uuid4())
        svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                       actor_role="super_admin", actor_tenant_id=None)
        r = MagicMock(); r.scalar_one_or_none.return_value = tmpl
        svc.db.execute = AsyncMock(return_value=r)
        result = await svc._get_template_for_tenant(tmpl.id)
        assert result is tmpl

    async def test_matching_tenant_allowed_for_owner_and_staff(self):
        for role in ("tenant_owner", "staff"):
            actor_tenant = uuid.uuid4()
            tmpl = _mock_template(actor_tenant)  # same tenant
            svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                           actor_role=role, actor_tenant_id=actor_tenant)
            r = MagicMock(); r.scalar_one_or_none.return_value = tmpl
            svc.db.execute = AsyncMock(return_value=r)
            result = await svc._get_template_for_tenant(tmpl.id)
            assert result is tmpl, role


@pytest.mark.asyncio
class TestItemParentIntegrity:
    async def test_foreign_item_under_template_rejected(self):
        """An item whose template_id != the supplied template_id is
        rejected (foreign-item substitution)."""
        actor_tenant = uuid.uuid4()
        tmpl = _mock_template(actor_tenant)
        foreign_item = MagicMock()
        foreign_item.id = uuid.uuid4()
        foreign_item.template_id = uuid.uuid4()  # belongs to a DIFFERENT template
        foreign_item.deleted_at = None
        svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                       actor_role="tenant_owner", actor_tenant_id=actor_tenant)
        tmpl_r = MagicMock(); tmpl_r.scalar_one_or_none.return_value = tmpl
        item_r = MagicMock(); item_r.scalar_one_or_none.return_value = foreign_item
        svc.db.execute = AsyncMock(side_effect=[tmpl_r, item_r])
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as ei:
            await svc._get_item_for_template(tmpl.id, foreign_item.id)
        assert ei.value.error_code == "CHECKLIST_ITEM_NOT_FOUND"

    async def test_item_belonging_to_template_allowed(self):
        actor_tenant = uuid.uuid4()
        tmpl = _mock_template(actor_tenant)
        item = MagicMock()
        item.id = uuid.uuid4()
        item.template_id = tmpl.id  # correct parent
        item.deleted_at = None
        svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                       actor_role="tenant_owner", actor_tenant_id=actor_tenant)
        tmpl_r = MagicMock(); tmpl_r.scalar_one_or_none.return_value = tmpl
        item_r = MagicMock(); item_r.scalar_one_or_none.return_value = item
        svc.db.execute = AsyncMock(side_effect=[tmpl_r, item_r])
        result = await svc._get_item_for_template(tmpl.id, item.id)
        assert result is item


@pytest.mark.asyncio
class TestListItemsReadIDOR:
    async def test_list_items_enforces_tenant_ownership(self):
        """The standalone GET /{template_id}/items previously read a
        foreign tenant's template item titles with no ownership check."""
        foreign_tenant = uuid.uuid4()
        actor_tenant = uuid.uuid4()
        tmpl = _mock_template(foreign_tenant)
        svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                       actor_role="staff", actor_tenant_id=actor_tenant)
        r = MagicMock(); r.scalar_one_or_none.return_value = tmpl
        svc.db.execute = AsyncMock(return_value=r)
        from app.exceptions import ServiceOSException
        with pytest.raises(ServiceOSException) as ei:
            await svc.list_items(tmpl.id)
        assert ei.value.error_code == "CHECKLIST_TEMPLATE_NOT_FOUND"

    async def test_list_items_allowed_for_own_tenant(self):
        actor_tenant = uuid.uuid4()
        tmpl = _mock_template(actor_tenant)
        svc = ChecklistTemplateService(db=MagicMock(), actor_id=uuid.uuid4(),
                                       actor_role="tenant_owner", actor_tenant_id=actor_tenant)
        tmpl_r = MagicMock(); tmpl_r.scalar_one_or_none.return_value = tmpl
        items_r = MagicMock(); items_r.scalars.return_value.all.return_value = []
        svc.db.execute = AsyncMock(side_effect=[tmpl_r, items_r])
        result = await svc.list_items(tmpl.id)
        assert result["template_id"] == str(tmpl.id)


class TestSourceGuards:
    def test_all_six_mutations_use_scope_aware_guard(self):
        import inspect
        from app.engines.field_ops import checklist_router as cr
        src = inspect.getsource(cr)
        # 6 mutation endpoints must use the scope-aware guard
        assert src.count("require_tenant_mutation_permission(P.FIELD_OPS_CHECKLIST_MANAGE)") == 6

    def test_ownership_check_is_role_agnostic(self):
        import inspect
        src = inspect.getsource(ChecklistTemplateService._get_template_for_tenant)
        assert 'self.actor_role != "super_admin"' in src
        assert 'self.actor_role == "tenant_owner"' not in src
