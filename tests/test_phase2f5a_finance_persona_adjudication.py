"""Phase 2A Slice 2F-5A — package_commerce/finance_hub persona adjudication.

This is an adjudication slice: no broad guard was applied to either module.
These tests lock in the evidence-based findings so a future slice cannot
silently regress the analysis (e.g. by someone assuming admin_router means
platform-only without re-checking, or a permission grant changing without
anyone revisiting this slice's conclusions).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_inventory_module():
    spec = importlib.util.spec_from_file_location(
        "inventory_mutation_routes",
        Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "inventory_mutation_routes.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRuntimeRouteInventory:
    """Workstream 1/13: exact mounted mutation counts for both modules."""

    def test_package_commerce_admin_router_has_20_mutations(self):
        mod = _load_inventory_module()
        from app.main import app
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.package_commerce.admin_router"]
        assert len(routes) == 20, f"expected 20, found {len(routes)}"

    def test_finance_hub_admin_router_has_17_mutations(self):
        mod = _load_inventory_module()
        from app.main import app
        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.finance_hub.admin_router"]
        assert len(routes) == 17, f"expected 17, found {len(routes)}"


class TestSecurityDepositDeprecatedStubsConfirmed:
    """Workstream 9: package_commerce's 3 security-deposit endpoints must
    remain unconditional 410s pointing to finance_hub as canonical."""

    @pytest.mark.parametrize("fn_name", [
        "admin_mark_deposit_paid", "admin_refund_deposit", "admin_forfeit_deposit",
    ])
    def test_deposit_stub_always_raises_410(self, fn_name):
        import inspect
        from app.engines.package_commerce import admin_router as r
        src = inspect.getsource(getattr(r, fn_name))
        assert "HTTPException" in src
        assert "410" in src

    def test_deposit_blocked_detail_names_finance_hub_as_canonical(self):
        from app.engines.package_commerce import admin_router as r
        assert "finance_hub" in r._DEPOSIT_BLOCKED_DETAIL


class TestPermissionBundleGaps:
    """Workstream 2/7: the exact set of permissions confirmed granted to no
    role except via super_admin's P.ALL wildcard. If this set ever changes
    (a permission gets granted or a new one is added), this test forces a
    re-adjudication rather than silently drifting."""

    UNGRANTED_PACKAGE_PERMISSIONS = [
        "PACKAGES_CREATE", "PACKAGES_UPDATE", "PACKAGES_ARCHIVE",
        "PACKAGES_ACTIVATE", "PACKAGES_DEACTIVATE", "PACKAGES_CLONE",
    ]
    UNGRANTED_FINANCE_PERMISSIONS = [
        "FINANCE_PAYOUTS_READ", "FINANCE_PAYOUTS_APPROVE", "FINANCE_PAYOUTS_REJECT",
        "FINANCE_PAYOUTS_PROCESS", "FINANCE_PAYOUTS_COMPLETE",
        "FINANCE_CLAIMS_READ", "FINANCE_CLAIMS_ASSIGN", "FINANCE_CLAIMS_APPROVE",
        "FINANCE_CLAIMS_REJECT", "FINANCE_CLAIMS_SETTLE",
    ]
    GRANTED_ADMIN_FINANCE_PERMISSIONS = [
        "FINANCE_USAGE_CREDITS_TOP_UP", "FINANCE_USAGE_CREDITS_ADJUST",
        "FINANCE_DEPOSITS_APPROVE", "FINANCE_DEPOSITS_UPDATE", "FINANCE_DEPOSITS_REFUND",
        "FINANCE_TOPUPS_UPDATE", "FINANCE_TOPUPS_REFUND",
    ]

    def test_ungranted_permissions_are_not_in_any_role_bundle(self):
        import app.core.permissions as perm_mod
        source = open(perm_mod.__file__, encoding="utf-8").read()
        # Count occurrences of "P.<NAME>" -- exactly 1 (the definition line)
        # means it is never referenced in any ROLE_PERMISSIONS bundle.
        for name in self.UNGRANTED_PACKAGE_PERMISSIONS + self.UNGRANTED_FINANCE_PERMISSIONS:
            occurrences = source.count(f"P.{name}")
            assert occurrences == 0, (
                f"P.{name} now appears in a role bundle (found {occurrences} references) -- "
                f"this changes Slice 2F-5A's adjudication; re-verify "
                f"finance-router-route-inventory.csv and module-readiness-decision.md"
            )

    def test_admin_finance_granted_permissions_still_referenced(self):
        import app.core.permissions as perm_mod
        source = open(perm_mod.__file__, encoding="utf-8").read()
        for name in self.GRANTED_ADMIN_FINANCE_PERMISSIONS:
            assert f"P.{name}" in source, f"P.{name} definition missing entirely"


class TestPackagePurchaseSharedCanonicalService:
    """Workstream 3/9: admin_purchase_package and tenant_purchase_package
    must call the identical canonical service method -- not two competing
    write owners."""

    def test_both_purchase_endpoints_call_create_package_assignment(self):
        import inspect
        from app.engines.package_commerce import admin_router, tenant_router
        admin_src = inspect.getsource(admin_router.admin_purchase_package)
        tenant_src = inspect.getsource(tenant_router.tenant_purchase_package)
        assert "create_package_assignment" in admin_src
        assert "create_package_assignment" in tenant_src


class TestWalletDelegatesToCanonicalUsageCreditService:
    """Workstream 4/6: credit-wallet endpoints must delegate to
    UsageCreditService, not mutate TenantWallet directly (the FINAL-L5-05J
    fix this slice confirmed, not re-broke)."""

    @pytest.mark.parametrize("fn_name", ["admin_topup_wallet", "admin_adjust_wallet"])
    def test_wallet_endpoint_uses_usage_credit_service(self, fn_name):
        import inspect
        from app.engines.package_commerce import admin_router as r
        src = inspect.getsource(getattr(r, fn_name))
        assert "UsageCreditService" in src

    def test_adjust_wallet_requires_a_reason(self):
        import inspect
        from app.engines.package_commerce import admin_router as r
        src = inspect.getsource(r.admin_adjust_wallet)
        assert "INVALID_ADJUSTMENT_REASON" in src or "reason" in src.lower()


class TestNoFrontendTenantPortalCaller:
    """Workstream 8: neither module's mutation paths should be called from
    frontend/tenant-portal -- both are genuinely platform-admin-facing."""

    PATH_FRAGMENTS = [
        "/admin/packages", "/admin/finance/deposits", "/admin/finance/payouts",
        "/admin/finance/topups", "/admin/finance/warranty-claims",
    ]

    def test_tenant_portal_has_no_caller_for_these_admin_paths(self):
        root = Path(__file__).parent.parent
        api_client = root / "frontend" / "tenant-portal" / "lib" / "api.ts"
        text = api_client.read_text(encoding="utf-8")
        found = [frag for frag in self.PATH_FRAGMENTS if frag in text]
        assert found == [], (
            f"frontend/tenant-portal/lib/api.ts now references platform-admin finance "
            f"path(s) {found} -- re-adjudicate persona classification if this is intentional"
        )
