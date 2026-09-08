"""Behavioral coverage of one-time credentials and the owner access boundary."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.provider_portal import team_login_service as service
from app.engines.auth.models import User
from app.engines.auth.service import AuthService
from app.engines.auth.utils import verify_password
from app.exceptions import ServiceOSException


@pytest.fixture
def context():
    tid, uid, mid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    actor = SimpleNamespace(user_id=str(uid), tenant_id=str(tid), role="tenant_owner")
    member = SimpleNamespace(id=mid, tenant_id=tid, full_name="Team Example", email="team@example.test",
                             phone=None, member_type="technician", user_id=None, status="active")
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.fetchone.return_value = member
    result.scalar_one_or_none.return_value = None
    result.scalar.return_value = None
    db.execute.return_value = result
    return tid, actor, member, db


@pytest.mark.asyncio
async def test_generation_uses_real_hash_and_requires_password_change(context, monkeypatch):
    tid, actor, member, db = context
    async def created_user(self, user_id):
        return next(call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], User))
    monkeypatch.setattr(AuthService, "_get_user_by_id", created_user)
    revoke, audit = AsyncMock(return_value=2), AsyncMock()
    monkeypatch.setattr(AuthService, "_revoke_all_user_sessions", revoke)
    monkeypatch.setattr(AuthService, "_audit", audit)
    result = await service.generate_team_password(db, member.id, tid, actor, "request", None)
    account = await created_user(None, None)
    assert verify_password(result["temporary_password"], account.hashed_password)
    assert account.hashed_password != result["temporary_password"]
    assert account.force_password_change and account.password_reset_required and account.temporary_password_active
    assert account.role == "technician" and account.is_active
    assert result["username"] == member.email and result["sessions_revoked"] == 2
    assert result["temporary_password"] not in str(audit.call_args)
    assert result["temporary_password"] not in str(db.execute.call_args_list)
    revoke.assert_awaited_once_with(account.id)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value,code", [("status", "inactive", "TEAM_MEMBER_DISABLED"), ("email", None, "TEAM_MEMBER_EMAIL_REQUIRED")])
async def test_disabled_or_missing_email_cannot_generate(context, field, value, code):
    tid, actor, member, db = context
    setattr(member, field, value)
    with pytest.raises(ServiceOSException) as exc:
        await service.generate_team_password(db, member.id, tid, actor, "request", None)
    assert exc.value.error_code == code
    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("role,cross_tenant,self_account", [
    ("tenant_owner", False, False), ("super_admin", False, False),
    ("staff", True, False), ("technician", False, True),
])
def test_owner_cannot_manage_unrelated_or_privileged_accounts(context, role, cross_tenant, self_account):
    tid, actor, _, _ = context
    account = SimpleNamespace(id=actor.user_id if self_account else uuid.uuid4(),
                              tenant_id=uuid.uuid4() if cross_tenant else tid, role=role)
    with pytest.raises(ServiceOSException) as exc:
        service.assert_managed_account(account, tid, actor.user_id)
    assert exc.value.error_code == "TEAM_LOGIN_SCOPE_INVALID"


@pytest.mark.asyncio
async def test_disable_revokes_sessions_and_enable_only_undoes_provider_disable(context, monkeypatch):
    tid, actor, member, db = context
    account = SimpleNamespace(id=uuid.uuid4(), meta={}, account_status="active", is_active=True)
    monkeypatch.setattr(service, "linked_account", AsyncMock(return_value=account))
    revoke = AsyncMock(return_value=1)
    monkeypatch.setattr(AuthService, "_revoke_all_user_sessions", revoke)
    await service.set_login_enabled(db, member.id, tid, actor.user_id, False)
    assert not account.is_active and account.meta["provider_access_disabled"]
    revoke.assert_awaited_once_with(account.id)
    assert db.execute.call_args.args[0].compile().params["status"] == "revoked"
    await service.set_login_enabled(db, member.id, tid, actor.user_id, True)
    assert account.is_active and "provider_access_disabled" not in account.meta


@pytest.mark.asyncio
@pytest.mark.parametrize("status,meta", [("suspended", {"provider_access_disabled": True}), ("active", {})])
async def test_enable_does_not_undo_admin_suspension_or_pending_invitation(context, monkeypatch, status, meta):
    tid, actor, member, db = context
    account = SimpleNamespace(id=uuid.uuid4(), meta=meta, account_status=status, is_active=False)
    monkeypatch.setattr(service, "linked_account", AsyncMock(return_value=account))
    await service.set_login_enabled(db, member.id, tid, actor.user_id, True)
    assert not account.is_active


@pytest.mark.asyncio
async def test_duplicate_email_does_not_link_other_account(context, monkeypatch):
    tid, actor, member, db = context
    monkeypatch.setattr(service, "linked_account", AsyncMock(return_value=None))
    db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(id=uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc:
        await service.generate_team_password(db, member.id, tid, actor, "request", None)
    assert exc.value.error_code == "TEAM_MEMBER_EMAIL_IN_USE"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_disabled_login_cannot_be_reset_as_activation(context, monkeypatch):
    tid, actor, member, db = context
    account = SimpleNamespace(id=uuid.uuid4(), email=member.email, meta={}, account_status="active", is_active=False)
    monkeypatch.setattr(service, "linked_account", AsyncMock(return_value=account))
    with pytest.raises(ServiceOSException) as exc:
        await service.generate_team_password(db, member.id, tid, actor, "request", None)
    assert exc.value.error_code == "TEAM_LOGIN_DISABLED"
    assert not account.is_active


@pytest.mark.asyncio
async def test_starter_skills_are_idempotent_and_do_not_restore_retired(context):
    from app.engines.admin_catalog.starter_skills import add_starter_skills, HOME_SERVICE_SKILLS
    tid, actor, _, db = context
    db.execute.return_value.rowcount = 0
    assert await add_starter_skills(db, tid, actor.user_id) == 0
    assert db.execute.await_count == len(HOME_SERVICE_SKILLS)
    for call in db.execute.call_args_list:
        sql = str(call.args[0])
        assert "ON CONFLICT (category_id, code) DO NOTHING" in sql
        assert "lower(name)=lower(:name)" in sql
        assert "UPDATE" not in sql
