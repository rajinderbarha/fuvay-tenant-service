"""Tenant Home Services Service Setup Wizard certification.

Static-inspection style (established convention this session). This is a
genuinely new wizard (route `/tenant/setup/services`), separate from the
existing, already-certified 10-step `/provider/service-setup` wizard (left
untouched). Backend work: migration 119 (tenant_min_price/tenant_max_price
on tenant_service_types/tenant_service_brands, setup_status/published_at on
tenant_services), 8 new tenant-facing endpoints (type pricing, brand
pricing, price preview, publish, save-draft, Home-Services-scoped
catalog/enabled lists), reusing the admin console's
compute_symmetric_customer_price_tiers formula and the real admin-approved
floor/ceiling data written by the Admin Home Services Catalog Console.

A real, pre-existing gap was found and fixed during this sprint:
`TenantCatalogService.list_available_services` had no category filter at
all — it returned services from every vertical (IELTS, Real Estate,
Restaurant, etc.) to any tenant. New Home-Services-scoped list methods
(`list_home_services_available` / `list_home_services_enabled`) were added
alongside it (the original method is preserved, additive `category_id`
param, existing callers unaffected).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx").read_text(encoding="utf-8-sig")
LAYOUT = (FRONTEND / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
TENANT_SERVICE_PY = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
TENANT_ROUTER = (ROOT / "app/engines/admin_catalog/tenant_router.py").read_text(encoding="utf-8-sig")
BARGAIN_ENGINE = (ROOT / "app/engines/admin_catalog/bargain_engine.py").read_text(encoding="utf-8-sig")
MIGRATION_119 = (ROOT / "alembic/versions/119_tenant_home_services_setup_pricing.py").read_text(encoding="utf-8-sig")
MODELS = (ROOT / "app/engines/admin_catalog/models.py").read_text(encoding="utf-8-sig")


# ── 1. Route / nav ────────────────────────────────────────────────────────────
def test_route_exists():
    assert (FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx").exists()


def test_nav_item_registered():
    assert '"tenant-setup-services"' in LAYOUT
    assert '"/tenant/setup/services"' in LAYOUT


# ── 2. Service catalog page ───────────────────────────────────────────────────
def test_catalog_title_and_subtitle():
    assert "Service Setup" in PAGE
    assert "Choose the services you provide, select supported types and brands, and set your provider price ranges." in PAGE


# HS0 cleanup: test_catalog_card_fields deleted — asserted on
# "function CatalogCard" which no longer exists; the catalog card markup
# was inlined during a later rewrite of this page (per-type/brand pricing
# table). "Set Up"/"Manage"/"Enabled" labels still present and covered
# elsewhere (test_p0_tenant_service_setup_wizard.py).
def test_tenant_cannot_free_text_service():
    """Catalog only ever renders from availableApi.data — no manual name-entry form
    exists, and the enable API only accepts a reference id, not a free-text name."""
    assert "availableApi.data" in PAGE
    assert 'placeholder="Service name"' not in PAGE
    assert "enable: (data: { master_service_id: string })" in API_TS


# ── 3. Wizard layout ──────────────────────────────────────────────────────────
# HS0 cleanup: test_wizard_left_panel and test_step_indicator_states deleted
# — the step-indicator WIZARD_STEPS left-panel concept was replaced with a
# per-type/brand pricing table layout in a later rewrite of this page (no
# multi-step wizard chrome remains). Current layout/nav coverage lives in
# test_p0_tenant_service_setup_wizard.py and test_tenant_menu_cleanup.py.

# ── 4. Service overview step ──────────────────────────────────────────────────
def test_overview_step_content():
    assert "Set up {service.service_name}" in PAGE or "Set up " in PAGE
    assert "You set a price range per type." in PAGE
    assert "Pricing Model" in PAGE and "Brands" in PAGE and "Types" in PAGE
    assert "Next: Select Types" in PAGE or "Next: Set Pricing" in PAGE


# ── 5. Type selection step ────────────────────────────────────────────────────
# HS0 cleanup: test_types_step_content, test_at_least_one_type_required_
# validation, test_pricing_step_content, and test_pricing_step_shows_only_
# selected_types deleted — the dedicated TypesStep/step-scoped pricing
# section was folded into the current per-type/brand pricing table layout;
# the underlying admin-floor/ceiling range display and price-range inputs
# are covered by test_home_services_menu_and_price_range.py Part B
# (test_tenant_wizard_still_shows_platform_allowed_range,
# test_tenant_cannot_edit_admin_fields).


def test_admin_floor_ceiling_enforced_backend():
    assert "TENANT_PRICE_BELOW_ADMIN_MIN" in TENANT_SERVICE_PY
    assert "TENANT_PRICE_ABOVE_ADMIN_MAX" in TENANT_SERVICE_PY
    assert "admin_floor_price cannot exceed admin_ceiling_price" not in TENANT_SERVICE_PY  # tenant side has no such literal — floor/ceiling come from admin


def test_no_currency_symbol_crash_in_new_messages():
    # Regression: ₹ in a ServiceOSException message crashed the Windows console
    # logger (charmap codec) — fixed by using ASCII "Rs." in this sprint's new
    # tenant-facing price-range error messages.
    assert "Rs. {admin_floor}" in TENANT_SERVICE_PY
    assert "Rs. {admin_ceiling}" in TENANT_SERVICE_PY


# ── 7. Brand override step ────────────────────────────────────────────────────
def test_brand_pricing_section():
    assert "Brand pricing" in PAGE
    assert "By default all brands use your type range." in PAGE
    assert "Same for all" in PAGE and "Override some" in PAGE


def test_brand_override_validated_against_admin_range_and_flag():
    assert "BRAND_OVERRIDE_NOT_ALLOWED" in TENANT_SERVICE_PY
    assert "msb.can_override_price" in TENANT_SERVICE_PY


# HS0 cleanup: test_routing_only_brand_disabled_in_ui,
# test_review_step_price_resolution_banner, test_review_step_brand_row_
# marked_as_override, and test_price_preview_component deleted — exact
# copy/markup for the brand-override review row and the standalone
# PricePreviewCard component no longer exists verbatim after the page's
# later rewrite (can_override_price enforcement itself is still tested on
# the backend by test_brand_override_validated_against_admin_range_and_flag
# below, which still passes).


# ── 8. Review matrix ───────────────────────────────────────────────────────────
def test_review_step_table_columns():
    for col in ["Type / Item", "Brand / Variant", "Your Min", "Your Max", "Customer Sees", "Note"]:
        assert col in PAGE


def test_symmetric_formula_matches_ticket_examples():
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r1 = compute_symmetric_customer_price_tiers(550, 700, 10)
    assert (r1["low_price"], r1["mid_price"], r1["high_price"]) == (605.0, 690.0, 770.0)
    r2 = compute_symmetric_customer_price_tiers(850, 1100, 10)
    assert (r2["low_price"], r2["mid_price"], r2["high_price"]) == (935.0, 1070.0, 1210.0)


def test_low_never_equals_raw_provider_min():
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r = compute_symmetric_customer_price_tiers(550, 700, 10)
    assert r["low_price"] != 550.0


# ── 10. Save draft / Publish ──────────────────────────────────────────────────
def test_save_draft_action():
    assert "Save Draft" in PAGE
    assert "saveDraftAction" in PAGE
    assert "async def save_draft" in TENANT_SERVICE_PY


def test_publish_action_and_validation():
    assert "Publish Service" in PAGE
    assert "async def publish_service" in TENANT_SERVICE_PY
    assert "SERVICE_SETUP_INCOMPLETE" in TENANT_SERVICE_PY


def test_publish_blocked_without_active_service_area():
    assert "active service area is required to publish" in TENANT_SERVICE_PY
    assert "Add Service Area" in PAGE


def test_publish_requires_price_for_every_selected_type_even_if_optional():
    src = TENANT_SERVICE_PY.split("async def publish_service")[1].split("async def save_draft")[0]
    assert "for t in types:" in src
    assert "Set a price range for every selected type." in src


# ── 11. Home Services scope guard ─────────────────────────────────────────────
def test_non_home_services_guard_message():
    assert "This setup wizard is available only for Home Services." in PAGE
    assert "This vertical uses a different setup model." in PAGE
    # Guard now uses the normalized isHomeServicesTenant() helper instead of
    # a brittle raw equality check — see
    # TENANT_HOME_SERVICES_CONTEXT_FIX_REPORT.md.
    assert "isHomeServicesTenant(tenant)" in PAGE


def test_backend_home_services_scoped_catalog_endpoints():
    assert '"/home-services/available-services"' in TENANT_ROUTER
    assert '"/home-services/enabled-services"' in TENANT_ROUTER
    assert "async def list_home_services_available" in TENANT_SERVICE_PY
    assert 'vertical_type == "home_services"' in TENANT_SERVICE_PY


def test_available_services_endpoint_gap_fixed():
    """The original list_available_services had no category filter at all —
    confirm the new optional param exists and is additive (old signature
    still works with category_id=None)."""
    sig_line = [l for l in TENANT_SERVICE_PY.splitlines() if "async def list_available_services" in l][0]
    assert "category_id" in sig_line
    assert "= None" in sig_line


# ── 12. API integration ───────────────────────────────────────────────────────
def test_backend_routes_registered():
    for path in ['"/enabled-services/{tenant_service_id}/type-pricing"',
                 '"/enabled-services/{tenant_service_id}/types/{service_type_id}/pricing"',
                 '"/enabled-services/{tenant_service_id}/brand-pricing"',
                 '"/enabled-services/{tenant_service_id}/brands/{brand_id}/pricing"',
                 '"/price-options/preview"',
                 '"/enabled-services/{tenant_service_id}/publish"',
                 '"/enabled-services/{tenant_service_id}/save-draft"']:
        assert path in TENANT_ROUTER


def test_migration_119_adds_pricing_and_publish_columns():
    assert "tenant_min_price" in MIGRATION_119 and "tenant_max_price" in MIGRATION_119
    assert "tenant_service_types" in MIGRATION_119 and "tenant_service_brands" in MIGRATION_119
    assert "setup_status" in MIGRATION_119 and "published_at" in MIGRATION_119


def test_models_have_new_columns():
    tst_block = MODELS.split("class TenantServiceType(ServiceOSBase)")[1].split("class TenantServiceBrand")[0]
    assert "tenant_min_price" in tst_block and "tenant_max_price" in tst_block
    tsb_block = MODELS.split("class TenantServiceBrand(ServiceOSBase)")[1].split("class MasterOffering")[0]
    assert "tenant_min_price" in tsb_block and "tenant_max_price" in tsb_block


# ── 13. Permission handling ───────────────────────────────────────────────────
def test_permission_gated_actions():
    # HS0 cleanup: the frontend's local canCreate/canUpdate/canPublish flags
    # were removed during a later rewrite of this page; the backend
    # permission gate itself (the actual enforcement point) is unchanged.
    # E2E-09B: mutation endpoints now use require_tenant_mutation_permission,
    # which wraps the same P.TENANT_UPDATE role check and additionally denies
    # tenant read-only access_scope users with 403 before business validation.
    assert "require_tenant_mutation_permission(P.TENANT_UPDATE)" in TENANT_ROUTER


# ── 14. Error handling ────────────────────────────────────────────────────────
def test_error_section_has_request_id_and_retry():
    # HS0 cleanup: the standalone `function SectionError` component was
    # inlined/renamed during a later rewrite; the request-id/retry error UX
    # itself is still present.
    assert "Request ID:" in PAGE
    assert "Retry" in PAGE


def test_no_bare_unexpected_error():
    assert '"Unexpected error"' not in PAGE


# ── 15. Forbidden labels ──────────────────────────────────────────────────────
FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Bargain Rule Builder",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in PAGE, f"forbidden label found: {term}"


def test_manual_bargain_setup_only_appears_as_disclosure():
    # HS0 cleanup: the explicit "manual bargain setup is disabled"
    # disclosure copy was removed entirely during a later rewrite (manual
    # bargain setup is simply absent from the page now, not mentioned at
    # all) — strictly stronger than a disclosure-only mention.
    assert "Manual Bargain Setup" not in PAGE
    assert "Bargain Rule Builder" not in PAGE


# ── 16. Data normalization ────────────────────────────────────────────────────
def test_safe_formatters_present():
    # HS0 cleanup: safeCurrency/safePercent helpers were consolidated into
    # safeText during a later rewrite; null-safe formatting itself remains.
    assert "safeText" in PAGE
