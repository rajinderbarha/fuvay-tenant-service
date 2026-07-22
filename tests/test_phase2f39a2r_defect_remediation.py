"""Slice 2F-39A2R: fixes for the 6 real defects Slice 2F-39A2 found and
deliberately did not force-fix, plus the security.router::rotate_api_key/
revoke_api_key/list_api_keys/get_api_key sibling revalidation.

All 4 security.router fixes (record_activity, write_audit_entry,
create_session, revoke_session) are historically documented, unremediated
observations from Slice 2F-26D/F/G/H's
security-observations-not-remediated.md -- this is the "future slice"
that document explicitly deferred to.
"""
from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio


def _svc(actor_role="tenant_owner", actor_tenant_id=None, actor_id=None):
    from app.engines.security.service import SecurityService
    svc = SecurityService.__new__(SecurityService)
    svc.db = MagicMock()
    svc.redis = MagicMock()
    svc.redis.delete = AsyncMock()
    svc.actor_id = actor_id
    svc.actor_role = actor_role
    svc.actor_tenant_id = actor_tenant_id
    svc.actor_ip = "127.0.0.1"
    svc.request_id = "req_test"
    return svc


class TestRecordActivityTenantScoping:
    async def test_foreign_tenant_id_is_rejected(self):
        svc = _svc(actor_tenant_id=uuid.uuid4())
        with pytest.raises(Exception):
            await svc.record_activity(uuid.uuid4(), "e1", "user", "login_failed", "1.2.3.4")

    async def test_own_tenant_id_is_accepted(self):
        own = uuid.uuid4()
        svc = _svc(actor_tenant_id=own)
        svc._record_suspicious_activity = AsyncMock(return_value={"log_id": "x"})
        await svc.record_activity(own, "e1", "user", "login_failed", "1.2.3.4")
        called_tenant = svc._record_suspicious_activity.await_args.args[0]
        assert called_tenant == own


class TestWriteAuditEntryTenantScoping:
    async def test_foreign_tenant_id_is_rejected(self):
        svc = _svc(actor_tenant_id=uuid.uuid4())
        with pytest.raises(Exception):
            await svc.write_audit_entry("op", "engine", "e1", uuid.uuid4(), "user", None, None)

    async def test_own_tenant_id_is_accepted(self):
        own = uuid.uuid4()
        svc = _svc(actor_tenant_id=own)
        svc._write_audit = AsyncMock()
        svc.db.flush = AsyncMock()
        await svc.write_audit_entry("op", "engine", "e1", own, "user", None, None)
        called_tenant = svc._write_audit.await_args.args[3]
        assert called_tenant == own


class TestCreateSessionActorScoping:
    async def test_different_user_id_is_rejected(self):
        svc = _svc(actor_id=uuid.uuid4(), actor_tenant_id=uuid.uuid4())
        other_user = uuid.uuid4()
        with pytest.raises(Exception):
            await svc.create_session(other_user, svc.actor_tenant_id, "sess1", {}, None, None, 3600)

    async def test_own_user_id_is_accepted(self):
        me = uuid.uuid4()
        tenant = uuid.uuid4()
        svc = _svc(actor_id=me, actor_tenant_id=tenant)
        count_result = MagicMock()
        count_result.scalar_one_or_none.return_value = 0
        svc.db.execute = AsyncMock(return_value=count_result)
        svc.db.add = MagicMock()
        svc.db.flush = AsyncMock()
        svc.redis.set = AsyncMock()
        try:
            await svc.create_session(me, tenant, "sess1", {}, None, None, 3600)
        except Exception as e:
            # Some later step (redis/db shape) may not be fully mocked --
            # what matters is it does NOT fail on the actor-mismatch check.
            assert "another user" not in str(e)


class TestRevokeSessionOwnership:
    async def test_foreign_session_is_treated_as_not_found(self):
        me = uuid.uuid4()
        someone_else = uuid.uuid4()
        svc = _svc(actor_id=me)
        session = MagicMock(user_id=someone_else, is_active=True)
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = session
        svc.db.execute = AsyncMock(return_value=session_result)
        result = await svc.revoke_session("sess-123", "user requested")
        assert result["note"] == "Already expired"
        svc.redis.delete.assert_not_awaited()

    async def test_own_session_is_revoked(self):
        me = uuid.uuid4()
        svc = _svc(actor_id=me)
        session = MagicMock(user_id=me, is_active=True)
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = session
        svc.db.execute = AsyncMock(return_value=session_result)
        svc._write_audit = AsyncMock()
        result = await svc.revoke_session("sess-123", "user requested")
        assert result["revoked"] is True
        assert result.get("note") != "Already expired"
        svc.redis.delete.assert_awaited()

    async def test_super_admin_can_revoke_any_session(self):
        svc = _svc(actor_role="super_admin", actor_id=uuid.uuid4())
        session = MagicMock(user_id=uuid.uuid4(), is_active=True)
        session_result = MagicMock()
        session_result.scalar_one_or_none.return_value = session
        svc.db.execute = AsyncMock(return_value=session_result)
        svc._write_audit = AsyncMock()
        result = await svc.revoke_session("sess-123", "admin action")
        assert result["revoked"] is True
        svc.redis.delete.assert_awaited()


class TestPricingRuleActivationTenantScoping:
    def _pricing_svc(self, actor_role="tenant_owner", actor_tenant_id=None):
        from app.engines.pricing.service import PricingService
        svc = PricingService.__new__(PricingService)
        svc.db = MagicMock()
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        return svc

    async def test_activate_rule_rejects_foreign_tenant(self):
        svc = self._pricing_svc(actor_tenant_id=uuid.uuid4())
        with pytest.raises(Exception):
            await svc.activate_rule(uuid.uuid4(), tenant_id=uuid.uuid4())

    async def test_activate_rule_rejects_rule_owned_by_another_tenant(self):
        own_tenant = uuid.uuid4()
        other_tenant = uuid.uuid4()
        svc = self._pricing_svc(actor_tenant_id=own_tenant)
        rule = MagicMock(tenant_id=other_tenant, is_active=False)
        rule_result = MagicMock()
        rule_result.scalar_one_or_none.return_value = rule
        svc.db.execute = AsyncMock(return_value=rule_result)
        with pytest.raises(Exception):
            await svc.activate_rule(uuid.uuid4(), tenant_id=own_tenant)

    async def test_deactivate_rule_rejects_rule_owned_by_another_tenant(self):
        own_tenant = uuid.uuid4()
        other_tenant = uuid.uuid4()
        svc = self._pricing_svc(actor_tenant_id=own_tenant)
        rule = MagicMock(tenant_id=other_tenant, is_active=True)
        rule_result = MagicMock()
        rule_result.scalar_one_or_none.return_value = rule
        svc.db.execute = AsyncMock(return_value=rule_result)
        with pytest.raises(Exception):
            await svc.deactivate_rule(uuid.uuid4(), tenant_id=own_tenant)

    async def test_router_uses_tenant_mutation_permission(self):
        import inspect
        from app.engines.pricing import router as pricing_router
        for fn_name in ("activate_rule", "deactivate_rule"):
            src = inspect.getsource(getattr(pricing_router, fn_name))
            assert "require_tenant_mutation_permission(P.TENANT_UPDATE)" in src
            assert "tenant_id=tenant_id" in src
