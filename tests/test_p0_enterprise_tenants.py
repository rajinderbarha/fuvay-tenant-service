"""P0 Enterprise Tenants Dashboard — static analysis tests.

Tests verify:
- Backend router has new enterprise endpoints
- Admin service has new enterprise methods
- api.ts has adminTenantsApi with all methods + interfaces
- Frontend page has all enterprise components
"""
import os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _backend(rel: str) -> str:
    path = os.path.join(BASE, "app", "engines", "tenant_engine", rel)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _frontend(rel: str) -> str:
    path = os.path.join(BASE, "frontend", "super-admin", rel)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Backend: admin_router.py ───────────────────────────────────────────────────

class TestTenantAdminRouter:
    def test_summary_endpoint_exists(self):
        src = _backend("admin_router.py")
        assert '"/summary"' in src or "get_tenants_summary" in src

    def test_insights_endpoint_exists(self):
        src = _backend("admin_router.py")
        assert "insights" in src

    def test_export_endpoint_exists(self):
        src = _backend("admin_router.py")
        assert '"/export"' in src or "export_tenants" in src

    def test_reactivate_endpoint_exists(self):
        src = _backend("admin_router.py")
        assert "reactivate" in src

    def test_request_changes_endpoint_exists(self):
        src = _backend("admin_router.py")
        assert "request-changes" in src or "request_changes" in src

    def test_add_usage_credits_endpoint_exists(self):
        src = _backend("admin_router.py")
        assert "add-usage-credits" in src or "add_usage_credits" in src

    def test_send_notification_endpoint_exists(self):
        src = _backend("admin_router.py")
        assert "send-notification" in src or "send_notification" in src

    def test_require_super_admin_on_write_endpoints(self):
        src = _backend("admin_router.py")
        assert "require_super_admin" in src

    def test_no_payout_language(self):
        src = _backend("admin_router.py")
        assert "payout" not in src.lower()
        assert "withdrawal" not in src.lower()


# ── Backend: admin_service.py ─────────────────────────────────────────────────

class TestTenantAdminService:
    def test_get_insights_method(self):
        src = _backend("admin_service.py")
        assert "async def get_insights" in src

    def test_add_usage_credits_method(self):
        src = _backend("admin_service.py")
        assert "async def add_usage_credits" in src

    def test_reactivate_tenant_method(self):
        src = _backend("admin_service.py")
        assert "async def reactivate_tenant" in src

    def test_request_changes_method(self):
        src = _backend("admin_service.py")
        assert "async def request_changes" in src

    def test_send_notification_method(self):
        src = _backend("admin_service.py")
        assert "async def send_notification" in src

    def test_export_csv_method(self):
        src = _backend("admin_service.py")
        assert "async def export_tenants_csv" in src

    def test_enriched_list_returns_usage_credit_balance(self):
        src = _backend("admin_service.py")
        assert "usage_credit_balance" in src

    def test_enriched_list_returns_active_jobs(self):
        src = _backend("admin_service.py")
        assert "active_jobs" in src

    def test_enriched_list_returns_open_complaints(self):
        src = _backend("admin_service.py")
        assert "open_complaints" in src

    def test_enriched_list_returns_staff_count(self):
        src = _backend("admin_service.py")
        assert "staff_count" in src

    def test_add_credits_requires_reason(self):
        src = _backend("admin_service.py")
        idx = src.index("async def add_usage_credits")
        snippet = src[idx:idx + 400]
        assert "REASON_REQUIRED" in snippet or "reason" in snippet.lower()

    def test_suspend_creates_audit_log(self):
        src = _backend("admin_service.py")
        idx = src.index("async def suspend_tenant")
        snippet = src[idx:idx + 300]
        assert "_audit" in snippet or "audit" in snippet

    def test_no_payout_wallet_language(self):
        src = _backend("admin_service.py")
        assert "payout_balance" not in src
        assert "withdrawable" not in src.lower()

    def test_insights_returns_verification_overview(self):
        src = _backend("admin_service.py")
        idx = src.index("async def get_insights")
        snippet = src[idx:idx + 4000]
        assert "verification_overview" in snippet

    def test_insights_returns_health_summary(self):
        src = _backend("admin_service.py")
        idx = src.index("async def get_insights")
        snippet = src[idx:idx + 5000]
        assert "health_summary" in snippet

    def test_insights_returns_financial_summary(self):
        src = _backend("admin_service.py")
        idx = src.index("async def get_insights")
        snippet = src[idx:idx + 5000]
        assert "financial_summary" in snippet

    def test_insights_does_not_show_payout(self):
        src = _backend("admin_service.py")
        idx = src.index("async def get_insights")
        snippet = src[idx:idx + 2000]
        assert "payout" not in snippet.lower()


# ── api.ts ────────────────────────────────────────────────────────────────────

class TestApiTs:
    def test_admin_tenants_api_exists(self):
        src = _frontend("lib/api.ts")
        assert "export const adminTenantsApi" in src

    def test_tenant_list_item_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface TenantListItem" in src

    def test_tenant_list_item_has_usage_credit_balance(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export interface TenantListItem")
        snippet = src[idx:idx + 600]
        assert "usage_credit_balance" in snippet

    def test_tenant_list_item_has_open_complaints(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export interface TenantListItem")
        snippet = src[idx:idx + 600]
        assert "open_complaints" in snippet

    def test_tenants_summary_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface TenantsSummary" in src

    def test_tenants_insights_interface(self):
        src = _frontend("lib/api.ts")
        assert "export interface TenantsInsights" in src

    def test_get_summary_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 2000]
        assert "getSummary" in snippet

    def test_get_insights_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 2000]
        assert "getInsights" in snippet

    def test_list_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 2000]
        assert "list:" in snippet

    def test_export_csv_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 2000]
        assert "exportCsv" in snippet

    def test_add_usage_credits_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 2000]
        assert "addUsageCredits" in snippet

    def test_suspend_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 3500]
        assert "suspend" in snippet

    def test_reactivate_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 3500]
        assert "reactivate" in snippet

    def test_request_changes_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 3500]
        assert "requestChanges" in snippet

    def test_send_notification_method(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 3500]
        assert "sendNotification" in snippet

    def test_no_payout_in_admin_tenants_api(self):
        src = _frontend("lib/api.ts")
        idx = src.index("export const adminTenantsApi")
        snippet = src[idx:idx + 2500]
        assert "payout" not in snippet.lower()


# ── Frontend page.tsx ─────────────────────────────────────────────────────────

class TestTenantsPage:
    def test_page_exists(self):
        _frontend("app/admin/tenants/page.tsx")

    def test_imports_admin_tenants_api(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "adminTenantsApi" in src

    def test_kpi_cards_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "KpiCards" in src

    def test_stat_card_used(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "StatCard" in src

    def test_toolbar_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "Toolbar" in src

    def test_active_chips_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "EnterpriseFilterBar" in src

    def test_bulk_bar_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "BulkBar" in src

    def test_row_actions_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "ActionMenu" in src

    def test_tenant_cell_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "TenantCell" in src

    def test_verification_cell_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "VerifCell" in src

    def test_credits_cell_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "CreditsCell" in src

    def test_right_sidebar_verification_donut(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "VerificationDonut" in src

    def test_right_sidebar_top_locations(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "TopLocations" in src

    def test_right_sidebar_recent_activity(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "RecentActivity" in src

    def test_bottom_cards_component(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "BottomCards" in src

    def test_add_credits_modal(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "AddCreditsModal" in src

    def test_suspend_modal(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "SuspendModal" in src

    def test_request_changes_modal(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "RequestChangesModal" in src

    def test_send_notification_modal(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "SendNotificationModal" in src

    def test_filter_key_serialized_to_string(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "filtersKey" in src

    def test_pagination_controls(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "totalPages" in src

    def test_empty_state_exists(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "No tenants found" in src

    def test_no_tailwind_classnames(self):
        src = _frontend("app/admin/tenants/page.tsx")
        bad = re.findall(r'className="(?!skeleton)[^"]*"', src)
        assert len(bad) == 0, f"Tailwind className found: {bad[:3]}"

    def test_usage_credit_not_real_money(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "not real money" in src or "usage-credit wallet" in src

    def test_no_payout_language(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "payout" not in src.lower()
        assert "withdrawable" not in src.lower()

    def test_page_header_used(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "PageHeader" in src

    def test_admin_layout_used(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "AdminLayout" in src

    def test_export_handler_exists(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "handleExport" in src

    def test_view_details_navigates_to_tenant_detail(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "/admin/tenants/" in src

    def test_open_complaints_column_exists(self):
        src = _frontend("app/admin/tenants/page.tsx")
        assert "open_complaints" in src
