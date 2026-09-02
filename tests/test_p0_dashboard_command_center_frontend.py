"""Static contract tests for the URL-addressable admin command center."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "frontend/super-admin/app/admin/dashboard/page.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend/super-admin/app/admin/dashboard/dashboard.module.css").read_text(encoding="utf-8")
API_TS = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")


def test_dashboard_has_command_center_header_and_real_scope():
    assert "Platform command center" in PAGE
    assert "native bookings" in PAGE
    assert "Home Services" in PAGE
    assert "styles.hero" in PAGE


def test_executive_kpis_are_decision_focused():
    for label in ("Platform Health", "Active Tenants", "Live Operations",
                  "Pending Admin Actions", "At-Risk Tenants"):
        assert label in PAGE
    assert "Critical Alerts" not in PAGE  # security owns this drill-down


def test_url_addressable_lazy_workspaces():
    for label in ("Overview", "Operations", "Providers", "Finance", "Platform & risk"):
        assert f'label: "{label}"' in PAGE
    assert 'searchParams.set("tab", next)' in PAGE
    assert 'role="tablist"' in PAGE
    assert 'role="tabpanel"' in PAGE
    assert 'aria-selected={tab === item.id}' in PAGE
    assert 'enabled: tab === "providers"' in PAGE
    assert 'enabled: financeAllowed && tab === "finance"' in PAGE
    assert 'enabled: enginesAllowed && tab === "platform"' in PAGE


def test_reporting_range_is_sent_to_real_apis():
    assert "function rangeParams" in PAGE
    assert "date_from" in PAGE and "date_to" in PAGE
    assert 'vertical: "home_services"' in PAGE
    assert "dashboardApi.getFinanceSnapshot(period)" in PAGE
    assert "dashboardApi.getTrends(period)" in PAGE


def test_finance_uses_canonical_terminology():
    for label in ("Platform Revenue", "Provider Direct Service Value",
                  "Completed Job Deductions"):
        assert label in PAGE
    assert "Security Deposits Held" not in PAGE
    for banned in ("Payout", "Cash Wallet", "Withdraw", "Escrow"):
        assert banned not in PAGE


def test_empty_loading_and_error_states_are_explicit():
    assert "No trend data for this period." in PAGE
    assert "No records match this workspace." in PAGE
    assert "No pending actions. Everything is on track." in PAGE
    assert "function SectionError" in PAGE
    assert "Request ID:" in PAGE and "Retry" in PAGE
    assert "Skeleton" in PAGE


def test_action_queue_resolve_and_snooze_are_wired():
    assert "Pending Admin Action Queue" in PAGE
    assert "dashboardApi.resolveAction" in PAGE
    assert "dashboardApi.snoozeAction" in PAGE
    assert "onResolve(item.action_id)" in PAGE
    assert "onSnooze(item.action_id)" in PAGE


def test_current_drill_down_routes_only():
    for route in (
        "/admin/home-services/providers", "/admin/home-services/bookings-jobs",
        "/admin/home-services/finance", "/admin/catalog-workspace",
        "/admin/bookability/providers", "/admin/security", "/admin/engines",
        "/admin/analytics?tab=reports",
    ):
        assert route in PAGE
    assert "/admin/service-area-requests" not in PAGE
    assert "/admin/home-services/provider-matching" not in PAGE
    assert "/admin/home-services/price-experience" not in PAGE
    assert '"/admin/tenants"' not in PAGE


def test_export_refresh_and_search_are_functional():
    assert "dashboardApi.exportSnapshot" in PAGE
    assert "dashboardApi.refresh" in PAGE
    assert "operationSearch" in PAGE
    assert 'placeholder="Search job, provider, status"' in PAGE


def test_dashboard_api_client_exposes_required_methods():
    for method in (
        "getExecutiveSummary", "getPlatformHealth", "getFinanceSnapshot",
        "getTenantLifecycle", "getOperationsSnapshot", "getLiveOperations",
        "getTrends", "getActionQueue", "resolveAction", "snoozeAction",
        "assignAction", "getEngineHealth", "getAtRiskTenants",
        "getComplianceSecurity", "getTrustQuality", "getActivityFeed",
        "getCategoryPerformance", "refresh", "exportSnapshot",
    ):
        assert f"{method}:" in API_TS or f"{method}(" in API_TS


def test_dashboard_styles_are_responsive_and_token_based():
    assert "var(--" in CSS
    assert "@media" in CSS
    assert "minmax(" in CSS
    assert "overflow-x" in CSS


def test_no_literal_invalid_values_or_mock_runtime_data():
    assert "{undefined}" not in PAGE
    assert "{null}" not in PAGE
    assert "NaN" not in PAGE
    assert "no mock data" in PAGE.lower()
