"""Deactivate Manual Bargain Module — Replace With Automatic Customer Price
Options UI — certification.

Static-inspection + live-verified (see AUTO_PRICE_OPTIONS_TEST_RESULTS.md)
that: manual bargain nav is hidden, the new admin Home Services pages exist
and use real backend endpoints, the tenant Customer Price Preview page is
read-only, and the Home Services scope guard is present everywhere required.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUPER_ADMIN = ROOT / "frontend/super-admin"
TENANT_PORTAL = ROOT / "frontend/tenant-portal"

ADMIN_LAYOUT = (SUPER_ADMIN / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8-sig")
BARGAIN_RULES_PAGE = (SUPER_ADMIN / "app/admin/pricing/bargain-rules/page.tsx").read_text(encoding="utf-8-sig")
PRICE_EXPERIENCE_PAGE = (SUPER_ADMIN / "app/admin/home-services/price-experience/page.tsx").read_text(encoding="utf-8-sig")
PROVIDER_MATCHING_PAGE = (SUPER_ADMIN / "app/admin/home-services/provider-matching/page.tsx").read_text(encoding="utf-8-sig")
MATCHING_DIAGNOSTICS_PAGE = (SUPER_ADMIN / "app/admin/home-services/matching-diagnostics/page.tsx").read_text(encoding="utf-8-sig")

TENANT_LAYOUT = (TENANT_PORTAL / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
TENANT_PRICE_PREVIEW_PAGE = (TENANT_PORTAL / "app/(tenant)/provider/customer-price-preview/page.tsx").read_text(encoding="utf-8-sig")

AUTO_PRICE_ROUTER = (ROOT / "app/engines/admin_catalog/auto_price_options_router.py").read_text(encoding="utf-8-sig")
FEATURE_FLAGS_MODULE = (ROOT / "app/core/feature_flags.py").read_text(encoding="utf-8-sig")


# ── Admin nav: Manual Bargain Rules hidden, Home Services group present ────
def test_manual_bargain_rules_nav_item_removed_from_pricing_group():
    idx = ADMIN_LAYOUT.index('label: "Pricing & Rules"')
    end = ADMIN_LAYOUT.index("},", ADMIN_LAYOUT.index("items:", idx) )
    # scan forward to the closing of this group's items array specifically
    group_end = ADMIN_LAYOUT.index("],", idx) + 2
    group_block = ADMIN_LAYOUT[idx:group_end]
    assert '"bargain-rules"' not in group_block
    assert "Bargain Rules" not in group_block


def test_home_services_admin_nav_group_present():
    assert 'label: "Home Services"' in ADMIN_LAYOUT
    assert "hs-price-experience" in ADMIN_LAYOUT
    assert "hs-provider-matching" in ADMIN_LAYOUT
    assert "hs-matching-diagnostics" in ADMIN_LAYOUT
    assert "Customer Price Experience" in ADMIN_LAYOUT
    assert "Provider Matching" in ADMIN_LAYOUT
    assert "Matching Diagnostics" in ADMIN_LAYOUT


# ── Deprecated bargain route handling ───────────────────────────────────────
def test_deprecated_bargain_route_shows_banner_and_redirect_link():
    assert "Manual Bargain Rules are disabled" in BARGAIN_RULES_PAGE
    assert "/admin/home-services/price-experience" in BARGAIN_RULES_PAGE
    assert "[Deprecated]" in BARGAIN_RULES_PAGE


# ── Admin Customer Price Experience page ────────────────────────────────────
def test_price_experience_page_hero_and_explanation():
    assert "Customer Price Experience" in PRICE_EXPERIENCE_PAGE
    assert "Automatic Price Options" in PRICE_EXPERIENCE_PAGE
    assert "Manual Bargain Rules" in PRICE_EXPERIENCE_PAGE
    assert "Home Services only" in PRICE_EXPERIENCE_PAGE
    # Corrected wording (CUSTOMER_PRICE_EXPERIENCE_CALCULATION_FIX_REPORT.md):
    # platform fee applies to BOTH ends of the selected range, not just the min.
    assert "platform fee is applied to the entire Selected Range" in PRICE_EXPERIENCE_PAGE


def test_price_experience_page_uses_real_preview_endpoint():
    assert "autoPriceOptionsApi.previewPriceExperience" in PRICE_EXPERIENCE_PAGE
    assert "autoPriceOptionsApi.getConfig" in PRICE_EXPERIENCE_PAGE


def test_price_experience_page_shows_low_mid_high_and_breakdown():
    for label in ("Low", "Mid", "High", "Platform Fee on Minimum", "Platform Fee on Maximum",
                  "Selected Range Minimum", "Selected Range Maximum"):
        assert label in PRICE_EXPERIENCE_PAGE


# ── Admin Provider Matching page ────────────────────────────────────────────
def test_provider_matching_page_shows_ranking_weights():
    for label, pct in [("Health Score", "20"), ("Job Completion", "20"), ("Rating", "15"),
                        ("Availability", "15"), ("Service Match", "10"), ("Area Match", "10"),
                        ("Cancellation", "5"), ("Capacity", "5")]:
        assert label in PROVIDER_MATCHING_PAGE


def test_provider_matching_page_states_manual_selection_disabled():
    assert "Disabled for this flow" in PROVIDER_MATCHING_PAGE
    assert "Home Services only" in PROVIDER_MATCHING_PAGE


# ── Admin Matching Diagnostics page ─────────────────────────────────────────
def test_matching_diagnostics_page_renders_real_diagnostics():
    assert "autoPriceOptionsApi.runMatchingDiagnostics" in MATCHING_DIAGNOSTICS_PAGE
    assert "Eligible Providers" in MATCHING_DIAGNOSTICS_PAGE
    assert "customer_visible_reason" in MATCHING_DIAGNOSTICS_PAGE
    assert "internal_score_breakdown" in MATCHING_DIAGNOSTICS_PAGE


# ── Tenant nav: no Bargain Settings, has Customer Price Preview ────────────
def test_tenant_nav_has_no_bargain_settings_item():
    assert "Bargain Settings" not in TENANT_LAYOUT
    assert "Bargain Rules" not in TENANT_LAYOUT
    assert "Manual Bargain" not in TENANT_LAYOUT


def test_tenant_nav_has_customer_price_preview_item():
    # HS0 cleanup: "Customer Price Preview" was removed from the active
    # tenant nav (ticket-forbidden duplicate menu item). The page itself
    # still exists (reachable directly) and now carries a "moved" banner
    # pointing at the canonical /tenant/setup/services wizard — see
    # test_tenant_menu_cleanup.py.
    assert "provider-customer-price-preview" not in TENANT_LAYOUT
    assert "Customer Price Preview" not in TENANT_LAYOUT


# ── Tenant Customer Price Preview page ──────────────────────────────────────
def test_tenant_price_preview_shows_low_mid_high_and_payment_copy():
    assert "Low" in TENANT_PRICE_PREVIEW_PAGE
    assert "Mid" in TENANT_PRICE_PREVIEW_PAGE
    assert "High" in TENANT_PRICE_PREVIEW_PAGE
    assert "Customer pays provider directly after service." in TENANT_PRICE_PREVIEW_PAGE
    assert "usage credits will be deducted" in TENANT_PRICE_PREVIEW_PAGE


def test_tenant_cannot_edit_platform_fee_or_configure_bargain_rule():
    # No input field bound to a platform-fee-editing or bargain-rule-creating action.
    assert "platform_fee_percent:" not in TENANT_PRICE_PREVIEW_PAGE.replace("preview.data.platform_fee_percent", "")
    assert "bargainRulesApi" not in TENANT_PRICE_PREVIEW_PAGE
    assert "createBargainRule" not in TENANT_PRICE_PREVIEW_PAGE


def test_tenant_price_preview_uses_real_readonly_endpoints():
    assert "tenantAutoPriceOptionsApi.getCustomerPricePreview" in TENANT_PRICE_PREVIEW_PAGE
    assert "tenantAutoPriceOptionsApi.getMatchingReadiness" in TENANT_PRICE_PREVIEW_PAGE


def test_tenant_page_has_home_services_scope_guard():
    assert 'tenant.vertical !== "home_services"' in TENANT_PRICE_PREVIEW_PAGE
    assert "not available for this business type" in TENANT_PRICE_PREVIEW_PAGE


# ── Backend: real endpoints + feature flags + Home Services guard ──────────
def test_backend_price_experience_preview_endpoint_exists():
    assert '"/price-experience/preview"' in AUTO_PRICE_ROUTER
    assert "compute_price_tiers" in AUTO_PRICE_ROUTER


def test_backend_matching_diagnostics_endpoint_exists():
    assert '"/matching/diagnostics"' in AUTO_PRICE_ROUTER
    assert "select_best_provider" in AUTO_PRICE_ROUTER
    assert "build_admin_provider" in AUTO_PRICE_ROUTER


def test_backend_tenant_endpoints_are_read_only():
    assert '"/customer-price-preview"' in AUTO_PRICE_ROUTER
    assert '"/matching-readiness"' in AUTO_PRICE_ROUTER
    idx = AUTO_PRICE_ROUTER.index("tenant_customer_price_preview")
    end = AUTO_PRICE_ROUTER.index("tenant_matching_readiness")
    tenant_block = AUTO_PRICE_ROUTER[idx:end]
    assert "@tenant_router.post" not in tenant_block
    assert "@tenant_router.put" not in tenant_block


def test_backend_config_endpoint_uses_real_feature_flag_system():
    assert '"/config"' in AUTO_PRICE_ROUTER
    assert "get_home_services_pricing_flags" in AUTO_PRICE_ROUTER
    assert "FeatureFlag" in FEATURE_FLAGS_MODULE
    assert "manual_bargain_rules_enabled" in FEATURE_FLAGS_MODULE
    assert "auto_price_options_enabled" in FEATURE_FLAGS_MODULE


def test_feature_flag_defaults_match_business_decision():
    from app.core.feature_flags import DEFAULTS, MANUAL_BARGAIN_RULES_ENABLED, AUTO_PRICE_OPTIONS_ENABLED, PROVIDER_FIRST_MATCHING_ENABLED
    assert DEFAULTS[MANUAL_BARGAIN_RULES_ENABLED] is False
    assert DEFAULTS[AUTO_PRICE_OPTIONS_ENABLED] is True
    assert DEFAULTS[PROVIDER_FIRST_MATCHING_ENABLED] is True


# ── Forbidden labels ─────────────────────────────────────────────────────────
FORBIDDEN_LABELS = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]

ALL_NEW_UI_SOURCE = PRICE_EXPERIENCE_PAGE + PROVIDER_MATCHING_PAGE + MATCHING_DIAGNOSTICS_PAGE + TENANT_PRICE_PREVIEW_PAGE


def test_no_forbidden_finance_labels_in_new_ui():
    for label in FORBIDDEN_LABELS:
        assert label not in ALL_NEW_UI_SOURCE, f"forbidden label '{label}' found"


def test_no_bargain_rule_builder_language_customer_facing():
    assert "Bargain Rule Builder" not in ALL_NEW_UI_SOURCE
    assert "Manual Bargain Setup" not in ALL_NEW_UI_SOURCE
