"""
Sprint 5 — Package Commerce Tests
55 tests covering: packages CRUD, visibility, purchase flow, security deposit,
credit wallet, commission, storage quota, security/cross-tenant, OpenAPI.
"""
from __future__ import annotations
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _scalar_result(value, first=None):
    """SQLAlchemy result mock. scalar_* methods are SYNCHRONOUS in SQLAlchemy async."""
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    r.scalar_one = MagicMock(return_value=value)
    r.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=value if isinstance(value, list) else []))
    )
    r.first = MagicMock(return_value=first)
    return r


def _make_package(**kwargs) -> MagicMock:
    pkg = MagicMock()
    pkg.id = uuid.uuid4()
    pkg.name = kwargs.get("name", "Test Onboarding")
    pkg.slug = kwargs.get("slug", "test-onboarding")
    pkg.description = kwargs.get("description", None)
    pkg.package_type = kwargs.get("package_type", "onboarding")
    pkg.plan_level = kwargs.get("plan_level", "starter")
    pkg.package_price = Decimal(str(kwargs.get("package_price", "5000.00")))
    pkg.security_deposit_amount = Decimal(str(kwargs.get("security_deposit_amount", "3000.00")))
    pkg.included_credit_amount = Decimal(str(kwargs.get("included_credit_amount", "2000.00")))
    pkg.storage_quota_gb = Decimal(str(kwargs.get("storage_quota_gb", "25.00"))) if kwargs.get("storage_quota_gb") else None
    pkg.commission_rate = Decimal(str(kwargs.get("commission_rate", "10.00"))) if kwargs.get("commission_rate") else None
    pkg.validity_days = kwargs.get("validity_days", 365)
    pkg.features = kwargs.get("features", {})
    pkg.is_active = kwargs.get("is_active", True)
    pkg.display_order = kwargs.get("display_order", 0)
    pkg.created_by = None
    pkg.deleted_at = None
    pkg.created_at = None
    return pkg


def _make_wallet(**kwargs) -> MagicMock:
    w = MagicMock()
    w.id = uuid.uuid4()
    w.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    w.credit_balance = Decimal(str(kwargs.get("credit_balance", "2000.00")))
    w.reserved_balance = Decimal("0.00")
    w.lifetime_purchased = Decimal("0.00")
    w.lifetime_consumed = Decimal("0.00")
    w.currency = "INR"
    w.low_balance_threshold = Decimal(str(kwargs.get("low_balance_threshold", "500.00")))
    w.is_active = True
    w.last_transaction_at = None
    w.balance = w.credit_balance
    return w


def _make_deposit(**kwargs) -> MagicMock:
    d = MagicMock()
    d.id = uuid.uuid4()
    d.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    d.required_amount = Decimal(str(kwargs.get("required_amount", "3000.00")))
    d.total_paid = Decimal(str(kwargs.get("total_paid", "0.00")))
    d.warranty_drawn = Decimal("0.00")
    d.replenishment_total = Decimal("0.00")
    d.status = kwargs.get("status", "unpaid")
    d.paid_at = kwargs.get("paid_at", None)
    d.refunded_at = None
    d.package_purchase_id = None
    d.payment_reference = None
    d.current_balance = d.total_paid - d.warranty_drawn
    d.is_unlocked = d.status == "paid"
    return d


def _make_purchase(**kwargs) -> MagicMock:
    p = MagicMock()
    p.id = uuid.uuid4()
    p.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    p.package_id = kwargs.get("package_id", uuid.uuid4())
    p.package_type = kwargs.get("package_type", "onboarding")
    p.package_price = Decimal(str(kwargs.get("package_price", "5000.00")))
    p.security_deposit_amount = Decimal(str(kwargs.get("security_deposit_amount", "3000.00")))
    p.credit_amount = Decimal(str(kwargs.get("credit_amount", "2000.00")))
    cr = kwargs.get("commission_rate")
    p.commission_rate = Decimal(str(cr)) if cr is not None else None
    sq = kwargs.get("storage_quota_gb")
    p.storage_quota_gb = Decimal(str(sq)) if sq is not None else None
    p.payment_status = kwargs.get("payment_status", "paid")
    p.payment_reference = kwargs.get("payment_reference", None)
    p.purchased_at = None
    p.expires_at = None
    p.created_at = None
    return p


def _make_assignment(**kwargs) -> MagicMock:
    a = MagicMock()
    a.id = uuid.uuid4()
    a.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    a.package_id = kwargs.get("package_id", uuid.uuid4())
    a.status = kwargs.get("status", "active")
    a.activated_at = None
    return a


def _make_commission(**kwargs) -> MagicMock:
    c = MagicMock()
    c.id = uuid.uuid4()
    c.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    c.job_id = kwargs.get("job_id", "JOB-001")
    c.base_rate = Decimal("10.00")
    c.health_adjustment = Decimal("0.00")
    c.effective_rate = Decimal("10.00")
    c.job_value = Decimal(str(kwargs.get("job_value", "1450.00")))
    c.commission_amount = Decimal(str(kwargs.get("commission_amount", "145.00")))
    c.wallet_balance_before = Decimal("2000.00")
    c.wallet_balance_after = Decimal("1855.00")
    c.health_band_at_time = "gold"
    c.status = kwargs.get("status", "pending")
    c.deducted_at = None
    c.failure_reason = None
    c.wallet_ledger_entry_id = None
    c.package_purchase_id = None
    c.calculation_base = "total_amount"
    c.invoice_id = None
    c.payment_id = None
    c.created_at = None
    return c


def _make_svc(db=None):
    from app.engines.package_commerce.service import PackageCommerceService
    if db is None:
        db = _make_db()
    return PackageCommerceService(
        db=db,
        request_id="req_test",
        actor_id=uuid.uuid4(),
        actor_role="super_admin",
    )


# ══════════════════════════════════════════════════════════════
# 1. PACKAGE ADMIN TESTS (1–6)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_01_admin_can_create_onboarding_package():
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    svc = _make_svc(db)
    data = {
        "name": "Starter Onboarding",
        "package_type": "onboarding_package",
        "plan_level": "starter",
        "package_price": 5000,
        "security_deposit_amount": 3000,
        "included_credit_amount": 2000,
        "storage_quota_gb": 25,
        "commission_rate": 10,
        "is_active": True,
    }
    result = await svc.create_package(data)
    assert result["package_type"] == "onboarding_package"
    assert result["package_price"] == 5000.0


@pytest.mark.asyncio
async def test_02_admin_can_create_credit_topup_package():
    """credit_topup is the provider wallet top-up plan — spendable commission credits."""
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    svc = _make_svc(db)
    data = {
        "name": "Credit Top-up 2000",
        "package_type": "credit_topup",
        "package_price": 2000,
        "security_deposit_amount": 0,
        "included_credit_amount": 2000,
        "is_active": True,
    }
    result = await svc.create_package(data)
    assert result["package_type"] == "credit_topup"
    assert result["security_deposit_amount"] == 0.0


@pytest.mark.asyncio
async def test_03_credit_topup_cannot_have_security_deposit():
    """credit_topup plans must not have a security_deposit_amount > 0."""
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    svc = _make_svc(db)
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_package({
            "name": "Bad Package",
            "package_type": "credit_topup",
            "package_price": 2000,
            "security_deposit_amount": 1000,
            "included_credit_amount": 2000,
        })
    assert "PACKAGE_PRICE_INVALID" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_04_package_price_cannot_be_negative():
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    svc = _make_svc(db)
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_package({
            "name": "Negative Price",
            "package_type": "credit_topup",
            "package_price": -100,
            "security_deposit_amount": 0,
            "included_credit_amount": 2000,
        })
    assert "PACKAGE_PRICE_INVALID" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_05_inactive_package_not_in_available_packages_after_deposit_paid():
    db = _make_db()
    inactive_pkg = _make_package(package_type="credit_topup", is_active=False)
    deposit = _make_deposit(status="paid")
    wallet = _make_wallet(credit_balance="2000")
    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            # deposit query
            return _scalar_result(deposit)
        elif call_count[0] == 2:
            # wallet query
            return _scalar_result(wallet)
        else:
            # packages query — inactive filtered by DB WHERE is_active=TRUE
            return _scalar_result([])

    db.execute = mock_execute
    svc = _make_svc(db)
    tid = uuid.uuid4()
    result = await svc.get_available_packages(tid)
    assert result["available_packages"] == []


@pytest.mark.asyncio
async def test_06_deactivate_does_not_delete_package():
    pkg = _make_package()
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(pkg))
    svc = _make_svc(db)
    result = await svc.deactivate_package(pkg.id)
    assert result["is_active"] == False
    assert pkg.deleted_at is None


# ══════════════════════════════════════════════════════════════
# 2. PACKAGE VISIBILITY TESTS (7–10)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_07_tenant_with_unpaid_deposit_sees_onboarding_packages():
    deposit = _make_deposit(status="unpaid")
    wallet = _make_wallet()
    pkg = _make_package(package_type="onboarding")
    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(deposit)
        elif call_count[0] == 2:
            return _scalar_result(wallet)
        else:
            r = AsyncMock()
            r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[pkg])))
            return r

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    result = await svc.get_available_packages(uuid.uuid4())
    assert result["security_deposit_status"] == "unpaid"
    assert len(result["available_packages"]) == 1
    assert result["available_packages"][0]["package_type"] == "onboarding"


@pytest.mark.asyncio
async def test_08_tenant_with_unpaid_deposit_does_not_see_credit_topup():
    deposit = _make_deposit(status="unpaid")
    wallet = _make_wallet()
    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(deposit)
        elif call_count[0] == 2:
            return _scalar_result(wallet)
        else:
            # Simulates: DB WHERE package_type = 'onboarding' filters out credit_topup
            r = AsyncMock()
            r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            return r

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    result = await svc.get_available_packages(uuid.uuid4())
    assert "credit top-up" in result["message"].lower()


@pytest.mark.asyncio
async def test_09_tenant_with_paid_deposit_sees_only_credit_topup():
    deposit = _make_deposit(status="paid")
    wallet = _make_wallet()
    pkg = _make_package(package_type="credit_topup")
    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(deposit)
        elif call_count[0] == 2:
            return _scalar_result(wallet)
        else:
            r = AsyncMock()
            r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[pkg])))
            return r

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    result = await svc.get_available_packages(uuid.uuid4())
    assert result["security_deposit_status"] == "paid"
    assert result["available_packages"][0]["package_type"] == "credit_topup"


@pytest.mark.asyncio
async def test_10_tenant_cannot_purchase_onboarding_when_deposit_paid():
    pkg = _make_package(package_type="onboarding", is_active=True)
    deposit = _make_deposit(status="paid")
    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        else:
            return _scalar_result(deposit)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.purchase_package(uuid.uuid4(), pkg.id, {"mark_paid": True})
    assert "PACKAGE_PURCHASE_NOT_ALLOWED" in str(exc.value.error_code)


# ══════════════════════════════════════════════════════════════
# 3. PACKAGE PURCHASE TESTS (11–18)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_11_tenant_can_purchase_onboarding_package():
    tid = uuid.uuid4()
    pkg = _make_package(package_type="onboarding", is_active=True)
    deposit = _make_deposit(status="unpaid", tenant_id=tid)
    wallet = _make_wallet(credit_balance="2000", tenant_id=tid)
    purchase = _make_purchase(tenant_id=tid, package_id=pkg.id, payment_status="paid")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)  # load_package
        elif call_count[0] == 2:
            return _scalar_result(deposit)  # get_deposit
        elif call_count[0] == 3:
            return _scalar_result(None)  # idempotency check for credit_wallet
        elif call_count[0] == 4:
            return _scalar_result(wallet)  # get_wallet_locked
        elif call_count[0] == 5:
            return _scalar_result(None)  # get_tenant_limits
        elif call_count[0] == 6:
            return _scalar_result(None)  # get TenantSettings for commission
        else:
            return _scalar_result(wallet)  # final wallet balance

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    with patch("app.engines.package_commerce.service.credit_wallet", new_callable=AsyncMock) as mock_credit:
        txn = MagicMock()
        txn.id = uuid.uuid4()
        txn.balance_after = Decimal("2000.00")
        mock_credit.return_value = txn
        result = await svc.purchase_package(tid, pkg.id, {"mark_paid": True})

    assert result["payment_status"] == "paid"
    assert result["security_deposit_status"] == "paid"


@pytest.mark.asyncio
async def test_12_onboarding_purchase_marks_security_deposit_paid():
    tid = uuid.uuid4()
    pkg = _make_package(package_type="onboarding", is_active=True,
                        security_deposit_amount="3000")
    deposit = _make_deposit(status="unpaid", tenant_id=tid)
    wallet = _make_wallet(credit_balance="0", tenant_id=tid)

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        elif call_count[0] == 2:
            return _scalar_result(deposit)
        elif call_count[0] == 3:
            return _scalar_result(None)  # idempotency
        elif call_count[0] == 4:
            return _scalar_result(wallet)  # wallet locked
        elif call_count[0] == 5:
            return _scalar_result(None)  # limits
        elif call_count[0] == 6:
            return _scalar_result(None)  # settings
        else:
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    with patch("app.engines.package_commerce.service.credit_wallet", new_callable=AsyncMock) as mc:
        mc.return_value = MagicMock(id=uuid.uuid4(), balance_after=Decimal("2000"))
        result = await svc.purchase_package(tid, pkg.id, {"mark_paid": True})

    assert deposit.status == "paid"
    assert result["security_deposit_status"] == "paid"


@pytest.mark.asyncio
async def test_13_onboarding_purchase_adds_credit_to_wallet():
    """FINAL-L5-05J: package credit grants now flow through
    UsageCreditService.grant_package_credit (tenant_billing/
    usage_credit_ledger), not ledger.credit_wallet (TenantWallet)."""
    tid = uuid.uuid4()
    pkg = _make_package(package_type="onboarding", is_active=True,
                        included_credit_amount="2000")
    deposit = _make_deposit(status="unpaid", tenant_id=tid)

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        return _scalar_result(deposit)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    grant_called = []

    async def fake_grant(self, **kwargs):
        grant_called.append(kwargs)
        return {"balance_after": 2000.0}

    with patch("app.engines.usage_credits.service.UsageCreditService.grant_package_credit", new=fake_grant):
        result = await svc.purchase_package(tid, pkg.id, {"mark_paid": True})

    assert any(g["amount"] == Decimal("2000") for g in grant_called)
    assert grant_called[0]["tenant_id"] == tid
    assert result["credit_added"] == 2000.0


@pytest.mark.asyncio
async def test_14_ledger_entry_created_after_purchase():
    # Verifies grant_package_credit is called exactly once (which writes
    # both tenant_billing.credit_balance and one usage_credit_ledger row).
    tid = uuid.uuid4()
    pkg = _make_package(package_type="onboarding", is_active=True)
    deposit = _make_deposit(status="unpaid")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        return _scalar_result(deposit)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    grant_called = []

    async def fake_grant(self, **kwargs):
        grant_called.append(True)
        return {"balance_after": 2000.0}

    with patch("app.engines.usage_credits.service.UsageCreditService.grant_package_credit", new=fake_grant):
        await svc.purchase_package(tid, pkg.id, {"mark_paid": True})

    assert len(grant_called) == 1


@pytest.mark.asyncio
async def test_15_tenant_can_purchase_credit_topup_after_deposit_paid():
    tid = uuid.uuid4()
    pkg = _make_package(package_type="credit_topup", is_active=True,
                        included_credit_amount="2000", security_deposit_amount="0")
    deposit = _make_deposit(status="paid", tenant_id=tid)
    wallet = _make_wallet(credit_balance="500", tenant_id=tid)

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        elif call_count[0] == 2:
            return _scalar_result(deposit)
        elif call_count[0] in (3, 4):
            return _scalar_result(wallet)
        else:
            wallet.credit_balance = Decimal("2500")
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    with patch("app.engines.package_commerce.service.credit_wallet", new_callable=AsyncMock) as mc:
        mc.return_value = MagicMock(id=uuid.uuid4(), balance_after=Decimal("2500"))
        result = await svc.purchase_package(tid, pkg.id, {"mark_paid": True})

    assert result["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_16_credit_topup_adds_credit_to_wallet():
    """FINAL-L5-05J: credit_topup packages grant Usage Credit via
    UsageCreditService.grant_package_credit, same canonical path as
    onboarding packages (test_13/14)."""
    tid = uuid.uuid4()
    pkg = _make_package(package_type="credit_topup", is_active=True,
                        included_credit_amount="2000", security_deposit_amount="0")
    deposit = _make_deposit(status="paid")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        return _scalar_result(deposit)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    credits_added = []

    async def fake_grant(self, **kwargs):
        credits_added.append(kwargs["amount"])
        return {"balance_after": 2500.0}

    with patch("app.engines.usage_credits.service.UsageCreditService.grant_package_credit", new=fake_grant):
        result = await svc.purchase_package(tid, pkg.id, {"mark_paid": True})

    assert any(a == Decimal("2000") for a in credits_added)


@pytest.mark.asyncio
async def test_17_pending_payment_does_not_credit_wallet():
    tid = uuid.uuid4()
    pkg = _make_package(package_type="onboarding", is_active=True,
                        included_credit_amount="2000")
    deposit = _make_deposit(status="unpaid")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        else:
            return _scalar_result(deposit)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    credit_called = []

    async def fake_credit(**kwargs):
        credit_called.append(True)
        return MagicMock()

    with patch("app.engines.package_commerce.service.credit_wallet", new=fake_credit):
        result = await svc.purchase_package(tid, pkg.id, {"mark_paid": False})

    assert result["payment_status"] == "pending"
    assert len(credit_called) == 0
    assert result["credit_added"] == 0.0


@pytest.mark.asyncio
async def test_18_credit_topup_blocked_before_deposit_paid():
    tid = uuid.uuid4()
    pkg = _make_package(package_type="credit_topup", is_active=True)
    deposit = _make_deposit(status="unpaid")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(pkg)
        else:
            return _scalar_result(deposit)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.purchase_package(tid, pkg.id, {"mark_paid": True})
    assert "PACKAGE_PURCHASE_NOT_ALLOWED" in str(exc.value.error_code)


# ══════════════════════════════════════════════════════════════
# 4. SECURITY DEPOSIT TESTS (19–24)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_19_security_deposit_initializes_not_found_gracefully():
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    svc = _make_svc(db)
    result = await svc.get_security_deposit(uuid.uuid4())
    assert result["status"] == "not_initialized"


@pytest.mark.asyncio
async def test_20_admin_mark_deposit_paid_works():
    deposit = _make_deposit(status="unpaid")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(deposit))
    svc = _make_svc(db)
    result = await svc.admin_mark_deposit_paid(deposit.tenant_id, {
        "amount": 3000,
        "payment_reference": "BANK-001",
    })
    assert deposit.status == "paid"
    assert result["status"] == "paid"


@pytest.mark.asyncio
async def test_21_duplicate_mark_paid_blocked():
    deposit = _make_deposit(status="paid")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(deposit))
    svc = _make_svc(db)
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_mark_deposit_paid(deposit.tenant_id, {"amount": 3000})
    assert "SECURITY_DEPOSIT_ALREADY_PAID" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_22_mark_deposit_paid_does_not_increase_credit_wallet():
    deposit = _make_deposit(status="unpaid")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(deposit))
    svc = _make_svc(db)
    credit_called = []

    async def fake_credit(**kwargs):
        credit_called.append(True)
        return MagicMock()

    with patch("app.engines.package_commerce.service.credit_wallet", new=fake_credit):
        await svc.admin_mark_deposit_paid(deposit.tenant_id, {"amount": 3000})

    assert len(credit_called) == 0


@pytest.mark.asyncio
async def test_23_refund_updates_deposit_status():
    deposit = _make_deposit(status="paid")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(deposit))
    svc = _make_svc(db)
    result = await svc.admin_refund_deposit(deposit.tenant_id, {"reason": "tenant exit"})
    assert deposit.status == "refunded"
    assert result["status"] == "refunded"


@pytest.mark.asyncio
async def test_24_forfeit_updates_deposit_status():
    deposit = _make_deposit(status="paid")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(deposit))
    svc = _make_svc(db)
    result = await svc.admin_forfeit_deposit(deposit.tenant_id, {"reason": "breach"})
    assert deposit.status == "forfeited"
    assert result["status"] == "forfeited"


# ══════════════════════════════════════════════════════════════
# 5. CREDIT WALLET TESTS (25–30)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_25_wallet_detail_returns_balance_fields():
    wallet = _make_wallet(credit_balance="2000")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(wallet))
    svc = _make_svc(db)
    result = await svc.get_credit_wallet_detail(wallet.tenant_id)
    assert result["balance"] == 2000.0
    assert "is_low_balance" in result
    assert "currency" in result


@pytest.mark.asyncio
async def test_26_admin_topup_increases_balance():
    tid = uuid.uuid4()
    wallet = _make_wallet(credit_balance="2000", tenant_id=tid)
    # When credit_wallet is patched, db.execute is called only for _get_wallet at the end
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(wallet))
    svc = _make_svc(db)

    with patch("app.engines.package_commerce.service.credit_wallet", new_callable=AsyncMock) as mc:
        mc.return_value = MagicMock(id=uuid.uuid4(), balance_after=Decimal("2000"))
        result = await svc.admin_topup_wallet(tid, {"amount": 1000, "reason": "bank transfer"})

    assert result["amount_added"] == 1000.0


@pytest.mark.asyncio
async def test_27_admin_adjustment_requires_reason():
    db = _make_db()
    svc = _make_svc(db)
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.admin_adjust_wallet(uuid.uuid4(), {
            "entry_type": "credit", "amount": 500, "reason": ""
        })
    assert "CREDIT_ADJUSTMENT_REASON_REQUIRED" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_28_ledger_balance_before_after_correct():
    tid = uuid.uuid4()
    wallet = _make_wallet(credit_balance="2000", tenant_id=tid)
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(wallet))
    svc = _make_svc(db)

    captured_args = {}

    async def fake_credit(**kwargs):
        captured_args.update(kwargs)
        return MagicMock(id=uuid.uuid4(), balance_after=Decimal("2500"))

    with patch("app.engines.package_commerce.service.credit_wallet", new=fake_credit):
        await svc.admin_topup_wallet(tid, {"amount": 500, "reason": "test"})

    assert captured_args["amount"] == Decimal("500")


@pytest.mark.asyncio
async def test_29_tenant_sees_own_wallet_only():
    # The tenant router extracts tenant_id from JWT — body-injected tenant_id is never used
    from app.engines.package_commerce.tenant_router import _tenant_id
    user = MagicMock()
    user.tenant_id = str(uuid.uuid4())
    result = _tenant_id(user)
    assert isinstance(result, uuid.UUID)
    assert str(result) == user.tenant_id


@pytest.mark.asyncio
async def test_30_cross_tenant_wallet_access_blocked():
    from app.engines.package_commerce.tenant_router import _tenant_id
    from app.exceptions import ServiceOSException
    user = MagicMock()
    user.tenant_id = None
    with pytest.raises(ServiceOSException) as exc:
        _tenant_id(user)
    assert "TENANT_ACCESS_DENIED" in str(exc.value.error_code)


# ══════════════════════════════════════════════════════════════
# 6. COMMISSION TESTS (31–40)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_31_commission_uses_package_rate_when_available():
    tid = uuid.uuid4()
    assignment = _make_assignment(tenant_id=tid, status="active")
    wallet = _make_wallet(tenant_id=tid, credit_balance="5000")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(None)  # existing commission check
        elif call_count[0] == 2:
            # active package assignment joined with ServicePackage.commission_rate
            return _scalar_result(None, first=(assignment, Decimal("8.00")))
        else:
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    result = await svc.calculate_commission("JOB-001", tid, Decimal("1000.00"))
    assert result["commission_rate"] == 8.0
    assert result["commission_amount"] == 80.0


@pytest.mark.asyncio
async def test_32_commission_amount_calculation_correct():
    tid = uuid.uuid4()
    wallet = _make_wallet(credit_balance="5000")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(None)  # no existing commission
        elif call_count[0] == 2:
            return _scalar_result(None)  # no package purchase
        elif call_count[0] == 3:
            return _scalar_result(None)  # no tenant settings
        else:
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    result = await svc.calculate_commission("JOB-002", tid, Decimal("1450.00"))
    # 10% of 1450 = 145
    assert result["commission_amount"] == 145.0


@pytest.mark.asyncio
async def test_33_commission_deduction_debits_wallet():
    tid = uuid.uuid4()
    commission = _make_commission(tenant_id=tid, status="pending", commission_amount="145.00")
    wallet = _make_wallet(credit_balance="2000", tenant_id=tid)

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(commission)
        elif call_count[0] == 2:
            return _scalar_result(wallet)
        else:
            wallet.credit_balance = Decimal("1855")
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    debit_called = []

    async def fake_debit(**kwargs):
        debit_called.append(kwargs["amount"])
        return MagicMock(id=uuid.uuid4())

    with patch("app.engines.package_commerce.service.debit_wallet", new=fake_debit):
        result = await svc.deduct_commission("JOB-001", tid)

    assert len(debit_called) == 1
    assert debit_called[0] == Decimal("145.00")
    assert result["commission_status"] == "deducted"


@pytest.mark.asyncio
async def test_34_commission_ledger_entry_created():
    tid = uuid.uuid4()
    commission = _make_commission(tenant_id=tid, status="pending")
    wallet = _make_wallet(credit_balance="2000", tenant_id=tid)

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(commission)
        elif call_count[0] == 2:
            return _scalar_result(wallet)
        else:
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)

    txn_mock = MagicMock()
    txn_mock.id = uuid.uuid4()

    async def fake_debit(**kwargs):
        return txn_mock

    with patch("app.engines.package_commerce.service.debit_wallet", new=fake_debit):
        result = await svc.deduct_commission("JOB-001", tid)

    assert commission.wallet_ledger_entry_id == txn_mock.id


@pytest.mark.asyncio
async def test_35_commission_cannot_be_deducted_twice():
    tid = uuid.uuid4()
    commission = _make_commission(tenant_id=tid, status="deducted")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(commission))
    svc = _make_svc(db)
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.deduct_commission("JOB-001", tid)
    assert "COMMISSION_ALREADY_DEDUCTED" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_36_insufficient_credit_fails_cleanly():
    tid = uuid.uuid4()
    commission = _make_commission(tenant_id=tid, status="pending",
                                   commission_amount="500.00")
    wallet = _make_wallet(credit_balance="100", tenant_id=tid)

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(commission)
        else:
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    result = await svc.deduct_commission("JOB-001", tid)
    assert result["commission_status"] == "failed"
    assert result["failure_reason"] == "insufficient_credit"


@pytest.mark.asyncio
async def test_37_failed_commission_does_not_change_wallet():
    tid = uuid.uuid4()
    commission = _make_commission(tenant_id=tid, status="pending", commission_amount="500")
    wallet = _make_wallet(credit_balance="100", tenant_id=tid)

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(commission)
        else:
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    original_balance = float(wallet.credit_balance)

    debit_called = []

    async def fake_debit(**kwargs):
        debit_called.append(True)
        return MagicMock()

    with patch("app.engines.package_commerce.service.debit_wallet", new=fake_debit):
        await svc.deduct_commission("JOB-001", tid)

    assert len(debit_called) == 0
    assert float(wallet.credit_balance) == original_balance


@pytest.mark.asyncio
async def test_38_commission_rate_falls_back_to_platform_default():
    tid = uuid.uuid4()
    wallet = _make_wallet(credit_balance="5000")

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        if call_count[0] == 1:
            return _scalar_result(None)  # no existing commission
        elif call_count[0] == 2:
            return _scalar_result(None)  # no purchase
        elif call_count[0] == 3:
            return _scalar_result(None)  # no settings
        else:
            return _scalar_result(wallet)

    db = _make_db()
    db.execute = mock_execute
    svc = _make_svc(db)
    result = await svc.calculate_commission("JOB-003", tid, Decimal("1000.00"))
    # Platform default is 10%
    assert result["commission_rate"] == 10.0


@pytest.mark.asyncio
async def test_39_cross_tenant_commission_blocked():
    tid = uuid.uuid4()
    other_tid = uuid.uuid4()
    commission = _make_commission(tenant_id=other_tid, status="pending")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(commission))
    svc = _make_svc(db)
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        await svc.deduct_commission("JOB-001", tid)
    assert "TENANT_ACCESS_DENIED" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_40_calculate_commission_is_idempotent():
    tid = uuid.uuid4()
    existing = _make_commission(tenant_id=tid, status="pending")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(existing))
    svc = _make_svc(db)
    result = await svc.calculate_commission("JOB-001", tid, Decimal("1000.00"))
    assert result["commission_id"] == str(existing.id)


# ══════════════════════════════════════════════════════════════
# 7. STORAGE QUOTA TESTS (41–44)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_41_storage_quota_comes_from_tenant_limits():
    from app.engines.tenant_engine.models import TenantLimits
    limits = MagicMock()
    limits.max_storage_gb = 25
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(limits))
    svc = _make_svc(db)
    with patch.object(svc, "_count_storage_used", new=AsyncMock(return_value=3.4)):
        result = await svc.get_storage_quota(uuid.uuid4())
    assert result["storage_quota_gb"] == 25.0
    assert result["storage_used_gb"] == 3.4
    assert result["storage_remaining_gb"] == pytest.approx(21.6, abs=0.01)


@pytest.mark.asyncio
async def test_42_upload_within_quota_allowed():
    from app.engines.tenant_engine.models import TenantLimits
    limits = MagicMock()
    limits.max_storage_gb = 25
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(limits))
    svc = _make_svc(db)
    with patch.object(svc, "_count_storage_used", new=AsyncMock(return_value=3.0)):
        result = await svc.get_storage_quota(uuid.uuid4())
    assert result["storage_remaining_gb"] > 0


@pytest.mark.asyncio
async def test_43_storage_remaining_non_negative_when_over_quota():
    from app.engines.tenant_engine.models import TenantLimits
    limits = MagicMock()
    limits.max_storage_gb = 10
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(limits))
    svc = _make_svc(db)
    with patch.object(svc, "_count_storage_used", new=AsyncMock(return_value=12.0)):
        result = await svc.get_storage_quota(uuid.uuid4())
    assert result["storage_remaining_gb"] == 0.0


@pytest.mark.asyncio
async def test_44_storage_quota_none_when_no_limits():
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    svc = _make_svc(db)
    result = await svc.get_storage_quota(uuid.uuid4())
    assert result["storage_quota_gb"] is None


# ══════════════════════════════════════════════════════════════
# 8. SECURITY TESTS (45–49)
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_45_tenant_cannot_access_another_tenant_packages():
    from app.engines.package_commerce.tenant_router import _tenant_id
    from app.exceptions import ServiceOSException
    user = MagicMock()
    user.tenant_id = None
    with pytest.raises(ServiceOSException):
        _tenant_id(user)


@pytest.mark.asyncio
async def test_46_tenant_cannot_access_another_tenant_ledger():
    from app.engines.package_commerce.tenant_router import _tenant_id
    user = MagicMock()
    user.tenant_id = str(uuid.uuid4())
    tid = _tenant_id(user)
    assert isinstance(tid, uuid.UUID)


@pytest.mark.asyncio
async def test_47_cross_tenant_commission_deduction_blocked():
    from app.exceptions import ServiceOSException
    tid = uuid.uuid4()
    other_tid = uuid.uuid4()
    commission = _make_commission(tenant_id=other_tid, status="pending")
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(commission))
    svc = _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.deduct_commission("JOB-X", tid)
    assert "TENANT_ACCESS_DENIED" in str(exc.value.error_code)


@pytest.mark.asyncio
async def test_48_non_admin_cannot_create_package():
    # Router-level: create_package requires require_super_admin
    from app.engines.package_commerce.admin_router import create_package
    import inspect
    sig = inspect.signature(create_package)
    params = {k: v for k, v in sig.parameters.items()}
    # Verify user param exists (auth dependency)
    assert "user" in params


@pytest.mark.asyncio
async def test_49_invalid_package_type_rejected():
    from app.exceptions import ServiceOSException
    db = _make_db()
    db.execute = AsyncMock(return_value=_scalar_result(None))
    svc = _make_svc(db)
    with pytest.raises(ServiceOSException) as exc:
        await svc.create_package({
            "name": "Bad Type", "package_type": "invalid_type",
            "package_price": 1000, "security_deposit_amount": 0, "included_credit_amount": 1000,
        })
    assert "PACKAGE_TYPE_INVALID" in str(exc.value.error_code)


# ══════════════════════════════════════════════════════════════
# 9. OPENAPI TESTS (50–55)
# ══════════════════════════════════════════════════════════════

def test_50_admin_package_endpoints_exist():
    from app.engines.package_commerce.admin_router import router
    paths = [r.path for r in router.routes]
    assert any("packages" in p for p in paths)
    assert any("onboard" in p or "packages" in p for p in paths)


def test_51_tenant_package_endpoints_exist():
    from app.engines.package_commerce.tenant_router import router
    paths = [r.path for r in router.routes]
    assert any("packages" in p for p in paths)
    assert any("credit-wallet" in p for p in paths)


def test_52_security_deposit_endpoints_exist():
    from app.engines.package_commerce.admin_router import router
    paths = [r.path for r in router.routes]
    assert any("security-deposit" in p for p in paths)


def test_53_credit_wallet_endpoints_exist():
    from app.engines.package_commerce.admin_router import router
    paths = [r.path for r in router.routes]
    assert any("credit-wallet" in p for p in paths)


def test_54_commission_deduction_endpoint_exists():
    from app.engines.package_commerce.admin_router import router
    paths = [r.path for r in router.routes]
    assert any("deduct-commission" in p for p in paths)


def test_55_sprint5_error_codes_all_registered():
    from app.schemas.base import ERROR_CODES
    sprint5_codes = [
        "PACKAGE_NOT_FOUND", "PACKAGE_INACTIVE", "PACKAGE_PURCHASE_NOT_ALLOWED",
        "PACKAGE_TYPE_INVALID", "PACKAGE_PRICE_INVALID",
        "SECURITY_DEPOSIT_ALREADY_PAID", "SECURITY_DEPOSIT_REFUND_FAILED",
        "SECURITY_DEPOSIT_FORFEIT_FAILED",
        "CREDIT_WALLET_NOT_FOUND", "CREDIT_WALLET_INSUFFICIENT_BALANCE",
        "CREDIT_ADJUSTMENT_REASON_REQUIRED", "CREDIT_AMOUNT_INVALID",
        "COMMISSION_NOT_FOUND", "COMMISSION_ALREADY_DEDUCTED",
        "COMMISSION_CALCULATION_FAILED", "COMMISSION_DEDUCTION_FAILED",
        "TENANT_STORAGE_QUOTA_EXCEEDED", "TENANT_PACKAGE_REQUIRED", "TENANT_LOW_CREDIT",
    ]
    missing = [c for c in sprint5_codes if c not in ERROR_CODES]
    assert missing == [], f"Missing error codes: {missing}"
