"""P0 Platform Command Center Dashboard — frontend static-inspection tests.

This repo's frontend has no test runner (no jest/vitest, no *.test.* files),
so these are Python source-inspection tests, matching the convention used in
tests/test_p0_admin_tenant_typescript_stabilization.py.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = (ROOT / "frontend/super-admin/app/admin/dashboard/page.tsx").read_text(encoding="utf-8")
API_TS = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")


def test_dashboard_page_renders_page_header():
    assert "PageHeader" in PAGE
    assert "Platform Command Center" in PAGE


def test_executive_kpi_cards_render():
    for label in ("Platform Health", "Active Tenants", "Live Operations",
                  "Pending Admin Actions", "At-Risk Tenants", "Critical Alerts"):
        assert label in PAGE


def test_no_nan_undefined_or_null_literal_rendered():
    # Guard against ??/?. chains that could print the literal strings
    # "NaN", "undefined", or "null" straight into the DOM.
    assert "{undefined}" not in PAGE
    assert "{null}" not in PAGE
    assert "NaN" not in PAGE


def test_platform_health_card_renders_score_and_status():
    assert "h?.score" in PAGE
    assert "h?.status" in PAGE


def test_finance_labels_use_correct_serviceos_terminology():
    assert "Platform Revenue" in PAGE
    assert "Provider Direct Service Value" in PAGE
    assert "Completed Job Deductions" in PAGE
    assert "Security Deposits Held" in PAGE
    for banned in ("Payout", "Cash Wallet", "Withdraw", "Escrow"):
        assert banned not in PAGE


def test_trend_empty_state_renders_when_no_data():
    assert "No trend data for this period." in PAGE
    assert "No live jobs right now." in PAGE
    assert "EmptyState" in PAGE


def test_action_queue_renders_with_resolve_and_snooze():
    assert "Pending Admin Action Queue" in PAGE
    assert "handleResolve" in PAGE
    assert "handleSnooze" in PAGE


def test_engine_health_panel_renders():
    assert "System / Engine Health" in PAGE
    assert "ENGINE_STATUS_BADGE" in PAGE


def test_at_risk_tenants_empty_state_renders():
    assert "No at-risk tenants." in PAGE


def test_drill_down_links_wired_to_admin_pages():
    assert '"/admin/tenants"' in PAGE
    assert '"/admin/operations"' in PAGE
    assert "/admin/tenants?health_band=at_risk" in PAGE
    assert '"/admin/security"' in PAGE


def test_export_and_refresh_actions_wired_to_dashboard_api():
    assert "dashboardApi.exportSnapshot" in PAGE
    assert "dashboardApi.refresh" in PAGE


def test_dashboard_api_client_exposes_all_required_methods():
    for method in (
        "getExecutiveSummary", "getPlatformHealth", "getFinanceSnapshot",
        "getTenantLifecycle", "getOperationsSnapshot", "getLiveOperations",
        "getTrends", "getActionQueue", "resolveAction", "snoozeAction",
        "assignAction", "getEngineHealth", "getAtRiskTenants",
        "getComplianceSecurity", "getTrustQuality", "getActivityFeed",
        "getCategoryPerformance", "refresh", "exportSnapshot",
    ):
        assert f"{method}:" in API_TS or f"{method}(" in API_TS, f"missing dashboardApi.{method}"
    assert "dashboardApi" in PAGE
