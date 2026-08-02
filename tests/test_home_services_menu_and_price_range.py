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
HS_DEDUCTION_PAGE = (FRONTEND / "app/admin/home-services/completed-job-deduction/page.tsx").read_text(encoding="utf-8-sig")
HS_SETTINGS_PAGE = (FRONTEND / "app/admin/home-services/settings/page.tsx").read_text(encoding="utf-8-sig")
TENANT_WIZARD_PAGE = (TENANT_FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx").read_text(encoding="utf-8-sig")
TENANT_SERVICE_PY = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
BARGAIN_ENGINE = (ROOT / "app/engines/admin_catalog/bargain_engine.py").read_text(encoding="utf-8-sig")


# ── PART A: Menu organization ─────────────────────────────────────────────────

def test_home_services_nav_group_has_all_required_items():
    # "Service Areas / Zones" retired alongside Pricing Tiers / City-Zip
    # Mapping -- replaced by Service Area Requests (see
    # test_admin_a2_dashboard_system_overview.py for its quick-link check).
    # "Pricing Rules" also retired (admin no longer sets price boundaries).
    hs_block = LAYOUT.split('label: "Home Services"')[1].split("},\n  {")[0]
    for item in ["Overview", "Service Catalog", "Customer Price Experience",
                 "Provider Matching", "Matching Diagnostics",
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


def test_home_services_pricing_rules_route_retired_from_nav():
    # Retired: admin no longer sets price boundaries. Page kept as a
    # retired-feature notice (see test_hs_pricing_rules_page_is_retired_notice)
    # but no longer linked from the sidebar.
    assert 'id: "hs-pricing-rules"' not in LAYOUT
    assert '"/admin/home-services/pricing-rules"' not in LAYOUT


def test_no_home_services_item_duplicated_in_another_group():
    hs_block = LAYOUT.split('label: "Home Services"')[1].split("},\n  {")[0]
    non_hs = LAYOUT.replace(hs_block, "")
    for href in ["/admin/home-services/service-catalog",
                 "/admin/home-services/price-experience", "/admin/home-services/provider-matching",
                 "/admin/home-services/matching-diagnostics",
                 "/admin/home-services/completed-job-deduction", "/admin/home-services/settings"]:
        assert href not in non_hs, f"{href} duplicated outside Home Services group"


def test_new_pages_exist():
    assert (FRONTEND / "app/admin/home-services/completed-job-deduction/page.tsx").exists()
    # Retired-notice stub, not deleted (matches Pricing Tiers/City-Zip Mapping
    # precedent) so a bookmarked/typed URL gets a clear notice, not a 404.
    assert (FRONTEND / "app/admin/home-services/pricing-rules/page.tsx").exists()
    assert (FRONTEND / "app/admin/home-services/settings/page.tsx").exists()


def test_service_areas_page_retired_and_replaced():
    """The Tier/City-Zip "Service Areas / Zones" page was deleted (it only
    read a table the backend rejects all writes to). Its real replacement,
    Service Area Requests (tenant-submitted city/zipcode coverage requests,
    admin approves/rejects, no pricing shown), lives at the top level, not
    under /admin/home-services/ -- it is a cross-vertical serviceability
    workflow, not Home-Services-specific."""
    assert not (FRONTEND / "app/admin/home-services/service-areas/page.tsx").exists()
    assert (FRONTEND / "app/admin/service-area-requests/page.tsx").exists()
    assert '"/admin/home-services/service-areas"' not in LAYOUT


def test_old_route_shows_deprecation_and_links_forward():
    # The vertical-scoped Home Services Pricing Rules screen this used to
    # link to is now itself retired (admin no longer sets price boundaries)
    # -- the deprecated global screen now points at the Catalog Workspace.
    assert "[Deprecated]" in OLD_PRICING_RULES_PAGE
    assert "/admin/catalog-workspace" in OLD_PRICING_RULES_PAGE
    assert "deprecated" in OLD_PRICING_RULES_PAGE.lower()


def test_old_route_still_functions_backward_compatible():
    # Deprecation banner only — the real CRUD underneath is untouched (no
    # data loss / broken links for anyone with the old URL bookmarked).
    assert "catalogApi" in OLD_PRICING_RULES_PAGE
    assert "listPricingRules" in OLD_PRICING_RULES_PAGE or "DataTable" in OLD_PRICING_RULES_PAGE


# ── Home Services Pricing Rules page -- retired (admin no longer sets
#    price boundaries; providers set their own price). Converted to a
#    retired-notice stub matching Pricing Tiers / City-Zip Mapping. ─────────

def test_hs_pricing_rules_page_is_retired_notice():
    assert "is retired" in HS_PRICING_RULES_PAGE
    assert "/admin/catalog-workspace" in HS_PRICING_RULES_PAGE
    # The old admin-sets-price-boundary form must be gone, not just hidden --
    # "Admin Minimum/Maximum Price" may still appear in the explanatory
    # comment describing what was retired, but the actual form wiring
    # (input fields, save calls) must not.
    for removed in ["createPricingRule", "updatePricingRule", "<input", "saveAction"]:
        assert removed not in HS_PRICING_RULES_PAGE


# ── Other 2 new pages (Service Areas / Zones retired; see
#    test_service_area_requests_page_is_the_real_replacement below) ─────────

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
    for page in [HS_PRICING_RULES_PAGE, HS_DEDUCTION_PAGE, HS_SETTINGS_PAGE]:
        for term in FORBIDDEN:
            assert term not in page, f"forbidden label found: {term}"


def test_manual_bargain_setup_wording_absent():
    for page in [HS_PRICING_RULES_PAGE, HS_DEDUCTION_PAGE, HS_SETTINGS_PAGE]:
        assert "Manual Bargain Setup" not in page
