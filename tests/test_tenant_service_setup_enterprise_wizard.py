"""Tenant Service Setup — Enterprise Wizard + Card Flow certification.

Static-inspection style (established convention this session). This page
already existed (found pre-built during this ticket's investigation) and was
verified + fixed rather than rewritten from scratch: live smoke testing found
2 real backend response_model bugs (see TENANT_SERVICE_SETUP_BUG_FIX_REPORT.md)
that were breaking the Issues/Options wizard steps with live 500s; both fixed
and re-verified live before this test file was written.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/provider/service-setup/page.tsx").read_text(encoding="utf-8-sig")
NAV_CONFIG_TS = (FRONTEND / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")

PROVIDER_OPTION_ROUTER = (ROOT / "app/engines/admin_catalog/service_option_provider_router.py").read_text(encoding="utf-8-sig")
CUSTOMER_OPTION_ROUTER = (ROOT / "app/engines/admin_catalog/service_option_customer_router.py").read_text(encoding="utf-8-sig")


# ── Route / nav ──────────────────────────────────────────────────────────────
def test_route_exists_and_is_wired_into_nav():
    # HS0 cleanup: /provider/service-setup was superseded by the canonical
    # /tenant/setup/services wizard and is no longer a live nav destination
    # — it's still reachable directly and carries a "moved" banner pointing
    # at the canonical route (see test_tenant_menu_cleanup.py).
    assert (FRONTEND / "app/(tenant)/provider/service-setup/page.tsx").exists()
    assert '"/tenant/setup/services"' in NAV_CONFIG_TS
    assert "Service Setup" in NAV_CONFIG_TS
    assert "/tenant/setup/services" in PAGE  # deprecation banner points forward


# ── Breadcrumb / header ──────────────────────────────────────────────────────
def test_breadcrumb_and_header():
    assert "Tenant Portal / Setup / Service Setup" in PAGE
    assert "Choose platform-approved services, configure coverage, assign staff" in PAGE


def test_header_actions_present():
    for label in ("Add Service", "Refresh Catalog", "Validate Setup", "View Activity"):
        assert label in PAGE


# ── Hero / catalog cards / enabled table / readiness panel ─────────────────
def test_readiness_hero_fields_present():
    for label in ("Enabled Services", "Bookable Services", "Setup Issues", "Service Areas", "Technicians"):
        assert label in PAGE


def test_catalog_cards_section_present():
    assert "Service Catalog" in PAGE
    assert "Enable Service" in PAGE
    assert "Manage Setup" in PAGE


def test_enabled_services_table_present():
    assert "Enabled Services" in PAGE
    for col in ("Types", "Brands", "Pricing", "Bookable", "Status", "Actions"):
        assert col in PAGE


def test_readiness_issues_panel_present():
    assert "Readiness Issues" in PAGE


# ── 10-step wizard ────────────────────────────────────────────────────────
def test_wizard_has_all_ten_steps():
    for step in ("service", "type", "brand", "issues", "options", "areas",
                 "technician", "pricing", "availability", "review"):
        assert f'key: "{step}"' in PAGE


def test_service_step_is_readonly_no_free_text_creation():
    idx = PAGE.index('step === "service"')
    snippet = PAGE[idx: idx + 900]
    assert "managed by the platform catalog" in snippet
    assert "<input" not in snippet  # no free-text service-name field


def test_type_and_brand_steps_use_real_coverage_apis():
    assert "offeringCoverageApi.getTypes" in PAGE
    assert "providerBrandApi.getAvailableForService" in PAGE


def test_issues_step_uses_real_customer_diagnostics_api():
    assert "customerServiceDiagnosticsApi.getIssueTypes" in PAGE


def test_options_step_uses_real_provider_service_option_api():
    assert "providerServiceOptionApi.getAvailableForService" in PAGE


def test_service_area_step_shows_active_areas_only_and_add_cta():
    idx = PAGE.index('step === "areas"')
    snippet = PAGE[idx: idx + 1200]
    assert "filter(a => a.is_active)" in snippet
    assert "Add Service Area" in snippet


def test_technician_step_requires_active_and_shows_add_cta():
    idx = PAGE.index('step === "technician"')
    snippet = PAGE[idx: idx + 1200]
    assert 'filter(m => m.status === "active")' in snippet
    assert "Add Technician" in snippet


def test_pricing_step_uses_backend_resolver_not_client_math():
    idx = PAGE.index('step === "pricing"')
    snippet = PAGE[idx: idx + 1700]
    assert "offeringPricingApi.preview" in PAGE
    assert "Pricing is resolved by the platform" in snippet
    assert "cannot set an authoritative price" in snippet
    assert "Customer pays the provider directly" in snippet


def test_availability_step_shows_missing_state_with_cta():
    idx = PAGE.index('step === "availability"')
    snippet = PAGE[idx: idx + 900]
    assert "Availability is missing" in snippet
    assert "Add Availability" in snippet


def test_review_step_has_full_checklist():
    idx = PAGE.index('step === "review"')
    snippet = PAGE[idx: idx + 1200]
    for item in ("Service selected", "Type selected", "Brand selected",
                 "Service area linked", "Technician assigned", "Availability ready"):
        assert item in snippet
    assert "Ready to enable" in snippet
    assert "saved as draft" in snippet


def test_enable_blocked_and_save_draft_available():
    assert "disabled={!readyToEnable}" in PAGE
    assert "Save Draft" in PAGE
    assert "Enable Service" in PAGE


# ── Error handling ────────────────────────────────────────────────────────
def test_section_error_shows_request_id_and_no_bare_unexpected_error():
    assert "Unexpected error." not in PAGE
    assert "Failed section:" in PAGE
    assert "Copy Request ID" in PAGE


# ── Home Services vertical scope guard ──────────────────────────────────────
def test_non_home_services_vertical_shows_blocked_message():
    assert 'tenant.vertical !== "home_services"' in PAGE
    assert "not available for this business type" in PAGE


# ── Forbidden label scan ─────────────────────────────────────────────────────
FORBIDDEN_LABELS = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]


def test_no_forbidden_finance_labels():
    for label in FORBIDDEN_LABELS:
        assert label not in PAGE, f"forbidden label '{label}' found in Service Setup page"


# ── Backend bug fixes: response_model list/dict mismatch ───────────────────
def test_provider_option_endpoints_use_list_response_model():
    assert "ApiResponse[list]" in PROVIDER_OPTION_ROUTER
    assert "response_model=ApiResponse[dict])\nasync def get_available_options" not in PROVIDER_OPTION_ROUTER


def test_customer_catalog_endpoints_use_list_response_model():
    assert "ApiResponse[list]" in CUSTOMER_OPTION_ROUTER
