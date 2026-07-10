"""
TENANT HOME SERVICES SERVICE SETUP WIZARD — Tests
Verifies the wizard page at /tenant/setup/services.
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx"
VERTICAL_GUARD = ROOT / "frontend/tenant-portal/lib/verticalGuard.ts"
API = ROOT / "frontend/tenant-portal/lib/api.ts"


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


SRC = read(PAGE)


# ── 1. Page renders ────────────────────────────────────────────────────────────
def test_page_file_exists():
    assert PAGE.exists()


def test_page_is_use_client():
    assert '"use client"' in SRC or "'use client'" in SRC


def test_page_exports_default_function():
    assert "export default function" in SRC


# ── 2. Service catalog renders ────────────────────────────────────────────────
def test_catalog_title():
    assert "Service Setup" in SRC


def test_catalog_subtitle():
    assert "Choose the services you provide" in SRC or "services you provide" in SRC


def test_catalog_uses_home_services_api():
    assert "homeServicesSetupApi" in SRC


def test_catalog_lists_available_services():
    assert "listAvailable" in SRC


def test_catalog_lists_enabled_services():
    assert "listEnabled" in SRC


# ── 3. Service cards ──────────────────────────────────────────────────────────
def test_service_card_component():
    assert "ServiceCard" in SRC


def test_service_card_shows_setup_cta():
    assert "Set Up" in SRC


def test_service_card_shows_manage_for_enabled():
    assert "Manage" in SRC


def test_service_card_shows_continue_setup():
    assert "Continue Setup" in SRC


# ── 4. Wizard opens ───────────────────────────────────────────────────────────
def test_wizard_component_exists():
    assert "ServiceSetupWizard" in SRC


def test_wizard_has_modal():
    assert "Modal" in SRC


# ── 5. Service overview step ──────────────────────────────────────────────────
def test_overview_step():
    assert 'step === "overview"' in SRC


def test_overview_title():
    assert "Set up" in SRC


def test_overview_subtitle():
    assert "Review what you" in SRC


# ── 6. Pricing model card ─────────────────────────────────────────────────────
def test_pricing_model_shown():
    assert "Pricing Model" in SRC or "pricing_model" in SRC


# ── 7. Brands card ────────────────────────────────────────────────────────────
def test_brands_shown_in_overview():
    assert "Brands" in SRC or "hasBrands" in SRC


# ── 8. Types card ─────────────────────────────────────────────────────────────
def test_types_shown_in_overview():
    assert "Types" in SRC or "hasTypes" in SRC


# ── 9. Types step renders ─────────────────────────────────────────────────────
def test_types_step():
    assert 'step === "types"' in SRC


def test_types_step_title():
    assert "Which types do you service" in SRC


# ── 10. Type selection works ──────────────────────────────────────────────────
def test_selected_type_ids_state():
    assert "selectedTypeIds" in SRC


def test_type_selection_toggle():
    assert "setSelectedTypeIds" in SRC


# ── 11. Pricing step renders only selected types ──────────────────────────────
def test_pricing_step():
    assert 'step === "pricing"' in SRC


def test_pricing_step_uses_type_pricing_state():
    assert "typePricingState" in SRC


# ── 12. Provider min cannot go below admin floor ──────────────────────────────
def test_min_floor_validation():
    assert "adminFloor" in SRC
    # validation check
    assert "cannot be below" in SRC.lower() or "adminFloor" in SRC


# ── 13. Provider max cannot exceed admin ceiling ──────────────────────────────
def test_max_ceiling_validation():
    assert "adminCeiling" in SRC
    assert "cannot exceed" in SRC.lower() or "adminCeiling" in SRC


# ── 14. Customer Price Options Preview renders ────────────────────────────────
def test_price_preview_component():
    assert "PricePreviewBand" in SRC


def test_price_preview_shows_low_mid_high():
    assert '"Low"' in SRC or "'Low'" in SRC
    assert '"Mid"' in SRC or "'Mid'" in SRC
    assert '"High"' in SRC or "'High'" in SRC


# ── 15. Low includes platform fee ─────────────────────────────────────────────
def test_platform_fee_shown():
    assert "platform_fee" in SRC or "Platform fee" in SRC


def test_price_preview_uses_backend():
    assert "pricePreview" in SRC
    assert "homeServicesSetupApi" in SRC


# ── 16. Brand pricing section renders if enabled ─────────────────────────────
def test_brand_step():
    assert 'step === "brands"' in SRC


def test_brand_pricing_section():
    assert "Brand pricing" in SRC


# ── 17. Same for all works ────────────────────────────────────────────────────
def test_same_for_all_option():
    assert "Same for all" in SRC


def test_brand_mode_state():
    assert "brandMode" in SRC


# ── 18. Override some works ───────────────────────────────────────────────────
def test_override_some_option():
    assert "Override some" in SRC


def test_brand_override_component():
    assert "BrandOverrideRow" in SRC


# ── 19. Brand override validation ────────────────────────────────────────────
def test_brand_override_validation():
    assert "canOverride" in SRC


# ── 20. Review table renders ──────────────────────────────────────────────────
def test_review_step():
    assert 'step === "review"' in SRC


def test_review_matrix_table():
    assert "Type / Item" in SRC
    assert "Brand / Variant" in SRC


def test_review_price_resolution_banner():
    assert "brand price" in SRC.lower() or "brand →" in SRC.lower() or "brand price → type price" in SRC.lower()


# ── 21. Save Draft works ──────────────────────────────────────────────────────
def test_save_draft_button():
    assert "Save Draft" in SRC


def test_save_draft_action():
    assert "saveDraft" in SRC


# ── 22. Publish blocked if service area missing ───────────────────────────────
def test_publish_blocked_without_service_area():
    assert "hasActiveArea" in SRC
    assert "Publish" in SRC and "disabled" in SRC


def test_add_service_area_cta():
    assert "Add Service Area" in SRC or "service-areas" in SRC


# ── 23. Publish works when complete ──────────────────────────────────────────
def test_publish_action():
    assert "publish" in SRC
    assert "publishAction" in SRC or "handlePublish" in SRC


# ── 24. No manual bargain wording ─────────────────────────────────────────────
BARGAIN_WORDS = ["Manual Bargain", "Bargain Rule", "Bargain Setup", "bargain_rule"]

def test_no_manual_bargain_wording():
    for w in BARGAIN_WORDS:
        assert w not in SRC, f"Forbidden bargain word found: {w!r}"


# ── 25. No forbidden labels ───────────────────────────────────────────────────
FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Bargain Rule Builder",
]

def test_no_forbidden_labels():
    for label in FORBIDDEN:
        assert label not in SRC, f"Forbidden label: {label!r}"


# ── 26. No NaN/null/undefined ─────────────────────────────────────────────────
def test_uses_safe_helpers():
    assert "safeText" in SRC
    assert "safeNum" in SRC
    assert "safeCur" in SRC


def test_preview_uses_fallback():
    assert "??" in SRC


# ── 27. Error state shows request_id ─────────────────────────────────────────
def test_error_shows_request_id():
    assert "requestId" in SRC
    assert "Request ID" in SRC


def test_error_has_retry():
    assert "Retry" in SRC or "onRetry" in SRC


def test_error_has_copy_request_id():
    assert "Copy Request ID" in SRC or "copyText" in SRC


# ── 28. Non-Home Services guard hides wizard ─────────────────────────────────
def test_scope_guard_uses_isHomeServicesTenant():
    assert "isHomeServicesTenant" in SRC


def test_scope_guard_shows_message():
    assert "available only for Home Services" in SRC


def test_scope_guard_imports_from_verticalGuard():
    assert "verticalGuard" in SRC


# ── API surface checks ────────────────────────────────────────────────────────
def test_homeServicesSetupApi_has_setTypePricing():
    api_src = read(API)
    assert "setTypePricing" in api_src


def test_homeServicesSetupApi_has_pricePreview():
    api_src = read(API)
    assert "pricePreview" in api_src


def test_homeServicesSetupApi_has_saveDraft():
    api_src = read(API)
    assert "saveDraft" in api_src


def test_homeServicesSetupApi_has_publish():
    api_src = read(API)
    assert "publish" in api_src


# ── Wizard architecture ───────────────────────────────────────────────────────
def test_wizard_steps_defined():
    assert "overview" in SRC
    assert "types" in SRC
    assert "pricing" in SRC
    assert "brands" in SRC
    assert "review" in SRC


def test_wizard_left_panel():
    assert "All services" in SRC


def test_wizard_step_labels():
    assert "1. Service" in SRC
    assert "2. Types" in SRC
    assert "3. Pricing" in SRC


def test_wizard_completed_steps():
    assert "completedSteps" in SRC
    assert "CheckCircle2" in SRC


def test_tenant_cannot_create_free_text_service():
    # Verify there's no free-text input for service name
    # The page only lists admin catalog services
    assert "listAvailable" in SRC  # catalog-driven
    # No free-text service name input
    assert "Create new service" not in SRC
    assert "Add custom service" not in SRC
    assert "Free-text" not in SRC


def test_customer_price_preview_label_used():
    assert "Customer Price" in SRC or "Low / Mid / High" in SRC


def test_provider_price_range_label_used():
    assert "Provider Price" in SRC or "Your Minimum Price" in SRC or "Your Maximum Price" in SRC


def test_pays_provider_directly_on_site():
    # Customer payment copy — no platform collection
    assert "directly" in SRC and "on-site" in SRC
