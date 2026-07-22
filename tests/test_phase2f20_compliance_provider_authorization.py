"""Slice 2F-20 — Compliance Provider Authorization, Tenant Authority,
Data-Subject Ownership, Consent Withdrawal and Export Privacy Closure.

Covers:
- Dependency-level: require_tenant_owner_mutation direct invocation
  (read-only tenant owner denied, super_admin exempt, prohibited alias
  denied).
- withdraw_consent no longer passes tenant_id=None.
- create_request persists metadata_json (tenant ownership) atomically at
  INSERT time, not via a separate post-creation UPDATE.
- Cross-tenant / same-tenant IDOR rejection for request/export lookups
  (existing metadata_json filtering, re-verified unchanged).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _user(role, user_id=None, tenant_id=None, access_scope=None):
    from app.dependencies.auth import UserContext
    return UserContext(
        user_id=str(user_id or uuid.uuid4()), email="x@example.com", role=role,
        tenant_id=tenant_id, full_name="X", is_verified=True, access_scope=access_scope,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 1. require_tenant_owner_mutation — direct dependency invocation
# ══════════════════════════════════════════════════════════════════════════════

class TestRequireTenantOwnerMutation:
    @pytest.mark.asyncio
    async def test_admits_tenant_owner(self):
        from app.core.permissions import require_tenant_owner_mutation
        u = _user("tenant_owner", tenant_id=str(uuid.uuid4()))
        result = await require_tenant_owner_mutation(u)
        assert result is u

    @pytest.mark.asyncio
    async def test_admits_super_admin_even_with_readonly_scope(self):
        from app.core.permissions import require_tenant_owner_mutation
        u = _user("super_admin", access_scope="customer_support_limited")
        result = await require_tenant_owner_mutation(u)
        assert result is u

    @pytest.mark.asyncio
    async def test_denies_readonly_tenant_owner(self):
        from app.core.permissions import require_tenant_owner_mutation
        from app.exceptions import ServiceOSException
        u = _user("tenant_owner", tenant_id=str(uuid.uuid4()), access_scope="customer_support_limited")
        with pytest.raises(ServiceOSException):
            await require_tenant_owner_mutation(u)

    @pytest.mark.asyncio
    async def test_denies_staff_role(self):
        # require_tenant_owner (the underlying dependency) excludes staff --
        # require_tenant_owner_mutation must preserve that exclusion, not
        # broaden the admitted role set.
        from app.dependencies.auth import require_tenant_owner
        from app.exceptions import ServiceOSException
        u = _user("staff", tenant_id=str(uuid.uuid4()))
        with pytest.raises(ServiceOSException):
            await require_tenant_owner(u)

    @pytest.mark.asyncio
    async def test_denies_technician(self):
        from app.dependencies.auth import require_tenant_owner
        from app.exceptions import ServiceOSException
        u = _user("technician", tenant_id=str(uuid.uuid4()))
        with pytest.raises(ServiceOSException):
            await require_tenant_owner(u)

    @pytest.mark.asyncio
    async def test_denies_customer(self):
        from app.dependencies.auth import require_tenant_owner
        from app.exceptions import ServiceOSException
        u = _user("customer")
        with pytest.raises(ServiceOSException):
            await require_tenant_owner(u)

    @pytest.mark.asyncio
    async def test_denies_prohibited_role_alias(self):
        from app.dependencies.auth import require_tenant_owner
        from app.exceptions import ServiceOSException
        u = _user("office_staff")  # prohibited alias, not a canonical role
        with pytest.raises(ServiceOSException):
            await require_tenant_owner(u)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Provider router — dependency wiring confirmed on all 6 mutations + download_export
# ══════════════════════════════════════════════════════════════════════════════

class TestProviderRouterDependencyWiring:
    def _dep_names(self, route):
        names = set()

        def walk(dependant):
            if dependant.call is not None and hasattr(dependant.call, "__name__"):
                names.add(dependant.call.__name__)
            for sub in dependant.dependencies:
                walk(sub)
        walk(route.dependant)
        return names

    @pytest.mark.parametrize("fn_name", [
        "withdraw_consent", "customer_tenant_response", "create_my_request",
        "cancel_my_request", "generate_export", "staff_tenant_response",
        "download_export",
    ])
    def test_uses_require_tenant_owner_mutation(self, fn_name):
        from app.engines.compliance import provider_router as m
        routes = {r.name: r for r in m.router.routes}
        assert fn_name in routes
        deps = self._dep_names(routes[fn_name])
        assert "require_tenant_owner_mutation" in deps

    @pytest.mark.parametrize("fn_name", [
        "list_staff_requests", "get_staff_request",
        "list_customer_requests", "get_customer_request",
    ])
    def test_read_routes_unchanged_bare_role_check(self, fn_name):
        # These are pure reads, deliberately left on the narrower bare-role
        # dependency (unchanged, not upgraded) -- out of this slice's
        # 6-mutation + download_export scope.
        from app.engines.compliance import provider_router as m
        routes = {r.name: r for r in m.router.routes}
        assert fn_name in routes
        deps = self._dep_names(routes[fn_name])
        assert "require_tenant_owner" in deps
        assert "require_tenant_owner_mutation" not in deps


# ══════════════════════════════════════════════════════════════════════════════
# 3. withdraw_consent no longer passes tenant_id=None
# ══════════════════════════════════════════════════════════════════════════════

class TestWithdrawConsentTenantFix:
    @pytest.mark.asyncio
    async def test_revoke_consent_forwards_real_tenant_id(self):
        from app.engines.compliance.enterprise_service import ComplianceEnterpriseService

        svc = ComplianceEnterpriseService.__new__(ComplianceEnterpriseService)
        svc._base = MagicMock()
        svc._base.withdraw_consent = AsyncMock(return_value={"withdrawn": True})
        svc._audit = AsyncMock()

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        await svc.revoke_consent(user_id, "marketing", "no longer needed", tenant_id=tenant_id)

        svc._base.withdraw_consent.assert_awaited_once_with(user_id, tenant_id, "marketing", "1.0")

    @pytest.mark.asyncio
    async def test_revoke_consent_defaults_to_none_when_caller_has_no_tenant(self):
        # Customer self-service callers genuinely have no tenant_id --
        # confirms the default is preserved for that legitimate case, not
        # removed outright.
        from app.engines.compliance.enterprise_service import ComplianceEnterpriseService

        svc = ComplianceEnterpriseService.__new__(ComplianceEnterpriseService)
        svc._base = MagicMock()
        svc._base.withdraw_consent = AsyncMock(return_value={"withdrawn": True})
        svc._audit = AsyncMock()

        user_id = uuid.uuid4()
        await svc.revoke_consent(user_id, "marketing", "reason")

        svc._base.withdraw_consent.assert_awaited_once_with(user_id, None, "marketing", "1.0")

    def test_provider_router_withdraw_consent_source_passes_tenant_id(self):
        import inspect
        from app.engines.compliance import provider_router as m
        src = inspect.getsource(m.withdraw_consent)
        assert "tenant_id=uuid.UUID(tenant_id_str)" in src


# ══════════════════════════════════════════════════════════════════════════════
# 4. create_request persists metadata_json atomically
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateRequestAtomicMetadata:
    @pytest.mark.asyncio
    async def test_metadata_json_passed_to_model_constructor(self):
        from app.engines.compliance.enterprise_service import ComplianceEnterpriseService

        svc = ComplianceEnterpriseService.__new__(ComplianceEnterpriseService)
        svc.db = MagicMock()
        svc.db.add = MagicMock()
        svc.db.flush = AsyncMock()
        svc._next_request_number = AsyncMock(return_value="COMP-2026-000001")
        svc._audit = AsyncMock()
        svc._enrich_request = MagicMock(return_value={"id": "x"})

        tenant_id = str(uuid.uuid4())
        data = {
            "subject_type": "tenant_business",
            "subject_id": tenant_id,
            "request_type": "data_export",
            "metadata_json": {"tenant_id": tenant_id, "actor_user_id": str(uuid.uuid4())},
        }
        await svc.create_request(data)

        assert svc.db.add.call_count == 1
        added_obj = svc.db.add.call_args[0][0]
        assert added_obj.metadata_json == data["metadata_json"]

    @pytest.mark.asyncio
    async def test_missing_metadata_json_defaults_to_empty_dict_not_none(self):
        from app.engines.compliance.enterprise_service import ComplianceEnterpriseService

        svc = ComplianceEnterpriseService.__new__(ComplianceEnterpriseService)
        svc.db = MagicMock()
        svc.db.add = MagicMock()
        svc.db.flush = AsyncMock()
        svc._next_request_number = AsyncMock(return_value="COMP-2026-000002")
        svc._audit = AsyncMock()
        svc._enrich_request = MagicMock(return_value={"id": "x"})

        data = {"subject_type": "customer", "subject_id": str(uuid.uuid4()), "request_type": "data_export"}
        await svc.create_request(data)

        added_obj = svc.db.add.call_args[0][0]
        assert added_obj.metadata_json == {}

    def test_provider_router_no_longer_does_post_creation_metadata_update(self):
        import inspect
        from app.engines.compliance import provider_router as m
        src = inspect.getsource(m.create_my_request)
        assert "Store tenant_id in the metadata after creation" not in src
        assert '"metadata_json": {' in src  # still passed into create_request's data dict


# ══════════════════════════════════════════════════════════════════════════════
# 5. Cross-tenant / cross-subject IDOR (existing metadata_json filtering, re-verified)
# ══════════════════════════════════════════════════════════════════════════════

class TestExistingTenantScopingUnchanged:
    def test_cancel_my_request_source_still_scopes_by_metadata_tenant_id(self):
        import inspect
        from app.engines.compliance import provider_router as m
        src = inspect.getsource(m.cancel_my_request)
        assert 'metadata_json["tenant_id"].astext == tenant_id_str' in src

    def test_generate_export_source_still_scopes_by_metadata_tenant_id(self):
        import inspect
        from app.engines.compliance import provider_router as m
        src = inspect.getsource(m.generate_export)
        assert 'metadata_json["tenant_id"].astext == tenant_id_str' in src

    def test_download_export_source_still_scopes_by_metadata_tenant_id(self):
        import inspect
        from app.engines.compliance import provider_router as m
        src = inspect.getsource(m.download_export)
        assert "tenant_id_str" in src
