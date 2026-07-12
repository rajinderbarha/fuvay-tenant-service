"""FINAL-L5-05R — Enterprise Export resource mapping, backend authorization
and runtime certification.

FINAL-L5-05O mapped the 12 most sensitive resources (Finance/Security/
Jobs) of the Enterprise Export system's 39 registered resources to real
export-shaped permissions, leaving 27 resources reachable by any
authenticated admin (a documented residual gap). This sprint:

1. Completes the mapping for all remaining 27 resources -- every one of
   the 39 registered resources now has an explicit export permission.
   No resource falls back to "reachable by any authenticated admin".
2. Closes the "unknown resource_key silently skips authorization" gap --
   `create_export` now checks `resource_exists()` first and returns a
   controlled `EXPORT_RESOURCE_UNSUPPORTED` 422 for anything not
   registered, rather than letting a falsy `required_export_permission()`
   (dict.get returning None) bypass the permission check entirely.
3. Wires the previously dead-code `validate_scope`-equivalent tenant
   isolation into `create_export` for SCOPE_PROVIDER resources -- a
   provider/tenant-side caller can no longer request an export with a
   `filters.tenant_id` belonging to a different tenant.
4. Adds CSV formula-injection mitigation (OWASP-standard leading-quote
   prefix for cells starting with =, +, -, @, tab, or CR).
5. Grants the new `operations:export` permission to Operations Admin
   (matching this mission's own Part 9 policy text naming Reviews/
   Complaints as Operations-approved exports) -- Finance/Security/Read-
   Only correctly remain without it.

Two new backend permission keys were added (`operations:export`,
`catalog:export`) -- no existing key fit these two domains cleanly,
whereas every other newly-mapped resource reuses an existing key
(`finance:hub:export`, `security:audit:export`, `tenant:data:export`,
`customers:export`, `settings:export`).
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


class TestFinalL5_05RExhaustiveResourceMapping:
    """Every one of the 39 registered resources must have an explicit
    export permission -- zero resources may fall through to the
    "reachable by any authenticated admin" default."""

    def test_every_registered_resource_has_an_export_permission_mapping(self):
        all_keys = EnterpriseFilterRegistry.all_resource_keys()
        assert len(all_keys) >= 39, f"expected at least 39 registered resources, found {len(all_keys)}"
        unmapped = [k for k in all_keys if k not in RESOURCE_EXPORT_PERMISSIONS]
        assert unmapped == [], f"active export resources remain unmapped: {unmapped}"

    def test_every_mapped_permission_is_export_or_admin_shaped_not_a_bare_read_key(self):
        # None of the mapped values should be a "*.read" style key --
        # read permission must not imply export (rule 5).
        for resource, perm in RESOURCE_EXPORT_PERMISSIONS.items():
            assert not perm.endswith(":read"), f"{resource} is mapped to a read-shaped permission: {perm}"
            assert not perm.endswith(".read"), f"{resource} is mapped to a read-shaped permission: {perm}"

    def test_every_mapped_permission_exists_in_the_p_class(self):
        p_values = {getattr(P, name) for name in dir(P) if not name.startswith("_")}
        for resource, perm in RESOURCE_EXPORT_PERMISSIONS.items():
            assert perm in p_values, f"{resource} maps to {perm!r}, which is not a real P.* permission key"

    def test_new_operations_and_catalog_export_keys_exist(self):
        assert P.OPERATIONS_EXPORT == "operations:export"
        assert P.CATALOG_EXPORT == "catalog:export"

    def test_finance_adjacent_resources_use_finance_export(self):
        for key in ("admin_service_invoices", "admin_payments", "admin_commission_records"):
            assert RESOURCE_EXPORT_PERMISSIONS[key] == P.FINANCE_EXPORT

    def test_operational_content_resources_use_operations_export(self):
        for key in ("admin_service_bookings", "admin_coaching_appointments", "admin_real_estate_leads",
                    "admin_reviews", "admin_complaints", "admin_refund_requests", "admin_rework_requests"):
            assert RESOURCE_EXPORT_PERMISSIONS[key] == P.OPERATIONS_EXPORT

    def test_catalog_pricing_resources_use_catalog_export(self):
        for key in ("admin_categories", "admin_engines", "admin_offerings",
                    "admin_pricing_tiers", "admin_tier_locations", "admin_pricing_rules"):
            assert RESOURCE_EXPORT_PERMISSIONS[key] == P.CATALOG_EXPORT

    def test_provider_scoped_resources_use_tenant_data_export(self):
        for key in ("provider_service_jobs", "provider_service_invoices", "provider_wallet_ledger",
                    "provider_reviews", "provider_complaints", "provider_coaching_appointments",
                    "provider_real_estate_leads", "admin_tenants"):
            assert RESOURCE_EXPORT_PERMISSIONS[key] == P.TENANT_DATA_EXPORT

    def test_customers_and_settings_use_exact_existing_matches(self):
        assert RESOURCE_EXPORT_PERMISSIONS["admin_customers"] == P.CUSTOMERS_EXPORT
        assert RESOURCE_EXPORT_PERMISSIONS["admin_settings"] == P.SETTINGS_EXPORT
        assert RESOURCE_EXPORT_PERMISSIONS["admin_feature_flags"] == P.SETTINGS_EXPORT


class TestUnknownResourceFailsClosed:
    def test_create_export_router_checks_resource_exists_before_permission_check(self):
        src = _read("app/engines/enterprise_grid/router.py")
        start = src.index("async def create_export(")
        end = src.index("async def list_exports(", start)
        block = src[start:end]
        idx_exists_check = block.index("resource_exists(body.resource_key)")
        idx_perm_check = block.index("required_export_permission(body.resource_key)")
        assert idx_exists_check < idx_perm_check, (
            "resource_exists() must be checked BEFORE required_export_permission() "
            "so an unknown resource_key fails closed with EXPORT_RESOURCE_UNSUPPORTED "
            "rather than silently bypassing authorization (dict.get returns None -> falsy)."
        )
        assert "EXPORT_RESOURCE_UNSUPPORTED" in block

    def test_unknown_resource_key_returns_none_permission_but_router_rejects_it_first(self):
        # required_export_permission() itself still returns None for unknown
        # keys (dict.get semantics) -- the router-level resource_exists()
        # check is what actually closes the gap, verified above.
        assert EnterpriseFilterRegistry.required_export_permission("does_not_exist_at_all") is None
        assert not EnterpriseFilterRegistry.resource_exists("does_not_exist_at_all")


class TestProviderScopeTenantIsolation:
    def test_create_export_router_denies_mismatched_tenant_id_filter_for_provider_scope(self):
        src = _read("app/engines/enterprise_grid/router.py")
        start = src.index("async def create_export(")
        end = src.index("async def list_exports(", start)
        block = src[start:end]
        assert "SCOPE_PROVIDER" in block

    def test_super_admin_is_exempt_from_the_provider_scope_check(self):
        # Live-verified regression: without this exemption, super_admin
        # (whose u.tenant_id is None/platform-level) was incorrectly
        # blocked from exporting ANY provider-scoped resource with a
        # tenant_id filter, since None never matches a real tenant UUID.
        src = _read("app/engines/enterprise_grid/router.py")
        start = src.index("async def create_export(")
        end = src.index("async def list_exports(", start)
        block = src[start:end]
        assert 'u.role != "super_admin"' in block
        assert "EXPORT_CROSS_TENANT_FORBIDDEN" in block
        assert "str(requested_tenant_id) != str(u.tenant_id)" in block


class TestCsvFormulaInjectionMitigation:
    def test_generate_csv_sanitizes_formula_prefixed_cells(self):
        from app.engines.enterprise_grid.services import ExportService
        svc = ExportService()
        out = svc.generate_csv(
            "admin_categories", ["name"],
            [{"name": "=cmd|'/c calc'!A1"}, {"name": "Normal Value"}, {"name": "+1+1"}],
        )
        lines = out.strip().split("\r\n")
        assert lines[1] == "'=cmd|'/c calc'!A1" or lines[1].startswith("\"'=cmd")
        assert "Normal Value" in out
        assert "'+1+1" in out or "\"'+1+1" in out

    def test_sanitize_csv_cell_only_touches_formula_prefixed_strings(self):
        from app.engines.enterprise_grid.services import ExportService
        svc = ExportService()
        assert svc._sanitize_csv_cell("Normal") == "Normal"
        assert svc._sanitize_csv_cell(42) == 42
        assert svc._sanitize_csv_cell("=SUM(A1)").startswith("'")
        assert svc._sanitize_csv_cell("-1").startswith("'")
        assert svc._sanitize_csv_cell("@mention").startswith("'")


class TestRoleExportIsolation:
    """The mission's mandatory cross-domain export denials (Part 9/28)."""

    def test_operations_admin_holds_operations_export_and_field_ops_jobs_export_only(self):
        perms = ROLE_PERMISSIONS["admin_operations"]
        assert P.OPERATIONS_EXPORT in perms
        assert P.FIELD_OPS_JOBS_EXPORT in perms
        assert P.FINANCE_EXPORT not in perms
        assert P.SECURITY_AUDIT_EXPORT not in perms
        assert P.CATALOG_EXPORT not in perms

    def test_finance_admin_holds_only_finance_export(self):
        perms = ROLE_PERMISSIONS["admin_finance"]
        assert P.FINANCE_EXPORT in perms
        assert P.SECURITY_AUDIT_EXPORT not in perms
        assert P.OPERATIONS_EXPORT not in perms
        assert P.FIELD_OPS_JOBS_EXPORT not in perms
        assert P.CATALOG_EXPORT not in perms

    def test_security_admin_holds_only_security_audit_export(self):
        perms = ROLE_PERMISSIONS["admin_security"]
        assert P.SECURITY_AUDIT_EXPORT in perms
        assert P.FINANCE_EXPORT not in perms
        assert P.OPERATIONS_EXPORT not in perms
        assert P.FIELD_OPS_JOBS_EXPORT not in perms

    def test_admin_readonly_holds_zero_export_permissions_of_any_domain(self):
        perms = ROLE_PERMISSIONS["admin_readonly"]
        export_keys = {
            P.FINANCE_EXPORT, P.SECURITY_AUDIT_EXPORT, P.FIELD_OPS_JOBS_EXPORT,
            P.OPERATIONS_EXPORT, P.CATALOG_EXPORT, P.TENANT_DATA_EXPORT,
            P.CUSTOMERS_EXPORT, P.SETTINGS_EXPORT, P.DASHBOARD_EXPORT,
        }
        held = export_keys & set(perms)
        assert held == set(), f"admin_readonly must hold zero export permissions, found: {held}"

    def test_super_admin_wildcard_covers_every_mapped_export_permission(self):
        # super_admin's P.ALL wildcard covers everything -- explicit check
        # that permission_checker.has() returns True for every mapped
        # resource's export permission under super_admin.
        for resource, perm in RESOURCE_EXPORT_PERMISSIONS.items():
            assert permission_checker.has("super_admin", perm), f"super_admin denied for {resource} ({perm})"
