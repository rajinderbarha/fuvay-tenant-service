"""Home Services Menu Isolation + Tenant Price Range Setup certification.

Static-inspection style (established convention this session). Part B
(tenant provider price range setup, admin floor/ceiling enforcement,
symmetric Low/Mid/High preview) was already built and live-verified in the
prior "Tenant Home Services Service Setup Wizard" sprint — this ticket's
new work is exclusively Part A (menu reorganization: moving "Pricing
Rules" out of the common/global "Pricing & Rules" nav group into the
Home-Services-only nav group, deprecating the old common route, and
building 4 new Home-Services-scoped admin pages: Pricing Rules, Service
Areas / Zones, Completed Job Deduction, Home Services Settings) plus
re-verifying Part B's backend enforcement still holds.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/super-admin"
TENANT_FRONTEND = ROOT / "frontend/tenant-portal"

LAYOUT = (FRONTEND / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8-sig")
OLD_PRICING_RULES_PAGE = (FRONTEND / "app/admin/pricing-rules/page.tsx").read_text(encoding="utf-8-sig")
HS_PRICING_RULES_PAGE = (FRONTEND / "app/admin/home-services/pricing-rules/page.tsx").read_text(encoding="utf-8-sig")
HS_SERVICE_AREAS_PAGE = (FRONTEND / "app/admin/home-services/service-areas/page.tsx").read_text(encoding="utf-8-sig")
HS_DEDUCTION_PAGE = (FRONTEND / "app/admin/home-services/completed-job-deduction/page.tsx").read_text(encoding="utf-8-sig")
HS_SETTINGS_PAGE = (FRONTEND / "app/admin/home-services/settings/page.tsx").read_text(encoding="utf-8-sig")
TENANT_WIZARD_PAGE = (TENANT_FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx").read_text(encoding="utf-8-sig")
TENANT_SERVICE_PY = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
BARGAIN_ENGINE = (ROOT / "app/engines/admin_catalog/bargain_engine.py").read_text(encoding="utf-8-sig")


# ── PART A: Menu organization ─────────────────────────────────────────────────

def test_home_services_nav_group_has_all_required_items():
    hs_block = LAYOUT.split('label: "Home Services"')[1].split("},\n  {")[0]
    for item in ["Overview", "Service Catalog", "Pricing Rules", "Customer Price Experience",
                 "Provider Matching", "Matching Diagnostics", "Service Areas / Zones",
                 "Completed Job Deduction", "Home Services Settings"]:
        assert item in hs_block, f"missing Home Services nav item: {item}"


def test_pricing_rules_removed_from_common_pricing_group():
    common_block = LAYOUT.split('label: "Pricing & Rules"')[1].split('label: "Home Services"')[0]
    assert 'id: "pricing-rules"' not in common_block
    assert '"/admin/pricing-rules"' not in common_block
    # Genuinely multi-vertical infra stays in the common group
    assert 'id: "pricing-tiers"' in common_block
    assert 'id: "location-mapping"' in common_block
    assert 'id: "provider-overrides"' in common_block


def test_home_services_pricing_rules_route_registered():
    assert 'id: "hs-pricing-rules"' in LAYOUT
    assert '"/admin/home-services/pricing-rules"' in LAYOUT


def test_no_home_services_item_duplicated_in_another_group():
    hs_block = LAYOUT.split('label: "Home Services"')[1].split("},\n  {")[0]
    non_hs = LAYOUT.replace(hs_block, "")
    for href in ["/admin/home-services/pricing-rules", "/admin/home-services/service-catalog",
                 "/admin/home-services/price-experience", "/admin/home-services/provider-matching",
                 "/admin/home-services/matching-diagnostics", "/admin/home-services/service-areas",
                 "/admin/home-services/completed-job-deduction", "/admin/home-services/settings"]:
        assert href not in non_hs, f"{href} duplicated outside Home Services group"


def test_new_pages_exist():
    assert (FRONTEND / "app/admin/home-services/pricing-rules/page.tsx").exists()
    assert (FRONTEND / "app/admin/home-services/service-areas/page.tsx").exists()
    assert (FRONTEND / "app/admin/home-services/completed-job-deduction/page.tsx").exists()
    assert (FRONTEND / "app/admin/home-services/settings/page.tsx").exists()


def test_old_route_shows_deprecation_and_links_forward():
    assert "[Deprecated]" in OLD_PRICING_RULES_PAGE
    assert "/admin/home-services/pricing-rules" in OLD_PRICING_RULES_PAGE
    assert "deprecated" in OLD_PRICING_RULES_PAGE.lower()


def test_old_route_still_functions_backward_compatible():
    # Deprecation banner only — the real CRUD underneath is untouched (no
    # data loss / broken links for anyone with the old URL bookmarked).
    assert "catalogApi" in OLD_PRICING_RULES_PAGE
    assert "listPricingRules" in OLD_PRICING_RULES_PAGE or "DataTable" in OLD_PRICING_RULES_PAGE


# ── Home Services Pricing Rules page ──────────────────────────────────────────

def test_hs_pricing_rules_title_and_subtitle():
    assert "Home Services Pricing Rules" in HS_PRICING_RULES_PAGE
    assert "Set platform-controlled price boundaries by service, type, brand, and tier. Providers can only set prices inside these ranges." in HS_PRICING_RULES_PAGE


def test_hs_pricing_rules_table_columns():
    for col in ["Service", "Type", "Brand", "Zone/Tier", "Admin Min", "Admin Max",
                "Platform Fee", "Completed Job Deduction", "Status", "Actions"]:
        assert col in HS_PRICING_RULES_PAGE


def test_hs_pricing_rules_form_fields():
    for field in ["Service", "Type (optional)", "Brand (optional)", "Admin Minimum Price",
                  "Admin Maximum Price", "Platform Fee %", "Completed Job Deduction Credits",
                  "Internal Notes"]:
        assert field in HS_PRICING_RULES_PAGE


def test_hs_pricing_rules_validation_messages():
    assert "Admin Minimum Price must be greater than 0." in HS_PRICING_RULES_PAGE
    assert "Admin Maximum Price must be greater than or equal to Admin Minimum Price." in HS_PRICING_RULES_PAGE
    assert "Platform Fee must be greater than or equal to 0." in HS_PRICING_RULES_PAGE
    assert "Completed Job Deduction must be greater than or equal to 0." in HS_PRICING_RULES_PAGE


def test_hs_pricing_rules_scoped_to_home_services():
    assert "homeServicesCatalogConsoleApi.listServices" in HS_PRICING_RULES_PAGE
    assert "homeServiceIds.has(r.master_service_id)" in HS_PRICING_RULES_PAGE


def test_hs_pricing_rules_error_shows_request_id():
    assert "Request ID:" in HS_PRICING_RULES_PAGE
    assert "saveAction.requestId" in HS_PRICING_RULES_PAGE


# ── Other 3 new pages ──────────────────────────────────────────────────────────

def test_service_areas_page_content():
    assert "Service Areas / Zones" in HS_SERVICE_AREAS_PAGE
    assert "catalogApi.listTiers" in HS_SERVICE_AREAS_PAGE


def test_completed_job_deduction_page_content():
    assert "Completed Job Deduction" in HS_DEDUCTION_PAGE
    assert "Usage Credits" in HS_DEDUCTION_PAGE or "usage credit" in HS_DEDUCTION_PAGE.lower()


def test_settings_page_content():
    assert "Home Services Settings" in HS_SETTINGS_PAGE
    assert "autoPriceOptionsApi.getConfig" in HS_SETTINGS_PAGE
    assert "Auto Price Options" in HS_SETTINGS_PAGE


# ── PART B: re-verify tenant price range setup (already built) ───────────────

def test_tenant_wizard_still_shows_platform_allowed_range():
    # HS0 cleanup: the wizard was rebuilt (per-type/brand pricing table)
    # since this test was written; the literal "Working Range" copy no
    # longer exists but the same admin-floor/ceiling range display does,
    # sourced from admin_floor_price/admin_ceiling_price.
    assert "admin_floor_price" in TENANT_WIZARD_PAGE or "admin_ceiling_price" in TENANT_WIZARD_PAGE
    assert "adminFloor" in TENANT_WIZARD_PAGE and "adminCeiling" in TENANT_WIZARD_PAGE


def test_tenant_cannot_edit_admin_fields():
    # No input bound directly to admin_floor_price/admin_ceiling_price/
    # platform_fee_percent — the per-type/brand inputs are bound to
    # tp.tenantMin/tp.tenantMax (validated client-side against
    # tp.adminFloor/tp.adminCeiling, never editable themselves).
    assert "value={tp.tenantMin}" in TENANT_WIZARD_PAGE and "value={tp.tenantMax}" in TENANT_WIZARD_PAGE
    assert "value={tp.adminFloor}" not in TENANT_WIZARD_PAGE and "value={tp.adminCeiling}" not in TENANT_WIZARD_PAGE


def test_backend_still_enforces_min_max_bounds():
    assert "TENANT_PRICE_BELOW_ADMIN_MIN" in TENANT_SERVICE_PY
    assert "TENANT_PRICE_ABOVE_ADMIN_MAX" in TENANT_SERVICE_PY
    assert "tmin > tmax" in TENANT_SERVICE_PY
    assert "tmin < admin_floor" in TENANT_SERVICE_PY
    assert "tmax > admin_ceiling" in TENANT_SERVICE_PY


def test_symmetric_low_mid_high_matches_ticket_example():
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r = compute_symmetric_customer_price_tiers(800, 1000, 10)
    assert (r["low_price"], r["mid_price"], r["high_price"]) == (880.0, 990.0, 1100.0)


def test_low_includes_platform_fee_not_raw_provider_min():
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r = compute_symmetric_customer_price_tiers(800, 1000, 10)
    assert r["low_price"] != 800.0


def test_brand_override_respects_admin_range_backend():
    assert "BRAND_OVERRIDE_NOT_ALLOWED" in TENANT_SERVICE_PY
    assert "admin_floor is None or admin_ceiling is None" in TENANT_SERVICE_PY


def test_publish_blocked_on_invalid_pricing():
    assert "SERVICE_SETUP_INCOMPLETE" in TENANT_SERVICE_PY


# ── Scope guard / other vertical isolation ────────────────────────────────────

def test_home_services_scope_guard_message():
    assert "This setup wizard is available only for Home Services." in TENANT_WIZARD_PAGE


def test_admin_pages_scoped_to_home_services_category():
    assert "get_home_services_category_id" in (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8-sig")
    assert "vertical_type == \"home_services\"" in (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")


# ── Forbidden labels ──────────────────────────────────────────────────────────
FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Bargain Rule Builder",
]


def test_no_forbidden_labels_new_pages():
    for page in [HS_PRICING_RULES_PAGE, HS_SERVICE_AREAS_PAGE, HS_DEDUCTION_PAGE, HS_SETTINGS_PAGE]:
        for term in FORBIDDEN:
            assert term not in page, f"forbidden label found: {term}"


def test_manual_bargain_setup_wording_absent():
    for page in [HS_PRICING_RULES_PAGE, HS_SERVICE_AREAS_PAGE, HS_DEDUCTION_PAGE, HS_SETTINGS_PAGE]:
        assert "Manual Bargain Setup" not in page
