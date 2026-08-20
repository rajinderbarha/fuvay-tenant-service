"""FINAL-L5-05U — Security Deposit Permission Namespace, Domain
Authorization and Runtime Certification.

FINAL-L5-05O identified that Security Deposit frontend/page permissions
used one permission namespace while mutation endpoints used another, and
applied a bounded fix (granting Finance Admin both namespaces) without
reconciling the underlying duplication. This sprint's own runtime
inventory found the problem was precisely located and worse than 05O's
own framing:

1. THREE live Security Deposit endpoint families existed against the same
   `SecurityDeposit`/`SecurityDepositTransaction` tables:
   - `finance_hub.admin_router` (`/v1/admin/finance/deposits*`) --
     `finance:deposits:*` permissions. The richest implementation: list/
     summary/detail/approve/reject/record-offline/refund/adjust, real
     `SecurityDepositTransaction` history via `credit_deposit`/
     `debit_deposit`, real `platform_audit_logs` audit trail.
   - `package_commerce.admin_router` (`/v1/admin/tenants/{tenant_id}/
     security-deposit*`) -- `finance.security_deposits.*` permissions
     (a SECOND, independent namespace). Zero real caller anywhere in the
     codebase. A genuine transactional-integrity defect: its refund/
     forfeit/mark-paid methods mutated `SecurityDeposit.status` directly
     with NO `SecurityDepositTransaction` history row and no call to the
     shared `credit_deposit`/`debit_deposit` primitives -- confirmed via
     source read that `current_balance` (a computed property:
     `total_paid + replenishment_total - warranty_drawn`) would silently
     never change even after a "refund".
   - `platform_commerce.router` (`/v1/commerce/tenants/{tenant_id}/
     deposit*`) -- the real tenant self-service payment-initiation flow
     (confirmed live caller in both super-admin AND tenant-portal
     frontends), but its admin-only `admin_adjust_deposit` mutation was
     gated by `require_super_admin` (a coarse role check, not a
     permission -- meaning Finance Admin's own UI rendered a button that
     always 403'd), and its 3 read/initiate endpoints were gated by
     `TENANT_BILLING_READ`/`TENANT_BILLING_MANAGE` -- Usage Credit's own
     permission names, reused for a different domain (a real, if
     low-severity, domain-boundary-crossing bug).

2. A precise root-cause smoking gun for the "frontend page vs mutation
   endpoint" mismatch 05O described: `/admin/finance/deposits`' nav item,
   its `RequirePermission` page-level route guard, AND the frontend
   permission catalog all checked `finance.security_deposits.read` (the
   deprecated namespace), while the SAME page's own action menu
   (Approve/Reject/Record-Offline/Refund/Adjust) and every backend
   endpoint it calls checked `finance:deposits:*` (the canonical
   namespace) -- meaning no role could ever both SEE the page (nav +
   RequirePermission) and successfully USE it (action menu + backend)
   without holding both namespaces simultaneously. Only `admin_finance`
   held both (05O's bounded fix); `admin_readonly` held only the dead
   alias, so Read Only saw the nav item but the page's own data fetch
   would 403.

3. A real, previously-undiscovered CROSS-TENANT VULNERABILITY: neither
   `CommerceService` (platform_commerce) nor `require_permission()` (pure
   RBAC, no tenant scoping) ever verified a caller's own tenant matched
   the route's `tenant_id` for `get_deposit_status`/`initiate_deposit`/
   `get_deposit_transactions` -- any `tenant_owner` (who legitimately
   holds `TENANT_BILLING_READ`/`MANAGE` for self-service) could substitute
   another tenant's UUID and read that tenant's Security Deposit status/
   history. Same defect class as FINAL-L5-05Q's Service Area fix.

Canonical decision: `FINANCE_DEPOSITS_*` (already the richest, most
complete, real-caller-backed namespace). See
docs/final-l5-05/FINAL_L5_05U_ADR_SECURITY_DEPOSIT_CANONICAL_PERMISSION.md.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.core.permissions import P, ROLE_PERMISSIONS, permission_checker

ROOT = Path(__file__).parent.parent

# Real, pre-existing Home Services tenants (confirmed live via direct SQL).
# Keep these aligned with the durable E2E seed instead of the retired Demo
# AC Services fixture, which was removed from the development database.
TENANT_A = uuid.UUID("13309ae1-69b2-4174-a775-1bc2e008bf8a")
TENANT_B = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestCanonicalPermissionNamespace:
    """Part 28: exactly one active Security Deposit permission namespace."""

    def test_finance_deposits_permissions_exist_and_are_canonical(self):
        assert P.FINANCE_DEPOSITS_READ == "finance:deposits:read"
        assert P.FINANCE_DEPOSITS_UPDATE == "finance:deposits:update"
        assert P.FINANCE_DEPOSITS_APPROVE == "finance:deposits:approve"
        assert P.FINANCE_DEPOSITS_REFUND == "finance:deposits:refund"

    def test_deprecated_alias_permissions_still_defined_but_marked_deprecated(self):
        # Constants remain defined (mission rule 13: explicit disposition,
        # not silent deletion) but every one is commented DEPRECATED.
        src = _read("app/core/permissions.py")
        for name in ("FINANCE_SECURITY_DEPOSITS_READ", "FINANCE_SECURITY_DEPOSITS_CONFIG_UPDATE",
                     "FINANCE_SECURITY_DEPOSITS_CREATE", "FINANCE_SECURITY_DEPOSITS_MARK_RECEIVED",
                     "FINANCE_SECURITY_DEPOSITS_HOLD", "FINANCE_SECURITY_DEPOSITS_RELEASE",
                     "FINANCE_SECURITY_DEPOSITS_ADJUST", "FINANCE_SECURITY_DEPOSITS_AUDIT_READ"):
            assert hasattr(P, name)
            start = src.index(f"{name} ")
            line = src[start:src.index("\n", start)]
            assert "DEPRECATED" in line

    def test_deprecated_alias_permissions_authorize_zero_active_endpoints(self):
        # No router anywhere in the codebase may still gate a real endpoint
        # with any of the 8 deprecated keys.
        import subprocess
        result = subprocess.run(
            ["git", "grep", "-n", "-E",
             r"require_permission\(P\.FINANCE_SECURITY_DEPOSITS_",
             "--", "app/"],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert result.stdout.strip() == "", (
            f"a deprecated FINANCE_SECURITY_DEPOSITS_* permission still gates "
            f"a live endpoint: {result.stdout}"
        )

    def test_package_commerce_security_deposit_routes_are_blocked_not_permission_gated(self):
        src = _read("app/engines/package_commerce/admin_router.py")
        start = src.index("# SECURITY DEPOSIT — /v1/admin/tenants/{tenant_id}/security-deposit")
        block = src[start:]
        assert "status_code=410" in block
        assert "require_permission(P.FINANCE_SECURITY_DEPOSITS_READ)" not in block
        assert "require_permission(P.FINANCE_SECURITY_DEPOSITS_MARK_RECEIVED)" not in block
        assert "require_permission(P.FINANCE_SECURITY_DEPOSITS_RELEASE)" not in block
        assert "require_permission(P.FINANCE_SECURITY_DEPOSITS_ADJUST)" not in block


class TestFrontendBackendMatchGuards:
    """Part 30: nav item, route guard, permission catalog, and action menu
    must all reference the SAME canonical key -- pinning the exact bug
    this sprint found and fixed."""

    def test_nav_item_uses_canonical_permission(self):
        src = _read("frontend/super-admin/components/layout/AdminLayout.tsx")
        # Deposits now live inside the consolidated Home Services Finance
        # workspace, so the old standalone nav item must not return. The
        # workspace has its canonical read guard; deposit mutations retain
        # their granular backend permissions.
        assert 'id: "finance-deposits"' not in src
        start = src.index('id: "home-services-finance"')
        line = src[start:src.index("\n", start)]
        assert 'requiredPermission: "finance:hub:read"' in line
        assert "finance.security_deposits" not in line

    def test_page_route_guard_uses_canonical_permission(self):
        src = _read("frontend/super-admin/app/admin/finance/deposits/page.tsx")
        assert 'requiredPermission="finance:deposits:read"' in src
        assert "finance.security_deposits" not in src

    def test_permission_catalog_no_longer_lists_deprecated_alias(self):
        src = _read("frontend/super-admin/lib/permission-catalog.ts")
        assert '"finance.security_deposits' not in src
        assert '"finance:deposits:read"' in src
        assert '"finance:deposits:approve"' in src
        assert '"finance:deposits:update"' in src
        assert '"finance:deposits:refund"' in src

    def test_export_button_gated_on_canonical_export_permission(self):
        src = _read("frontend/super-admin/app/admin/finance/deposits/page.tsx")
        start = src.index("Export</Btn>")
        block = src[max(0, start - 300):start]
        assert 'perm.has("finance:hub:export")' in block

    def test_tenant_detail_adjust_deposit_button_is_permission_gated(self):
        src = _read("frontend/super-admin/app/admin/tenants/[id]/page.tsx")
        start = src.index("Adjust Security Deposit</button>")
        block = src[max(0, start - 300):start]
        assert 'perm.has("finance:deposits:update")' in block

    def test_dead_frontend_client_methods_removed(self):
        src = _read("frontend/super-admin/lib/api.ts")
        assert "getSecurityDeposit:" not in src
        assert "markDepositPaid:" not in src


class TestRolePolicyMatrix:
    """Part 9/28: machine-readable role policy -- zero unexplained cells."""

    def test_super_admin_has_full_access_via_wildcard(self):
        for perm in (P.FINANCE_DEPOSITS_READ, P.FINANCE_DEPOSITS_UPDATE,
                     P.FINANCE_DEPOSITS_APPROVE, P.FINANCE_DEPOSITS_REFUND, P.FINANCE_EXPORT):
            assert permission_checker.has("super_admin", perm)

    def test_finance_admin_holds_exactly_the_canonical_deposit_permissions(self):
        perms = set(ROLE_PERMISSIONS["admin_finance"])
        deposit_perms = {p for p in perms if "deposit" in p.lower()}
        assert deposit_perms == {
            P.FINANCE_DEPOSITS_READ, P.FINANCE_DEPOSITS_APPROVE,
            P.FINANCE_DEPOSITS_UPDATE, P.FINANCE_DEPOSITS_REFUND,
        }, f"admin_finance holds unexpected deposit permissions: {deposit_perms}"

    def test_admin_readonly_holds_only_canonical_read(self):
        perms = set(ROLE_PERMISSIONS["admin_readonly"])
        deposit_perms = {p for p in perms if "deposit" in p.lower()}
        assert deposit_perms == {P.FINANCE_DEPOSITS_READ}, (
            f"admin_readonly holds unexpected deposit permissions: {deposit_perms}"
        )

    def test_operations_admin_holds_zero_deposit_permissions(self):
        perms = set(ROLE_PERMISSIONS["admin_operations"])
        deposit_perms = {p for p in perms if "deposit" in p.lower()}
        assert deposit_perms == set(), f"admin_operations must hold 0 deposit permissions, found: {deposit_perms}"

    def test_security_admin_holds_zero_deposit_permissions(self):
        perms = set(ROLE_PERMISSIONS["admin_security"])
        deposit_perms = {p for p in perms if "deposit" in p.lower()}
        assert deposit_perms == set(), f"admin_security must hold 0 deposit permissions, found: {deposit_perms}"

    def test_admin_readonly_holds_zero_deposit_mutation_or_export_permissions(self):
        perms = set(ROLE_PERMISSIONS["admin_readonly"])
        mutation_shaped = {
            P.FINANCE_DEPOSITS_UPDATE, P.FINANCE_DEPOSITS_APPROVE, P.FINANCE_DEPOSITS_REFUND,
        }
        assert not (mutation_shaped & perms), f"admin_readonly holds mutation permissions: {mutation_shaped & perms}"
        assert P.FINANCE_EXPORT not in perms

    def test_read_permission_alone_does_not_authorize_mutation_router_side(self):
        # Static ordering guard: the read endpoint and each mutation
        # endpoint use DISTINCT require_permission() calls in finance_hub's
        # admin_router (no endpoint conflates read with mutation).
        src = _read("app/engines/finance_hub/admin_router.py")
        assert 'require_permission(P.FINANCE_DEPOSITS_READ)' in src
        assert 'require_permission(P.FINANCE_DEPOSITS_APPROVE)' in src
        assert 'require_permission(P.FINANCE_DEPOSITS_UPDATE)' in src
        assert 'require_permission(P.FINANCE_DEPOSITS_REFUND)' in src
        assert 'require_permission(P.FINANCE_EXPORT)' in src  # export distinct from read


class TestPlatformCommerceAdminAdjustMigration:
    """Part 11: the coarse require_super_admin check migrated to the
    canonical permission -- closing a real, live bug (Finance Admin's own
    UI rendered a button that always 403'd)."""

    def test_admin_adjust_deposit_uses_canonical_permission_not_raw_role_check(self):
        src = _read("app/engines/platform_commerce/router.py")
        start = src.index("async def admin_adjust_deposit(")
        end = src.index("async def ", start + 10)
        block = src[start:end]
        assert "u: UserContext = Depends(require_permission(P.FINANCE_DEPOSITS_UPDATE))" in block
        assert "Depends(require_super_admin)" not in block


class TestCrossTenantVulnerabilityFix:
    """Part 20/29: the real cross-tenant read vulnerability found in
    CommerceService's deposit methods (no tenant-ownership check at all)
    is closed, mirroring ServiceabilityService._assert_owns_tenant()'s
    established pattern."""

    def test_commerce_service_tracks_actor_tenant_id(self):
        src = _read("app/engines/platform_commerce/service.py")
        start = src.index("class CommerceService:")
        end = src.index("def _get_tenant(", start)
        block = src[start:end]
        assert "actor_tenant_id" in block

    def test_deposit_read_and_initiate_methods_assert_tenant_ownership(self):
        src = _read("app/engines/platform_commerce/service.py")
        for method in ("async def get_deposit_status(", "async def initiate_deposit(",
                       "async def get_deposit_transactions("):
            start = src.index(method)
            end = src.index("\n\n", start)
            block = src[start:end]
            assert "_assert_owns_tenant_deposit(tid)" in block, f"{method} missing tenant-ownership check"

    def test_router_passes_actor_tenant_id_to_service(self):
        src = _read("app/engines/platform_commerce/router.py")
        start = src.index("def _svc(")
        end = src.index("def _svc_open(", start)
        block = src[start:end]
        assert "actor_tenant_id=" in block


class TestDomainIsolationGuards:
    """Part 29: Security Deposit mutations must never write Usage Credit
    tables or Completed Job Deduction / provider-earning / customer-payment
    context."""

    def test_finance_hub_deposit_mutations_never_reference_usage_credit_tables(self):
        src = _read("app/engines/finance_hub/service.py")
        start = src.index("async def approve_deposit(")
        end = src.index("async def export_deposits(", start)
        block = src[start:end]
        assert "usage_credit_ledger" not in block
        assert "UsageCreditLedger" not in block
        assert "tenant_billing" not in block.lower().replace("tenantbilling", "")
        assert "TenantBilling" not in block

    def test_commerce_service_deposit_methods_never_reference_usage_credit_tables(self):
        src = _read("app/engines/platform_commerce/service.py")
        start = src.index("# ── Deposit (5)")
        end = src.index("# ── Packages (5)", start)
        block = src[start:end]
        assert "UsageCreditLedger" not in block
        assert "TenantBilling" not in block

    def test_credit_debit_deposit_primitives_only_touch_security_deposit_tables(self):
        src = _read("app/engines/platform_commerce/ledger.py")
        start = src.index("async def debit_deposit(")
        end = src.index("# ── Commission", start) if "# ── Commission" in src[start:] else len(src)
        block = src[start:end]
        assert "SecurityDeposit" in block
        assert "UsageCreditLedger" not in block
        assert "TenantBilling" not in block

    @pytest.mark.skipif(
        __import__("os").environ.get("SERVICEOS_RUN_REAL_DB_TESTS", "1") != "1",
        reason="requires a real reachable Postgres instance",
    )
    @pytest.mark.asyncio
    async def test_live_deposit_adjustment_does_not_change_tenant_billing(self):
        """Real Postgres: a real deposit adjustment must not move
        tenant_billing.credit_balance or write a usage_credit_ledger row."""
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, pool_size=5, max_overflow=5)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as db:
                before_billing = (await db.execute(text(
                    "SELECT credit_balance FROM tenant_billing WHERE tenant_id = :t"
                ), {"t": str(TENANT_A)})).scalar_one_or_none()
                before_ledger_count = (await db.execute(text(
                    "SELECT count(*) FROM usage_credit_ledger WHERE tenant_id = :t"
                ), {"t": str(TENANT_A)})).scalar_one()

            from unittest.mock import AsyncMock, patch
            from app.engines.finance_hub.service import FinanceHubService
            async with session_factory() as db:
                svc = FinanceHubService(db=db, actor_role="super_admin")
                deposit_row = (await db.execute(text(
                    "SELECT id FROM security_deposits WHERE tenant_id = :t"
                ), {"t": str(TENANT_A)})).scalar_one()
                with patch("app.engines.finance_hub.service.record_platform_audit", new=AsyncMock()):
                    await svc.record_offline_deposit(deposit_row, __import__("decimal").Decimal("100"),
                                                       "test-ref", "L5U concurrency/isolation test")
                await db.commit()

            async with session_factory() as db:
                after_billing = (await db.execute(text(
                    "SELECT credit_balance FROM tenant_billing WHERE tenant_id = :t"
                ), {"t": str(TENANT_A)})).scalar_one_or_none()
                after_ledger_count = (await db.execute(text(
                    "SELECT count(*) FROM usage_credit_ledger WHERE tenant_id = :t"
                ), {"t": str(TENANT_A)})).scalar_one()
                assert before_billing == after_billing, "deposit mutation changed tenant_billing.credit_balance"
                assert before_ledger_count == after_ledger_count, "deposit mutation wrote a usage_credit_ledger row"
        finally:
            async with session_factory() as db:
                await db.execute(text(
                    "UPDATE security_deposits SET total_paid = 0.00, status = 'unpaid' WHERE tenant_id = :t"
                ), {"t": str(TENANT_A)})
                await db.execute(text(
                    "DELETE FROM security_deposit_transactions WHERE tenant_id = :t AND reference_id = 'test-ref'"
                ), {"t": str(TENANT_A)})
                await db.commit()
            await engine.dispose()


@pytest.mark.skipif(
    __import__("os").environ.get("SERVICEOS_RUN_REAL_DB_TESTS", "1") != "1",
    reason="requires a real reachable Postgres instance",
)
class TestRealConcurrencyMatrix:
    """Part 19/38: real Postgres, real credit_deposit/debit_deposit
    primitives. debit_deposit's own balance check ('Raises if insufficient
    balance') is the over-release guard -- proven here under concurrency,
    not just read from source."""

    @pytest.fixture
    def session_factory(self):
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=10)
        yield async_sessionmaker(engine, expire_on_commit=False)

    @pytest.mark.asyncio
    async def test_concurrent_debits_never_produce_negative_balance(self, session_factory):
        import asyncio
        from decimal import Decimal
        from app.engines.platform_commerce.ledger import credit_deposit, debit_deposit
        from app.engines.platform_commerce.constants import DepositTxnType
        from app.engines.platform_commerce.models import SecurityDeposit

        tenant_id = uuid.uuid4()
        try:
            async with session_factory() as db:
                deposit = SecurityDeposit(tenant_id=tenant_id, required_amount=Decimal("1000"),
                                           status="paid")
                db.add(deposit)
                await db.flush()
                await credit_deposit(db, deposit, Decimal("1000"), DepositTxnType.INITIAL_PAYMENT,
                                      None, "seed", None)
                await db.commit()
                deposit_id = deposit.id

            async def try_debit(amount: Decimal):
                async with session_factory() as db:
                    d = (await db.execute(select(SecurityDeposit).where(
                        SecurityDeposit.id == deposit_id))).scalar_one()
                    try:
                        await debit_deposit(db, d, amount, "refund", None, "concurrency test", None)
                        await db.commit()
                        return "ok"
                    except Exception as e:
                        await db.rollback()
                        return type(e).__name__

            # Two concurrent debits of 700 each against a balance of 1000 --
            # at most one can succeed (700), the other must fail (700+700>1000).
            results = await asyncio.gather(try_debit(Decimal("700")), try_debit(Decimal("700")))
            successes = [r for r in results if r == "ok"]
            assert len(successes) == 1, f"expected exactly 1 debit to succeed, got: {results}"

            async with session_factory() as verify_db:
                row = (await verify_db.execute(text(
                    "SELECT total_paid, replenishment_total, warranty_drawn FROM security_deposits WHERE id = :id"
                ), {"id": str(deposit_id)})).fetchone()
                balance = row[0] + row[1] - row[2]
                assert balance >= 0, f"negative balance after concurrent debits: {balance}"
                assert balance == Decimal("300"), f"expected final balance 300, got {balance}"
        finally:
            async with session_factory() as db:
                await db.execute(text("DELETE FROM security_deposit_transactions WHERE tenant_id = :t"),
                                  {"t": str(tenant_id)})
                await db.execute(text("DELETE FROM security_deposits WHERE tenant_id = :t"),
                                  {"t": str(tenant_id)})
                await db.commit()

    @pytest.mark.asyncio
    async def test_live_cross_tenant_read_denied_for_tenant_owner(self, session_factory):
        """The real fix: a tenant_owner for Tenant A must not be able to
        read Tenant B's deposit status via the same service method."""
        from app.engines.platform_commerce.service import CommerceService
        from app.exceptions import NotFoundException

        async with session_factory() as db:
            svc = CommerceService(db=db, actor_role="tenant_owner", actor_tenant_id=TENANT_A)
            with pytest.raises(NotFoundException):
                await svc.get_deposit_status(TENANT_B)

    @pytest.mark.asyncio
    async def test_live_same_tenant_read_still_works_for_tenant_owner(self, session_factory):
        from app.engines.platform_commerce.service import CommerceService

        async with session_factory() as db:
            svc = CommerceService(db=db, actor_role="tenant_owner", actor_tenant_id=TENANT_A)
            result = await svc.get_deposit_status(TENANT_A)
            assert result["tenant_id"] == str(TENANT_A)

    @pytest.mark.asyncio
    async def test_live_admin_read_across_tenants_still_works(self, session_factory):
        """Admin/super_admin callers (actor_tenant_id=None or actor_role
        != tenant_owner) must remain unaffected -- the ownership check is
        scoped only to self-service tenant_owner callers."""
        from app.engines.platform_commerce.service import CommerceService

        async with session_factory() as db:
            svc = CommerceService(db=db, actor_role="super_admin", actor_tenant_id=None)
            result_a = await svc.get_deposit_status(TENANT_A)
            result_b = await svc.get_deposit_status(TENANT_B)
            assert result_a["tenant_id"] == str(TENANT_A)
            assert result_b["tenant_id"] == str(TENANT_B)
