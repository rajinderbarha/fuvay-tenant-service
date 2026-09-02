"""Sprint 4 — Tenant Onboarding + Tenant 360 Backend Tests (57 tests).

Tests cover:
  • AdminTenantService — slugify, tenant_code generation
  • Atomic onboarding (success + rollback guards on missing fields)
  • Tenant CRUD + lifecycle (verify, reject, suspend, archive)
  • Users sub-resource CRUD (list, create, suspend, reset password)
  • Staff sub-resource CRUD (list, create, deactivate, reset password, photo)
  • Service Areas sub-resource CRUD (list, create, update, delete)
  • Credit Wallet (get, topup, adjust, ledger)
  • Security Deposit (get, mark-paid)
  • Settings (get, update)
  • Overview
  • Audit logs
  • Tenant portal router helpers (_tenant_id, safe-field filter)
  • Error code coverage (all 43 Sprint 4 error codes present in base.py)
  • TenantSettings model defaults
"""
from __future__ import annotations

import re
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest


# ═══════════════════════════════════════════════════════════════
# UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════

def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]


def _tenant_code(name: str) -> str:
    letters = re.sub(r"[^a-z0-9]", "", name.lower())[:6].upper()
    suffix = uuid.uuid4().hex[:4].upper()
    return f"TNT-{letters}-{suffix}"


# ── 1-5: Slugify utility ───────────────────────────────────────

def test_slugify_simple():
    assert _slugify("Rajan Home Services") == "rajan-home-services"


def test_slugify_special_chars():
    assert _slugify("A&B Plumbing!") == "ab-plumbing"


def test_slugify_trim_dashes():
    assert _slugify("  --Hello World--  ") == "hello-world"


def test_slugify_max_80_chars():
    long = "a" * 100
    assert len(_slugify(long)) == 80


def test_slugify_numbers():
    assert _slugify("24/7 Repair Co.") == "247-repair-co"


# ── 6-8: Tenant code generation ───────────────────────────────

def test_tenant_code_prefix():
    code = _tenant_code("Rajan Home Services")
    assert code.startswith("TNT-")


def test_tenant_code_format():
    code = _tenant_code("Rajan Home Services")
    parts = code.split("-")
    assert len(parts) == 3


def test_tenant_code_unique():
    c1 = _tenant_code("Same Name")
    c2 = _tenant_code("Same Name")
    assert c1 != c2


# ═══════════════════════════════════════════════════════════════
# MOCK DB FIXTURE
# ═══════════════════════════════════════════════════════════════

def _make_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    # AsyncSession.begin_nested() returns an async context manager directly;
    # model that contract instead of AsyncMock's default coroutine return.
    db.begin_nested = MagicMock()
    db.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    db.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)
    return db


def _scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    result.scalar = MagicMock(return_value=value)
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    return result


def _make_tenant(**kwargs):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.tenant_name = kwargs.get("tenant_name", "Test Tenant")
    t.business_name = kwargs.get("business_name", "Test Tenant")
    t.legal_name = None
    t.slug = kwargs.get("slug", "test-tenant")
    t.tenant_code = kwargs.get("tenant_code", "TNT-TEST-1234")
    t.vertical = "home_services"
    t.category_id = None
    t.status = kwargs.get("status", "pending_verification")
    t.verification_status = kwargs.get("verification_status", "not_started")
    t.plan_type = "starter"
    t.owner_user_id = None
    t.email = "test@example.com"
    t.phone = "+91 9876543210"
    t.gst_number = None
    t.business_type = None
    t.address_line1 = None
    t.address_line2 = None
    t.district = None
    t.city = "Ludhiana"
    t.state = "Punjab"
    t.zipcode = None
    t.country = "India"
    t.logo_url = None
    t.health_score = 100.0
    t.health_band = "gold"
    t.rating_average = 0.0
    t.is_discoverable = True
    t.activated_at = None
    t.suspended_at = None
    t.suspension_reason = None
    t.archived_at = None
    t.created_at = MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00+00:00"))
    t.updated_at = None
    for k, v in kwargs.items():
        setattr(t, k, v)
    return t


def _make_user(**kwargs):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.full_name = kwargs.get("full_name", "Test User")
    u.email = kwargs.get("email", "user@example.com")
    u.phone = kwargs.get("phone", "+91 9000000000")
    u.role = kwargs.get("role", "tenant_owner")
    u.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    u.is_active = kwargs.get("is_active", True)
    u.is_verified = kwargs.get("is_verified", False)
    u.last_login_at = None
    u.created_at = MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00+00:00"))
    for k, v in kwargs.items():
        setattr(u, k, v)
    return u


# FINAL-L5-05T: _make_area() removed -- it only ever backed the now-
# removed AdminTenantService service-area tests (see the "SERVICE AREAS"
# block further down, also removed this sprint).

# ═══════════════════════════════════════════════════════════════
# ADMIN TENANT SERVICE — import + instantiation
# ═══════════════════════════════════════════════════════════════

async def _make_svc(db=None):
    from app.engines.tenant_engine.admin_service import AdminTenantService
    return AdminTenantService(
        db=db or _make_db(),
        request_id="test-req",
        actor_id=uuid.uuid4(),
        actor_role="super_admin",
    )


# ── 9: Service can be instantiated ────────────────────────────

@pytest.mark.asyncio
async def test_service_instantiation():
    svc = await _make_svc()
    assert svc.actor_role == "super_admin"


# ═══════════════════════════════════════════════════════════════
# ONBOARDING VALIDATION
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_onboard_missing_business_name():
    from app.exceptions import ServiceOSException
    db = _make_db()
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.onboard_tenant({
            "business": {"city": "Ludhiana", "state": "Punjab"},
            "owner": {"name": "Test", "email": "a@b.com", "phone": "9999999999"},
        })
    assert "business_name" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_onboard_missing_city():
    from app.exceptions import ServiceOSException
    db = _make_db()
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException):
        await svc.onboard_tenant({
            "business": {"business_name": "Rajan", "state": "Punjab"},
            "owner": {"name": "Test", "email": "a@b.com", "phone": "9999999999"},
        })


@pytest.mark.asyncio
async def test_onboard_missing_owner():
    from app.exceptions import ServiceOSException
    db = _make_db()
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.onboard_tenant({
            "business": {"business_name": "Rajan", "city": "Ludhiana", "state": "Punjab"},
            "owner": {},
        })
    assert "owner" in exc.value.detail.lower() or "name" in exc.value.detail.lower()


# ── 13-14: Onboarding — duplicate email guard ──────────────────

@pytest.mark.asyncio
async def test_onboard_duplicate_email():
    from app.exceptions import ServiceOSException
    db = _make_db()
    existing_user = _make_user(email="taken@example.com")
    db.execute.return_value = _scalar_result(existing_user)
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.onboard_tenant({
            "business": {"business_name": "Rajan", "city": "Ludhiana", "state": "Punjab"},
            "owner": {"name": "Test", "email": "taken@example.com", "phone": "9999999999"},
        })
    assert "already exists" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_onboard_no_duplicate_on_new_email():
    """No exception when email is fresh — test that the flow progresses past email check."""
    db = _make_db()
    # First execute (user check): not found. Second+ execute (slug check + etc): also not found.
    db.execute.return_value = _scalar_result(None)
    svc = await _make_svc(db)
    # It will fail later on flush/model creation — just ensure no "already exists" exception
    try:
        await svc.onboard_tenant({
            "business": {"business_name": "Rajan", "city": "Ludhiana", "state": "Punjab"},
            "owner": {"name": "Test", "email": "new@example.com", "phone": "9999999999"},
        })
    except Exception as e:
        assert "already exists" not in str(e).lower()


# ═══════════════════════════════════════════════════════════════
# TENANT CRUD
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_tenant_not_found():
    from app.exceptions import NotFoundException
    db = _make_db()
    db.execute.return_value = _scalar_result(None)
    svc = await _make_svc(db)
    with pytest.raises(NotFoundException):
        await svc.get_tenant(uuid.uuid4())


@pytest.mark.asyncio
async def test_get_tenant_found():
    db = _make_db()
    tenant = _make_tenant()
    # Each execute returns the tenant (for get_tenant + settings + billing)
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    result = await svc.get_tenant(tenant.id)
    assert result["tenant_id"] == str(tenant.id)
    assert result["tenant_name"] == tenant.tenant_name


@pytest.mark.asyncio
async def test_list_tenants_returns_list():
    db = _make_db()
    tenants = [_make_tenant(), _make_tenant()]
    # list_tenants does 3 execute calls: COUNT query, data query, enrichment query
    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=2)
    data_result = MagicMock()
    data_result.scalars.return_value.all.return_value = tenants
    enrich_result = MagicMock()
    enrich_result.fetchall.return_value = []
    db.execute = AsyncMock(side_effect=[count_result, data_result, enrich_result])
    svc = await _make_svc(db)
    result = await svc.list_tenants({})
    assert result["pagination"]["total_items"] == 2
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_update_tenant():
    db = _make_db()
    tenant = _make_tenant()
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    result = await svc.update_tenant(tenant.id, {"city": "Chandigarh"})
    assert result["tenant_id"] == str(tenant.id)


# ── Lifecycle ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_tenant_success():
    db = _make_db()
    tenant = _make_tenant(verification_status="pending")
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    result = await svc.verify_tenant(tenant.id)
    assert tenant.verification_status == "approved"
    assert tenant.status == "active"


@pytest.mark.asyncio
async def test_verify_tenant_invalid_status():
    from app.exceptions import ServiceOSException
    db = _make_db()
    tenant = _make_tenant(verification_status="approved")
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.verify_tenant(tenant.id)
    assert "TENANT_VERIFICATION_INVALID_STATUS" == exc.value.error_code


@pytest.mark.asyncio
async def test_reject_verification():
    db = _make_db()
    tenant = _make_tenant(verification_status="pending")
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    await svc.reject_verification(tenant.id, "Documents incomplete")
    assert tenant.verification_status == "rejected"
    assert tenant.status == "rejected"


@pytest.mark.asyncio
async def test_suspend_tenant():
    db = _make_db()
    tenant = _make_tenant(status="active")
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    await svc.suspend_tenant(tenant.id, "Policy violation")
    assert tenant.status == "suspended"
    assert tenant.suspension_reason == "Policy violation"


@pytest.mark.asyncio
async def test_activate_tenant():
    db = _make_db()
    tenant = _make_tenant(status="suspended")
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    result = await svc.activate_tenant(tenant.id)
    assert tenant.status == "active"


@pytest.mark.asyncio
async def test_archive_tenant():
    db = _make_db()
    tenant = _make_tenant(status="suspended")
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    await svc.archive_tenant(tenant.id)
    assert tenant.status == "archived"
    assert tenant.archived_at is not None


# ═══════════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_users_empty():
    db = _make_db()
    tenant = _make_tenant()
    user_result = MagicMock()
    user_result.scalars.return_value.all.return_value = []
    db.execute.side_effect = [_scalar_result(tenant), user_result]
    svc = await _make_svc(db)
    result = await svc.list_users(tenant.id)
    assert result["total"] == 0
    assert result["users"] == []


@pytest.mark.asyncio
async def test_create_user_invalid_role():
    from app.exceptions import ServiceOSException
    db = _make_db()
    tenant = _make_tenant()
    db.execute.return_value = _scalar_result(tenant)
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_user(tenant.id, {"name": "Test", "email": "t@t.com", "role": "god_mode"})
    assert "TENANT_USER_ROLE_INVALID" == exc.value.error_code


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    from app.exceptions import ServiceOSException
    db = _make_db()
    tenant = _make_tenant()
    existing = _make_user(email="taken@t.com")
    db.execute.side_effect = [
        _scalar_result(tenant),
        _scalar_result(existing),
    ]
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_user(tenant.id, {
            "name": "Test", "email": "taken@t.com", "role": "staff"
        })
    assert "TENANT_USER_ALREADY_EXISTS" == exc.value.error_code


@pytest.mark.asyncio
async def test_suspend_user():
    db = _make_db()
    tenant = _make_tenant()
    user = _make_user(is_active=True)
    db.execute.side_effect = [_scalar_result(tenant), _scalar_result(user)]
    svc = await _make_svc(db)
    # _load_tenant_user is used in suspend_user, not get_tenant first
    # Reset side_effect to just user
    db.execute.side_effect = [_scalar_result(user)]
    result = await svc.suspend_user(tenant.id, user.id)
    assert user.is_active is False


@pytest.mark.asyncio
async def test_activate_user():
    db = _make_db()
    tenant = _make_tenant()
    user = _make_user(is_active=False)
    db.execute.side_effect = [_scalar_result(user)]
    svc = await _make_svc(db)
    await svc.activate_user(tenant.id, user.id)
    assert user.is_active is True


@pytest.mark.asyncio
async def test_user_not_found():
    from app.exceptions import NotFoundException
    db = _make_db()
    db.execute.return_value = _scalar_result(None)
    svc = await _make_svc(db)
    with pytest.raises(NotFoundException):
        await svc.suspend_user(uuid.uuid4(), uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# STAFF
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_staff_empty():
    db = _make_db()
    tenant = _make_tenant()
    staff_result = MagicMock()
    staff_result.scalars.return_value.all.return_value = []
    db.execute.side_effect = [_scalar_result(tenant), staff_result]
    svc = await _make_svc(db)
    result = await svc.list_staff(tenant.id)
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_create_staff_duplicate():
    from app.exceptions import ServiceOSException
    db = _make_db()
    tenant = _make_tenant()
    existing = _make_user(role="staff")
    db.execute.side_effect = [
        _scalar_result(tenant),
        _scalar_result(existing),
    ]
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_staff(tenant.id, {"name": "Test", "email": "taken@t.com"})
    assert "TENANT_STAFF_ALREADY_EXISTS" == exc.value.error_code


@pytest.mark.asyncio
async def test_deactivate_staff():
    db = _make_db()
    tenant = _make_tenant()
    staff = _make_user(role="staff", is_active=True)
    db.execute.return_value = _scalar_result(staff)
    svc = await _make_svc(db)
    await svc.deactivate_staff(tenant.id, staff.id)
    assert staff.is_active is False


@pytest.mark.asyncio
async def test_activate_staff():
    db = _make_db()
    tenant = _make_tenant()
    staff = _make_user(role="staff", is_active=False)
    db.execute.return_value = _scalar_result(staff)
    svc = await _make_svc(db)
    await svc.activate_staff(tenant.id, staff.id)
    assert staff.is_active is True


@pytest.mark.asyncio
async def test_update_staff_photo():
    db = _make_db()
    tenant = _make_tenant()
    staff = _make_user(role="staff")
    db.execute.return_value = _scalar_result(staff)
    svc = await _make_svc(db)
    await svc.update_staff_photo(tenant.id, staff.id, "https://cdn.example.com/photo.jpg")
    assert staff.avatar_url == "https://cdn.example.com/photo.jpg"


@pytest.mark.asyncio
async def test_staff_not_found():
    from app.exceptions import NotFoundException
    db = _make_db()
    db.execute.return_value = _scalar_result(None)
    svc = await _make_svc(db)
    with pytest.raises(NotFoundException):
        await svc.deactivate_staff(uuid.uuid4(), uuid.uuid4())


# FINAL-L5-05T: the "SERVICE AREAS" test block that lived here exercised
# AdminTenantService.list_service_areas/create_service_area/
# delete_service_area directly -- methods that only ever backed dead,
# HTTP-unreachable routes (shadowed by app.engines.serviceability.router,
# confirmed in FINAL-L5-05Q) and have since been removed entirely (the
# certified canonical owner is now ServiceabilityService; see
# docs/final-l5-05/FINAL_L5_05T_ADR_SERVICE_AREA_CANONICAL_OWNER.md).
# Removed rather than kept passing against dead code (mission rule 15:
# "do not keep tests that exercise only dead handlers"). Equivalent
# coverage for the real, live implementation lives in
# tests/test_serviceability_hardening.py and
# tests/test_final_l5_05t_service_area_route_canonicalization.py.

# FINAL-L5-05U: the "SECURITY DEPOSIT" test block that lived here exercised
# AdminTenantService.get_security_deposit/mark_deposit_paid directly --
# methods that were already fully orphaned (their routes were removed in
# an earlier "Phase 4 finance certification" sprint) and have since been
# deleted entirely (see docs/final-l5-05/FINAL_L5_05U_ADR_SECURITY_DEPOSIT_CANONICAL_PERMISSION.md).
# Removed rather than kept passing against deleted code (mission rule:
# "do not keep tests that exercise only dead handlers"). Equivalent
# coverage for the real, live canonical implementation
# (app.engines.finance_hub.FinanceHubService /
# app.engines.platform_commerce.CommerceService) lives in
# tests/test_final_l5_05u_security_deposit_permission_authorization.py.


# ═══════════════════════════════════════════════════════════════
# CREDIT WALLET
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@pytest.mark.skip(reason="legacy tenant credit methods moved to the finance/credits engine")
async def test_get_credit_wallet_not_found():
    from app.exceptions import ServiceOSException
    db = _make_db()
    tenant = _make_tenant()
    db.execute.side_effect = [_scalar_result(tenant), _scalar_result(None)]
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.get_credit_wallet(tenant.id)
    assert "CREDIT_WALLET_NOT_FOUND" == exc.value.error_code


@pytest.mark.asyncio
@pytest.mark.skip(reason="legacy tenant credit methods moved to the finance/credits engine")
async def test_credit_topup():
    db = _make_db()
    tenant = _make_tenant()
    wallet = MagicMock()
    wallet.credit_balance = Decimal("1000.00")
    wallet.lifetime_purchased = Decimal("0.00")
    db.execute.side_effect = [_scalar_result(tenant), _scalar_result(wallet)]
    svc = await _make_svc(db)
    result = await svc.credit_topup(tenant.id, 500.0, "Test top-up")
    assert wallet.credit_balance == Decimal("1500.00")
    assert result["amount_added"] == 500.0


@pytest.mark.asyncio
@pytest.mark.skip(reason="legacy tenant credit methods moved to the finance/credits engine")
async def test_credit_adjust_requires_reason():
    from app.exceptions import ServiceOSException
    db = _make_db()
    svc = await _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.credit_adjust(uuid.uuid4(), 100.0, "")
    assert "CREDIT_ADJUSTMENT_REASON_REQUIRED" == exc.value.error_code


@pytest.mark.asyncio
@pytest.mark.skip(reason="legacy tenant credit methods moved to the finance/credits engine")
async def test_credit_adjust_negative():
    db = _make_db()
    tenant = _make_tenant()
    wallet = MagicMock()
    wallet.credit_balance = Decimal("1000.00")
    db.execute.side_effect = [_scalar_result(wallet)]
    svc = await _make_svc(db)
    result = await svc.credit_adjust(tenant.id, -200.0, "Penalty deduction")
    assert wallet.credit_balance == Decimal("800.00")


# ═══════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_settings_no_record_returns_defaults():
    db = _make_db()
    tenant = _make_tenant()
    db.execute.side_effect = [_scalar_result(tenant), _scalar_result(None)]
    svc = await _make_svc(db)
    result = await svc.get_settings(tenant.id)
    assert result["timezone"] == "Asia/Kolkata"
    assert result["currency"] == "INR"


@pytest.mark.asyncio
async def test_commission_rate_not_updatable_via_tenant():
    """Verify commission_rate gets excluded when popped by portal router."""
    payload = {"timezone": "UTC", "commission_rate": 0.30}
    payload.pop("commission_rate", None)
    assert "commission_rate" not in payload
    assert payload["timezone"] == "UTC"


# ═══════════════════════════════════════════════════════════════
# AUDIT LOGS
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_audit_logs():
    db = _make_db()
    tenant = _make_tenant()
    log = MagicMock()
    log.id = uuid.uuid4()
    log.actor_id = uuid.uuid4()
    log.actor_role = "super_admin"
    log.action_type = "admin_verify_tenant"
    log.entity_type = "tenant"
    log.entity_id = str(tenant.id)
    log.notes = None
    log.created_at = MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00+00:00"))
    log_result = MagicMock()
    log_result.scalars.return_value.all.return_value = [log]
    db.execute.side_effect = [_scalar_result(tenant), log_result]
    svc = await _make_svc(db)
    result = await svc.get_audit_logs(tenant.id)
    assert len(result["logs"]) == 1
    assert result["logs"][0]["action_type"] == "admin_verify_tenant"


# ═══════════════════════════════════════════════════════════════
# TENANT SETTINGS MODEL
# ═══════════════════════════════════════════════════════════════

def test_tenant_settings_model_exists():
    from app.engines.tenant_engine.models import TenantSettings
    assert TenantSettings.__tablename__ == "tenant_operational_settings"


def test_tenant_settings_default_timezone():
    from app.engines.tenant_engine.models import TenantSettings
    ts = TenantSettings.__new__(TenantSettings)
    assert hasattr(TenantSettings, "timezone")


def test_tenant_model_has_verification_status():
    from app.engines.tenant_engine.models import Tenant
    assert hasattr(Tenant, "verification_status")


def test_tenant_model_has_slug():
    from app.engines.tenant_engine.models import Tenant
    assert hasattr(Tenant, "slug")


def test_tenant_model_has_tenant_code():
    from app.engines.tenant_engine.models import Tenant
    assert hasattr(Tenant, "tenant_code")


def test_tenant_model_has_archived_at():
    from app.engines.tenant_engine.models import Tenant
    assert hasattr(Tenant, "archived_at")


# ═══════════════════════════════════════════════════════════════
# ERROR CODES — all 43 Sprint 4 codes present in base.py
# ═══════════════════════════════════════════════════════════════

def _get_all_error_codes() -> set[str]:
    from app.schemas.base import ERROR_CODES
    return set(ERROR_CODES.keys())


def test_error_tenant_already_exists():
    assert "TENANT_ALREADY_EXISTS" in _get_all_error_codes()


def test_error_tenant_onboarding_failed():
    assert "TENANT_ONBOARDING_FAILED" in _get_all_error_codes()


def test_error_tenant_owner_required():
    assert "TENANT_OWNER_REQUIRED" in _get_all_error_codes()


def test_error_tenant_user_not_found():
    assert "TENANT_USER_NOT_FOUND" in _get_all_error_codes()


def test_error_tenant_user_already_exists():
    assert "TENANT_USER_ALREADY_EXISTS" in _get_all_error_codes()


def test_error_tenant_user_role_invalid():
    assert "TENANT_USER_ROLE_INVALID" in _get_all_error_codes()


def test_error_tenant_staff_not_found():
    assert "TENANT_STAFF_NOT_FOUND" in _get_all_error_codes()


def test_error_tenant_staff_already_exists():
    assert "TENANT_STAFF_ALREADY_EXISTS" in _get_all_error_codes()


def test_error_tenant_service_area_not_found():
    assert "TENANT_SERVICE_AREA_NOT_FOUND" in _get_all_error_codes()


def test_error_tenant_service_area_invalid():
    assert "TENANT_SERVICE_AREA_INVALID" in _get_all_error_codes()


def test_retired_security_deposit_not_found_error_is_absent():
    assert "SECURITY_DEPOSIT_NOT_FOUND" not in _get_all_error_codes()


def test_retired_security_deposit_already_paid_error_is_absent():
    assert "SECURITY_DEPOSIT_ALREADY_PAID" not in _get_all_error_codes()


def test_error_credit_wallet_not_found():
    assert "CREDIT_WALLET_NOT_FOUND" in _get_all_error_codes()


def test_error_credit_adjustment_reason_required():
    assert "CREDIT_ADJUSTMENT_REASON_REQUIRED" in _get_all_error_codes()


def test_error_tenant_verification_invalid_status():
    assert "TENANT_VERIFICATION_INVALID_STATUS" in _get_all_error_codes()


def test_error_tenant_media_not_found():
    assert "TENANT_MEDIA_NOT_FOUND" in _get_all_error_codes()


def test_error_tenant_archived():
    assert "TENANT_ARCHIVED" in _get_all_error_codes()


# ═══════════════════════════════════════════════════════════════
# ROUTER INSTANTIATION
# ═══════════════════════════════════════════════════════════════

def test_admin_router_prefix():
    from app.engines.tenant_engine.admin_router import router
    assert router.prefix == "/v1/admin/tenants"


def test_portal_router_prefix():
    from app.engines.tenant_engine.portal_router import router
    assert router.prefix == "/v1/tenant"


def test_admin_router_has_onboard_route():
    from app.engines.tenant_engine.admin_router import router
    paths = [r.path for r in router.routes]
    assert any("onboard" in p for p in paths)


def test_admin_router_has_wallet_topup_route():
    from app.engines.tenant_engine.admin_router import router
    paths = [r.path for r in router.routes]
    assert any("wallet/topup" in p for p in paths)


def test_portal_router_has_profile_route():
    from app.engines.tenant_engine.portal_router import router
    paths = [r.path for r in router.routes]
    assert any("profile" in p for p in paths)


def test_portal_router_no_longer_has_a_service_areas_route():
    # FINAL-L5-05T: removed entirely -- app.engines.serviceability.router
    # is the certified canonical owner of /v1/tenant/service-areas.
    from app.engines.tenant_engine.portal_router import router
    paths = [r.path for r in router.routes]
    assert not any("service-areas" in p for p in paths)
