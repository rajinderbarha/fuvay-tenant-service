"""
Verifies that sensitive cross-engine actions mirror into the centralized
PlatformAuditLog (app/core/audit.py), closing the Phase 1 audit-log gap:
tenant lifecycle changes, high-risk auth actions, platform-tier settings,
and admin wallet credits must all be searchable from one place.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.engines.security.models import PlatformAuditLog
from app.engines.tenant_engine.models import TenantAuditLog
from app.engines.auth.models import AuthAuditLog
from app.engines.settings_engine.models import SettingAuditLog


def make_db():
    db = MagicMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_platform_audit_normalizes_database_values_for_jsonb():
    from app.core.audit import record_platform_audit

    db = make_db()
    value_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    await record_platform_audit(
        db, operation="provider_offering.suspended", engine_id="tenant_engine",
        before={"id": value_id, "price": Decimal("299.00"), "at": now},
        after={"status": "suspended"},
    )
    entry = db.add.call_args.args[0]
    assert entry.before_state == {
        "id": str(value_id), "price": 299.0, "at": now.isoformat(),
    }


@pytest.mark.asyncio
async def test_tenant_audit_mirrors_to_platform_log():
    from app.engines.tenant_engine.service import TenantService
    db = make_db()
    svc = TenantService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    tid = uuid.uuid4()

    await svc._audit(tid, "tenant.suspended", before={"status": "active"}, after={"status": "suspended"})

    kinds = [type(call.args[0]) for call in db.add.call_args_list]
    assert TenantAuditLog in kinds
    assert PlatformAuditLog in kinds
    platform_entry = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], PlatformAuditLog))
    assert platform_entry.operation == "tenant.suspended"
    assert platform_entry.engine_id == "tenant"
    assert platform_entry.tenant_id == tid


@pytest.mark.asyncio
async def test_auth_high_risk_action_mirrors_to_platform_log():
    from app.engines.auth.service import AuthService
    db = make_db()
    svc = AuthService(db=db)

    await svc._audit("staff.deactivated", "success", actor_id=uuid.uuid4(), tenant_id=uuid.uuid4())

    kinds = [type(call.args[0]) for call in db.add.call_args_list]
    assert AuthAuditLog in kinds
    assert PlatformAuditLog in kinds


@pytest.mark.asyncio
async def test_auth_routine_login_does_not_mirror_to_platform_log():
    """Login/MFA noise must stay engine-local — mirroring it would drown the platform log."""
    from app.engines.auth.service import AuthService
    db = make_db()
    svc = AuthService(db=db)

    await svc._audit("login.success", "success", actor_id=uuid.uuid4())

    kinds = [type(call.args[0]) for call in db.add.call_args_list]
    assert AuthAuditLog in kinds
    assert PlatformAuditLog not in kinds


@pytest.mark.asyncio
async def test_platform_tier_setting_change_mirrors_to_platform_log():
    from app.engines.settings_engine.service import SettingsService
    db = make_db()
    svc = SettingsService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")

    await svc._audit("platform", "max_upload_mb", 10, 50)

    kinds = [type(call.args[0]) for call in db.add.call_args_list]
    assert SettingAuditLog in kinds
    assert PlatformAuditLog in kinds


@pytest.mark.asyncio
async def test_tenant_tier_setting_change_does_not_mirror_to_platform_log():
    """Per-tenant self-service settings are low-risk — only platform tier mirrors."""
    from app.engines.settings_engine.service import SettingsService
    db = make_db()
    svc = SettingsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner")

    await svc._audit("tenant", "business_hours", "9-5", "8-6", tenant_id=uuid.uuid4())

    kinds = [type(call.args[0]) for call in db.add.call_args_list]
    assert SettingAuditLog in kinds
    assert PlatformAuditLog not in kinds


@pytest.mark.asyncio
async def test_admin_wallet_credit_writes_platform_audit():
    """admin_credit_wallet previously had ZERO audit trail anywhere — must now log."""
    from app.engines.platform_commerce import service as commerce_module

    fake_txn = MagicMock(id=uuid.uuid4(), balance_after=1500)

    async def fake_credit_wallet(*args, **kwargs):
        return fake_txn

    db = make_db()
    svc = commerce_module.CommerceService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    svc._publish = AsyncMock()
    orig_credit_wallet = commerce_module.credit_wallet
    commerce_module.credit_wallet = fake_credit_wallet
    try:
        result = await svc.admin_credit_wallet(uuid.uuid4(), 1000, "goodwill credit", "support")
    finally:
        commerce_module.credit_wallet = orig_credit_wallet

    assert result["amount_credited"] == 1000.0
    kinds = [type(call.args[0]) for call in db.add.call_args_list]
    assert PlatformAuditLog in kinds
    entry = next(c.args[0] for c in db.add.call_args_list if isinstance(c.args[0], PlatformAuditLog))
    assert entry.operation == "wallet.admin_credited"
    assert entry.after_state["amount"] == 1000.0
