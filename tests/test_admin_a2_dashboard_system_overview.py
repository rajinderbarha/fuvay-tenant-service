"""Admin Sprint A2 — Dashboard + System Overview certification.

The admin dashboard ("Platform Command Center",
`frontend/super-admin/app/admin/dashboard/page.tsx`) already existed as a
substantial, real-data implementation (migration 104 +
DashboardCommandCenterService, 19 real endpoints under
`/v1/admin/dashboard/*`, backed by real SQL against `tenants`, `jobs`,
`bookings`, `health_scores`, `commission_records`, `platform_audit_logs`,
etc. — confirmed via live curl, all 15 read endpoints return 200 with
real data). This sprint's real gaps, found and fixed:

1. No dedicated "Home Services Summary" section — the ticket hard-gates
   Home Services must be shown separately, not mixed into common
   categories. Added a new real backend endpoint
   (`GET /v1/admin/dashboard/home-services-summary`) and a new dashboard
   section with quick links routing under `/admin/home-services/*`.
2. No section-level error handling anywhere on the page — any API
   failure silently rendered nothing, with no error message, no
   request_id, no retry. Added a `SectionError` component (title +
   message + Copy Request ID + Retry) wired into the 4 top snapshot
   cards + the new Home Services section.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/super-admin"

PAGE = (FRONTEND / "app/admin/dashboard/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
DASHBOARD_ROUTER = (ROOT / "app/engines/dashboard_command_center/admin_router.py").read_text(encoding="utf-8-sig")
DASHBOARD_SERVICE = (ROOT / "app/engines/dashboard_command_center/service.py").read_text(encoding="utf-8-sig")
PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8-sig")


# ── 1. Route ──────────────────────────────────────────────────────────────────
def test_route_exists():
    assert (FRONTEND / "app/admin/dashboard/page.tsx").exists()


# ── 2. Dashboard layout / header ──────────────────────────────────────────────
def test_page_header_title_and_subtitle():
    assert "Platform command center" in PAGE
    assert "One operational view of provider readiness, native bookings" in PAGE


def test_header_actions_present():
    for action in ["Refresh", "Export Snapshot", "Reports"]:
        assert action in PAGE


# ── 3. Platform health hero / KPI cards ───────────────────────────────────────
def test_kpi_cards_present():
    for label in ["Platform Health", "Active Tenants", "Live Operations",
                  "Pending Admin Actions", "At-Risk Tenants"]:
        assert label in PAGE


def test_kpi_loading_skeleton():
    assert "Skeleton" in PAGE


# ── 4/5. Tenant + Finance summary ─────────────────────────────────────────────
def test_tenant_lifecycle_summary():
    assert "Tenant Lifecycle" in PAGE
    for label in ["Pending Review", "Changes Requested", "Bookable", "Non-Bookable"]:
        assert label in PAGE


def test_finance_summary_correct_labels():
    for label in ["Platform Revenue", "Provider Direct Service Value",
                  "Completed Job Deductions", "Customer service credits issued"]:
        assert label in PAGE


# ── 6. Home Services summary — new this sprint ────────────────────────────────
def test_home_services_summary_section_exists():
    assert "Home Services Summary" in PAGE
    assert "dashboardApi.getHomeServicesSummary" in PAGE


def test_home_services_summary_shown_separately_not_merged():
    assert 'SectionTitle title="Home Services Summary"' in PAGE
    for label in ["Service Catalog", "Finance Rules",
                  "Provider Coverage Readiness", "Bookability & Trust Gates", "Completion Deductions"]:
        assert label in PAGE
    assert "Auto Price Options" not in PAGE


def test_home_services_quick_links_route_under_home_services_prefix():
    for href in ["/admin/catalog-workspace", "/admin/home-services/providers",
                 "/admin/bookability/providers",
                 "/admin/home-services/finance?tab=monetization",
                 "/admin/home-services/finance?tab=provider-charges"]:
        assert href in PAGE, f"missing quick link: {href}"
    assert "/admin/service-area-requests" not in PAGE
    assert "/admin/home-services/provider-matching" not in PAGE
    assert "/admin/home-services/price-experience" not in PAGE
    assert "/admin/home-services/pricing-rules" not in PAGE


def test_home_services_hardgate_no_loose_common_route():
    assert 'vertical: "home_services"' in PAGE
    assert 'dashboardApi.getOperationsSnapshot("home_services")' in PAGE
    assert '"/admin/tenants"' not in PAGE


def test_backend_home_services_summary_endpoint_real():
    assert '"/home-services-summary"' in DASHBOARD_ROUTER
    assert "async def get_home_services_summary" in DASHBOARD_SERVICE
    # real SQL, not mock data
    assert "SELECT COUNT(*) FROM tenants WHERE vertical = 'home_services'" in DASHBOARD_SERVICE
    assert "provider_visibility_statuses" in DASHBOARD_SERVICE
    assert "provider_coverage_health" in DASHBOARD_SERVICE
    assert "tenant_service_area_health" not in DASHBOARD_SERVICE
    assert "provider_bookability_health" in DASHBOARD_SERVICE
    assert "provider_matching_health" not in DASHBOARD_SERVICE


# ── 7. Operations summary ─────────────────────────────────────────────────────
def test_operations_summary():
    assert "Live operations board" in PAGE
    for label in ["Live Jobs", "Today's Bookings", "Pending Provider Acceptance", "SLA Breaches"]:
        assert label in PAGE


# ── 8. Trust & Quality summary ────────────────────────────────────────────────
def test_trust_quality_summary():
    assert "Trust & Quality" in PAGE
    for label in ["Avg Rating", "Complaint Rate", "Dispute Rate", "Providers Under Review"]:
        assert label in PAGE


# ── 9. Alerts / action-required ───────────────────────────────────────────────
def test_action_queue_panel():
    assert "Pending Admin Action Queue" in PAGE
    assert "No pending actions. Everything is on track." in PAGE
    assert "Resolve" in PAGE and "Snooze" in PAGE


# ── 10. Quick actions ─────────────────────────────────────────────────────────
def test_quick_links_panel():
    assert "Quick Links" in PAGE
    for label in ["Tenant Approvals", "Live Operations", "Finance Summary", "Security Center"]:
        assert label in PAGE


# ── 11. Recent activity ───────────────────────────────────────────────────────
def test_recent_activity_panel():
    assert "Recent Activity" in PAGE
    assert "No activity yet." in PAGE


# ── 12. Engine status ──────────────────────────────────────────────────────────
def test_engine_health_panel():
    assert "System / Engine Health" in PAGE
    assert "dashboardApi.getEngineHealth" in PAGE


# ── 13. Permission-aware ──────────────────────────────────────────────────────
def test_backend_permission_constants_exist():
    for perm in ["DASHBOARD_READ", "DASHBOARD_FINANCE_READ", "DASHBOARD_OPERATIONS_READ",
                 "DASHBOARD_SECURITY_READ", "DASHBOARD_ACTIVITY_READ", "DASHBOARD_ENGINE_HEALTH_READ",
                 "DASHBOARD_EXPORT", "DASHBOARD_ACTION_QUEUE_MANAGE"]:
        assert perm in PERMISSIONS


def test_finance_endpoint_gated_by_finance_permission():
    endpoint_src = DASHBOARD_ROUTER.split("async def finance_snapshot")[1].split("async def tenant_lifecycle")[0]
    assert "require_permission(P.DASHBOARD_FINANCE_READ)" in endpoint_src


def test_activity_endpoint_gated_by_activity_permission():
    endpoint_src = DASHBOARD_ROUTER.split("async def activity_feed")[1].split("async def category_performance")[0]
    assert "require_permission(P.DASHBOARD_ACTIVITY_READ)" in endpoint_src


def test_home_services_summary_gated_by_dashboard_read():
    endpoint_src = DASHBOARD_ROUTER.split("async def home_services_summary")[1][:300]
    assert "s: DashboardCommandCenterService = Depends(_svc)" in endpoint_src  # _svc itself requires DASHBOARD_READ


# ── 16/17. Error handling ─────────────────────────────────────────────────────
def test_section_error_component_exists():
    assert "function SectionError" in PAGE
    assert "Request ID:" in PAGE
    assert "Retry" in PAGE


def test_section_error_wired_into_finance_tenant_ops_trust_and_home_services():
    for anchor in ["finance.error", "lifecycle.error", "data.error", "live.error",
                   "risk.error", "trust.error", "home.error", "engines.error",
                   "compliance.error", "categories.error"]:
        assert anchor in PAGE


def test_no_bare_unexpected_error():
    assert '"Unexpected error"' not in PAGE


# ── 18. Forbidden labels ──────────────────────────────────────────────────────
FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Credit Wallet Health", "Manual Bargain Setup", "Bargain Rule Builder",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in PAGE, f"forbidden label found: {term}"


def test_finance_rule_platform_revenue_separate_from_provider_value():
    assert "Platform Revenue" in PAGE and "Provider Direct Service Value" in PAGE
    assert "platform_revenue" in DASHBOARD_SERVICE
    assert "provider_direct_service_value" in DASHBOARD_SERVICE


# ── 19. No mock data ──────────────────────────────────────────────────────────
def test_no_mock_runtime_data_comment_confirms():
    assert "no mock data" in PAGE.lower()


def test_all_api_calls_use_real_dashboard_api():
    for call in ["getExecutiveSummary", "getPlatformHealth", "getFinanceSnapshot", "getTenantLifecycle",
                 "getHomeServicesSummary", "getOperationsSnapshot", "getLiveOperations", "getTrends",
                 "getActionQueue", "getEngineHealth", "getAtRiskTenants", "getComplianceSecurity",
                 "getTrustQuality", "getActivityFeed", "getCategoryPerformance"]:
        assert f"dashboardApi.{call}" in PAGE, f"missing real API call: {call}"


# ── Data normalization ────────────────────────────────────────────────────────
def test_safe_number_fallbacks_in_kpi_and_metrics():
    assert "function Kpi" in PAGE
    assert "?? 0" in PAGE
    assert "Number(provider.credit_balance || 0)" in PAGE
