"""FINAL-L5-05O — Dashboard, contextual link, export and in-page action
permission certification. Static/unit-level guards proving the real,
bounded fixes made this sprint are correct and self-consistent:

1. Enterprise Grid export system (Sprint 26, 33 resources) previously had
   ZERO domain-permission gating on create_export_job -- any authenticated
   role could export any resource, including Finance/Security-sensitive
   ones. Now gated via RESOURCE_EXPORT_PERMISSIONS for the sensitive subset.
2. finance_hub's 4 export endpoints (deposits/topups/warranty-claims/
   payouts) used a READ permission, violating "report read must not imply
   export" -- now require the distinct FINANCE_EXPORT permission.
3. Dashboard widgets were unreachable by ALL 4 non-super-admin roles (no
   role held the base DASHBOARD_READ gate at all) -- now each role holds
   the base + its own domain-specific dashboard read permissions, still
   with zero cross-domain leakage and zero export/mutation grants to
   Admin Read Only.
4. Security Deposits page's mutation actions map to a different backend
   permission domain (finance:deposits:*) than the page's own route guard
   (finance.security_deposits.*) -- a pre-existing architecture mismatch;
   Finance Admin is granted the real, correct permissions this sprint.

Live cross-domain HTTP/Chromium evidence is captured separately in
docs/final-l5-05/FINAL_L5_05O_LIVE_API_MATRIX.md and the Chromium spec.
"""
from __future__ import annotations

from pathlib import Path

from app.core.permissions import P, ROLE_PERMISSIONS, permission_checker
from app.engines.enterprise_grid.filter_registry import (
    EnterpriseFilterRegistry, RESOURCE_EXPORT_PERMISSIONS,
)

ROOT = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestEnterpriseExportPermissionGate:
    def test_resource_export_permissions_map_only_to_real_resources(self):
        for key in RESOURCE_EXPORT_PERMISSIONS:
            assert EnterpriseFilterRegistry.resource_exists(key), f"{key} is not a registered resource"

    def test_finance_export_resources_require_finance_export_permission(self):
        for key in ("admin_finance_deposits", "admin_finance_topups",
                    "admin_finance_claims", "admin_finance_payouts", "admin_finance_wallets"):
            assert RESOURCE_EXPORT_PERMISSIONS[key] == P.FINANCE_EXPORT

    def test_security_export_resources_require_security_audit_export_permission(self):
        for key in ("admin_security_threats", "admin_security_sessions",
                    "admin_ip_blocklist", "admin_api_keys",
                    "admin_audit_logs", "admin_setting_audit_logs"):
            assert RESOURCE_EXPORT_PERMISSIONS[key] == P.SECURITY_AUDIT_EXPORT

    def test_jobs_export_resource_requires_field_ops_jobs_export_permission(self):
        assert RESOURCE_EXPORT_PERMISSIONS["admin_service_jobs"] == P.FIELD_OPS_JOBS_EXPORT

    def test_required_export_permission_returns_none_for_unmapped_resource(self):
        assert EnterpriseFilterRegistry.required_export_permission("admin_categories") is None

    def test_create_export_router_enforces_the_mapping(self):
        src = _read("app/engines/enterprise_grid/router.py")
        assert "required_export_permission(body.resource_key)" in src
        assert "PERMISSION_DENIED" in src


class TestFinanceHubExportPermissionSeparation:
    """REPORT_READ != REPORT_EXPORT (rule 9) for the 4 finance_hub exports."""

    def test_no_finance_hub_export_endpoint_uses_a_read_only_permission(self):
        src = _read("app/engines/finance_hub/admin_router.py")
        assert 'async def export_deposits(' in src
        assert 'async def export_topups(' in src
        assert 'async def export_claims(' in src
        assert 'async def export_payouts(' in src
        for fn in ("export_deposits", "export_topups", "export_claims", "export_payouts"):
            start = src.index(f"async def {fn}(")
            end = src.index("):\n", start)
            block = src[start:end]
            assert "P.FINANCE_EXPORT" in block, f"{fn} must require P.FINANCE_EXPORT, not a read permission"


class TestDashboardRoleBundles:
    """Every dashboard-capable admin role must actually be able to reach the
    dashboard's base sections (a real, previously-undiscovered gap: before
    this sprint, 0 of the 4 non-super-admin roles held DASHBOARD_READ at
    all -- every dashboard widget 403'd for every non-super-admin role)."""

    def test_all_four_admin_roles_hold_base_dashboard_read(self):
        for role in ("admin_operations", "admin_finance", "admin_security", "admin_readonly"):
            assert permission_checker.has(role, P.DASHBOARD_READ), f"{role} must hold DASHBOARD_READ"

    def test_operations_admin_has_operations_dashboard_widgets(self):
        assert permission_checker.has("admin_operations", P.DASHBOARD_OPERATIONS_READ)
        assert permission_checker.has("admin_operations", P.DASHBOARD_ENGINE_HEALTH_READ)
        assert permission_checker.has("admin_operations", P.DASHBOARD_ACTIVITY_READ)
        assert permission_checker.has("admin_operations", P.DASHBOARD_ACTION_QUEUE_MANAGE)

    def test_operations_admin_has_zero_finance_or_security_dashboard_widgets(self):
        assert not permission_checker.has("admin_operations", P.DASHBOARD_FINANCE_READ)
        assert not permission_checker.has("admin_operations", P.DASHBOARD_SECURITY_READ)

    def test_finance_admin_has_finance_dashboard_widget(self):
        assert permission_checker.has("admin_finance", P.DASHBOARD_FINANCE_READ)

    def test_finance_admin_has_zero_operations_or_security_dashboard_widgets(self):
        assert not permission_checker.has("admin_finance", P.DASHBOARD_OPERATIONS_READ)
        assert not permission_checker.has("admin_finance", P.DASHBOARD_SECURITY_READ)
        assert not permission_checker.has("admin_finance", P.DASHBOARD_ACTION_QUEUE_MANAGE)

    def test_security_admin_has_security_dashboard_widget(self):
        assert permission_checker.has("admin_security", P.DASHBOARD_SECURITY_READ)

    def test_security_admin_has_zero_finance_or_operations_dashboard_widgets(self):
        assert not permission_checker.has("admin_security", P.DASHBOARD_FINANCE_READ)
        assert not permission_checker.has("admin_security", P.DASHBOARD_OPERATIONS_READ)
        assert not permission_checker.has("admin_security", P.DASHBOARD_ACTION_QUEUE_MANAGE)

    def test_admin_readonly_has_zero_domain_dashboard_widgets(self):
        assert not permission_checker.has("admin_readonly", P.DASHBOARD_FINANCE_READ)
        assert not permission_checker.has("admin_readonly", P.DASHBOARD_OPERATIONS_READ)
        assert not permission_checker.has("admin_readonly", P.DASHBOARD_SECURITY_READ)

    def test_admin_readonly_has_zero_dashboard_export_or_mutation(self):
        assert not permission_checker.has("admin_readonly", P.DASHBOARD_EXPORT)
        assert not permission_checker.has("admin_readonly", P.DASHBOARD_ACTION_QUEUE_MANAGE)

    def test_no_role_except_super_admin_holds_dashboard_export(self):
        for role, perms in ROLE_PERMISSIONS.items():
            if role == "super_admin":
                continue
            assert P.DASHBOARD_EXPORT not in perms, f"{role} must not hold DASHBOARD_EXPORT by default"


class TestExportRoleSeparation:
    """Mission rules 13-15/17-19: Operations sees zero Finance exports,
    Finance sees zero Security exports, Security sees zero Finance/
    Operations exports, Admin Read Only sees zero exports at all."""

    def test_operations_admin_cannot_export_finance_data(self):
        assert not permission_checker.has("admin_operations", P.FINANCE_EXPORT)

    def test_operations_admin_can_export_own_jobs_data(self):
        assert permission_checker.has("admin_operations", P.FIELD_OPS_JOBS_EXPORT)

    def test_finance_admin_cannot_export_security_or_operations_data(self):
        assert not permission_checker.has("admin_finance", P.SECURITY_AUDIT_EXPORT)
        assert not permission_checker.has("admin_finance", P.FIELD_OPS_JOBS_EXPORT)

    def test_finance_admin_can_export_own_finance_data(self):
        assert permission_checker.has("admin_finance", P.FINANCE_EXPORT)

    def test_security_admin_cannot_export_finance_or_operations_data(self):
        assert not permission_checker.has("admin_security", P.FINANCE_EXPORT)
        assert not permission_checker.has("admin_security", P.FIELD_OPS_JOBS_EXPORT)

    def test_security_admin_can_export_own_security_audit_data(self):
        assert permission_checker.has("admin_security", P.SECURITY_AUDIT_EXPORT)

    def test_admin_readonly_has_zero_export_permissions_of_any_kind(self):
        export_keys = (P.FINANCE_EXPORT, P.SECURITY_AUDIT_EXPORT, P.FIELD_OPS_JOBS_EXPORT, P.DASHBOARD_EXPORT)
        for key in export_keys:
            assert not permission_checker.has("admin_readonly", key), f"admin_readonly must not hold {key}"


class TestSecurityDepositsActionPermissionArchitectureMismatch:
    """Real, pre-existing finding: the frontend page's route guard uses
    finance.security_deposits.read, but its mutation actions call backend
    endpoints gated by an entirely different permission domain
    (finance:deposits:*). Finance Admin is granted the real permissions
    needed to actually use the page it's meant to own."""

    def test_finance_admin_holds_the_real_deposits_mutation_permissions(self):
        for perm in (P.FINANCE_DEPOSITS_READ, P.FINANCE_DEPOSITS_APPROVE, P.FINANCE_DEPOSITS_UPDATE, P.FINANCE_DEPOSITS_REFUND):
            assert permission_checker.has("admin_finance", perm)

    def test_admin_readonly_does_not_hold_deposits_mutation_permissions(self):
        for perm in (P.FINANCE_DEPOSITS_APPROVE, P.FINANCE_DEPOSITS_UPDATE, P.FINANCE_DEPOSITS_REFUND):
            assert not permission_checker.has("admin_readonly", perm)

    def test_deposits_page_gates_every_mutation_action_by_the_real_backend_permission(self):
        src = _read("frontend/super-admin/app/admin/finance/deposits/page.tsx")
        assert 'usePermissions' in src
        for label_fragment, perm_key in (
            ("Approve Deposit", "finance:deposits:approve"),
            ("Reject Deposit", "finance:deposits:approve"),
            ("Record Offline Deposit", "finance:deposits:update"),
            ("Initiate Refund", "finance:deposits:refund"),
            ("Forfeit / Adjust", "finance:deposits:update"),
        ):
            idx = src.index(label_fragment)
            # the perm.has(...) guard must appear on the same line/entry,
            # immediately before the action's label in the array literal
            window = src[max(0, idx - 120):idx]
            assert f'perm.has("{perm_key}")' in window, f"{label_fragment} is missing its perm.has({perm_key!r}) guard"


class TestDashboardRequestSuppression:
    """Part 5: restricted widget requests must not fire when denial is
    already known -- useApi gained an `enabled` option and the dashboard
    page wires it to each domain-sensitive widget's resolved permission."""

    def test_use_api_supports_enabled_option_and_skips_fetch_when_disabled(self):
        src = _read("frontend/super-admin/hooks/useApi.ts")
        assert "options?: { enabled?: boolean }" in src
        assert "if (!enabled)" in src

    def test_dashboard_page_gates_every_sensitive_widget_with_enabled(self):
        src = _read("frontend/super-admin/app/admin/dashboard/page.tsx")
        for call, flag in (
            ("dashboardApi.getFinanceSnapshot()", "financeAllowed"),
            ("dashboardApi.getOperationsSnapshot()", "opsAllowed"),
            ("dashboardApi.getLiveOperations(20)", "opsAllowed"),
            ("dashboardApi.getActionQueue(50)", "actionsAllowed"),
            ("dashboardApi.getEngineHealth()", "enginesAllowed"),
            ("dashboardApi.getComplianceSecurity()", "securityAllowed"),
            ("dashboardApi.getActivityFeed(15)", "activityAllowed"),
        ):
            idx = src.index(call)
            line_end = src.index("\n", idx)
            line = src[idx:line_end]
            assert f"enabled: {flag}" in line, f"{call} is missing enabled: {flag}"

    def test_dashboard_page_omits_export_snapshot_action_when_denied(self):
        src = _read("frontend/super-admin/app/admin/dashboard/page.tsx")
        idx = src.index("Export Snapshot")
        window = src[max(0, idx - 200):idx]
        assert "exportAllowed ?" in window

    def test_dashboard_quick_links_filter_by_destination_permission(self):
        src = _read("frontend/super-admin/app/admin/dashboard/page.tsx")
        assert ".filter(link =>" in src
        assert 'perm.role === "super_admin"' in src


class TestPermissionCatalogValidity:
    """Every new frontend-referenced key must exist in the real backend
    registry -- no frontend-invented permission keys (rule: no second
    permission registry)."""

    def test_all_new_dashboard_keys_exist_in_backend_registry(self):
        backend_keys = {
            P.DASHBOARD_READ, P.DASHBOARD_FINANCE_READ, P.DASHBOARD_OPERATIONS_READ,
            P.DASHBOARD_SECURITY_READ, P.DASHBOARD_EXPORT, P.DASHBOARD_ACTION_QUEUE_MANAGE,
            P.DASHBOARD_ENGINE_HEALTH_READ, P.DASHBOARD_ACTIVITY_READ,
        }
        src = _read("frontend/super-admin/lib/permission-catalog.ts")
        for key in backend_keys:
            assert f'"{key}"' in src, f"{key} referenced by frontend but missing from permission-catalog.ts"

    def test_all_new_finance_deposits_keys_exist_in_backend_registry(self):
        for key in (P.FINANCE_DEPOSITS_APPROVE, P.FINANCE_DEPOSITS_UPDATE, P.FINANCE_DEPOSITS_REFUND):
            src = _read("frontend/super-admin/lib/permission-catalog.ts")
            assert f'"{key}"' in src
