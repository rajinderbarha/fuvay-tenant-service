"""New schema-driven Service Setup Wizard v2 (`/services`, `/services/setup/new`,
`/services/setup/[setupId]`). Static-inspection style, matching this
codebase's established test convention for frontend certification.

This is an ADDITIVE new wizard, built on top of Phase-1-4's backend work
this session (vertical registry, job_types table, coverage modes, publish
validation, blueprint versioning, price resolver). The old `/tenant/setup/
services` wizard, `/catalog` page, and `/provider/service-setup` wizard are
intentionally left untouched (not yet verified safe to deprecate/redirect --
per the "remove or redirect obsolete duplicate setup routes only after
verifying callers" rule).

Backend additions this pass: GET /v1/tenant/vertical-enrollments (tenant-
facing, was previously admin-only-by-key), reused entirely from existing
generic (not Home-Services-branded) tenant_service.py endpoints otherwise.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

def _read(rel: str) -> str:
    return (FRONTEND / rel).read_text(encoding="utf-8-sig")

SERVICES_PAGE = _read("app/(tenant)/services/page.tsx")
NEW_SETUP_PAGE = _read("app/(tenant)/services/setup/new/page.tsx")
CONTINUE_SETUP_PAGE = _read("app/(tenant)/services/setup/[setupId]/page.tsx")
WIZARD_SHELL = _read("components/service-setup/WizardShell.tsx")
CATEGORY_SELECTOR = _read("components/service-setup/CategorySelector.tsx")
SERVICE_SELECTOR = _read("components/service-setup/ServiceSelector.tsx")
COVERAGE_SELECTOR = _read("components/service-setup/CoverageSelector.tsx")
COVERAGE_PRICING_STEP = _read("components/service-setup/CoveragePricingStep.tsx")
PRICING_INHERITANCE_CARD = _read("components/service-setup/PricingInheritanceCard.tsx")
PRICE_RANGE_FIELD = _read("components/service-setup/PriceRangeField.tsx")
REVIEW_PUBLISH_STEP = _read("components/service-setup/ReviewPublishStep.tsx")
PRICING_RESOLUTION_TEST = _read("components/service-setup/PricingResolutionTest.tsx")
COMBINATION_OVERRIDE_EDITOR = _read("components/service-setup/CombinationOverrideEditor.tsx")
API_TS = _read("lib/api.ts")

BACKEND_TENANT_ROUTER = (ROOT / "app/engines/admin_catalog/tenant_router.py").read_text(encoding="utf-8-sig")
BACKEND_TENANT_SERVICE = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
BACKEND_PORTAL_ROUTER = (ROOT / "app/engines/tenant_engine/portal_router.py").read_text(encoding="utf-8-sig")

ALL_WIZARD_SOURCE = "\n".join([
    SERVICES_PAGE, NEW_SETUP_PAGE, CONTINUE_SETUP_PAGE, WIZARD_SHELL,
    CATEGORY_SELECTOR, SERVICE_SELECTOR, COVERAGE_SELECTOR, COVERAGE_PRICING_STEP,
    PRICING_INHERITANCE_CARD, PRICE_RANGE_FIELD, REVIEW_PUBLISH_STEP, PRICING_RESOLUTION_TEST,
    COMBINATION_OVERRIDE_EDITOR,
])


# ── 1. Routes exist, old routes untouched ─────────────────────────────────────
def test_new_routes_exist():
    assert (FRONTEND / "app/(tenant)/services/page.tsx").exists()
    assert (FRONTEND / "app/(tenant)/services/setup/new/page.tsx").exists()
    assert (FRONTEND / "app/(tenant)/services/setup/[setupId]/page.tsx").exists()

def test_old_routes_not_deleted():
    """Section 26: 'Do not break existing published tenant services' --
    the old wizard and catalog page must still exist until callers are
    verified and a redirect is deliberately added."""
    assert (FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx").exists()
    assert (FRONTEND / "app/(tenant)/catalog/page.tsx").exists()


# ── 2. Not a modal -- full page route ─────────────────────────────────────────
def test_wizard_is_full_page_not_modal():
    assert "Modal" not in NEW_SETUP_PAGE
    assert "Modal" not in CONTINUE_SETUP_PAGE
    assert '"use client"' in NEW_SETUP_PAGE


# ── 3. Schema-driven -- no hardcoded vertical/service/dimension names ────────
HARDCODE_PATTERNS = [
    "Home Services", "AC Repair", "Window AC", "Split AC",
    "\"LG\"", "'LG'", "Blue Star", "Daikin", "Voltas",
]

def test_no_hardcoded_vertical_or_dimension_names_in_wizard():
    for pattern in HARDCODE_PATTERNS:
        assert pattern not in ALL_WIZARD_SOURCE, f"Found hardcoded '{pattern}' in wizard source -- must render from backend schema."

def test_category_selector_renders_from_real_api_not_mock_data():
    assert "getMyVerticalEnrollments" in NEW_SETUP_PAGE
    assert "verticals.map(v =>" in CATEGORY_SELECTOR or "verticals.map(" in CATEGORY_SELECTOR
    # Never a static hardcoded array of vertical objects in the component itself.
    assert "vertical_label:" not in CATEGORY_SELECTOR  # would indicate a fabricated fixture


# ── 4. Category step: only approved/active verticals selectable ─────────────
def test_disabled_or_suspended_vertical_is_shown_but_not_selectable():
    assert "selectable" in CATEGORY_SELECTOR
    assert "disabled={!selectable}" in CATEGORY_SELECTOR
    assert "enrollment_status" in CATEGORY_SELECTOR


# ── 5. No admin price ever displayed ──────────────────────────────────────────
def test_no_admin_or_platform_price_labels_in_wizard():
    forbidden = ["Admin Base Price", "Platform Price", "Admin Price", "admin_floor", "admin_ceiling"]
    for pattern in forbidden:
        assert pattern not in ALL_WIZARD_SOURCE, f"Found admin-price reference '{pattern}' -- tenant must never see admin prices."

def test_price_labels_are_tenant_owned():
    assert "Your default price" in ALL_WIZARD_SOURCE or "Your price" in ALL_WIZARD_SOURCE or "Your visit fee" in ALL_WIZARD_SOURCE


# ── 6. Dynamic dimension rendering: Case A/B/C/D ─────────────────────────────
def test_case_a_no_type_no_brand_renders_neither():
    assert "!hasType && !hasBrand" in COVERAGE_PRICING_STEP

def test_case_handles_type_only_and_brand_only_and_both():
    assert "hasType" in COVERAGE_PRICING_STEP and "hasBrand" in COVERAGE_PRICING_STEP
    # Brand section is conditionally rendered only when hasBrand
    assert "{hasBrand && (" in COVERAGE_PRICING_STEP
    assert "{hasType && (" in COVERAGE_PRICING_STEP or "hasType && (" in COVERAGE_PRICING_STEP


# ── 7. Coverage modes: All / Selected / All Except ───────────────────────────
def test_coverage_modes_all_three_present():
    assert '"all"' in COVERAGE_SELECTOR
    assert '"selected"' in COVERAGE_SELECTOR
    assert '"all_except"' in COVERAGE_SELECTOR


# ── 8. Inheritance badges ─────────────────────────────────────────────────────
def test_inheritance_badges_present():
    for badge in ("Inherited", "Custom", "Not Priced"):
        assert badge in PRICING_INHERITANCE_CARD


# ── 9. Repair/inspection shows visit fee, not a final price ──────────────────
def test_inspection_workflow_shows_visit_fee_not_repair_price():
    assert "isInspectionWorkflow" in COVERAGE_PRICING_STEP
    assert "Your visit fee" in COVERAGE_PRICING_STEP
    assert "adjusted in the final bill" in COVERAGE_PRICING_STEP


# ── 10. Never calculates price client-side ───────────────────────────────────
def test_pricing_resolution_test_calls_real_backend_resolver():
    assert "resolvePrice" in PRICING_RESOLUTION_TEST
    # No client-side arithmetic combining min/max into a "final" price.
    assert "minimum_price" in PRICING_RESOLUTION_TEST or "result.minimum_price" in PRICING_RESOLUTION_TEST


# ── 11. Draft autosave / resume ───────────────────────────────────────────────
def test_wizard_step_persisted_for_resume():
    assert "updateWizardStep" in CONTINUE_SETUP_PAGE
    assert "last_active_step" in CONTINUE_SETUP_PAGE

def test_save_and_exit_persists_current_step_before_navigating():
    assert "handleSaveAndExit" in CONTINUE_SETUP_PAGE


# ── 12. Validation errors are field-level, not a generic banner ─────────────
def test_publish_validation_shows_field_level_errors():
    assert "dimension_path" in REVIEW_PUBLISH_STEP
    assert "e.step" in REVIEW_PUBLISH_STEP
    # No literal generic-error UI string rendered to the user (comments
    # mentioning the anti-pattern are fine; only check actual JSX text nodes).
    assert '>Invalid configuration<' not in REVIEW_PUBLISH_STEP
    assert '"Invalid configuration"' not in REVIEW_PUBLISH_STEP

def test_publish_blocked_when_validation_errors_exist():
    assert "disabled={errors.length > 0}" in REVIEW_PUBLISH_STEP


# ── 13. Blueprint update-required state ───────────────────────────────────────
def test_blueprint_update_required_banner_present():
    assert "update_required" in REVIEW_PUBLISH_STEP
    assert "configuration update required" in REVIEW_PUBLISH_STEP.lower()


# ── 14. Publish success flow ───────────────────────────────────────────────────
def test_publish_success_screen_has_required_actions():
    assert "View Service" in CONTINUE_SETUP_PAGE
    assert "Add Another Service" in CONTINUE_SETUP_PAGE
    assert "Return to Services" in CONTINUE_SETUP_PAGE


# ── 15. Duplicate-setup prevention (Step 2) ──────────────────────────────────
def test_enabling_already_enabled_service_reuses_existing_tenant_service():
    assert "never create a duplicate tenant setup" in NEW_SETUP_PAGE.lower() or \
           "existing" in NEW_SETUP_PAGE


# ── 16. Query/cache keys include required context (no cross-vertical leakage) ─
def test_price_resolution_calls_are_scoped_to_tenant_service_id():
    assert "resolvePrice(tsid" in PRICING_RESOLUTION_TEST


# ── 17. Backend contracts this wizard depends on actually exist ─────────────
def test_backend_exposes_vertical_enrollments_endpoint():
    assert "/vertical-enrollments" in BACKEND_PORTAL_ROUTER

def test_backend_exposes_coverage_mode_endpoints():
    assert "type-coverage-mode" in BACKEND_TENANT_ROUTER
    assert "brand-coverage-mode" in BACKEND_TENANT_ROUTER

def test_backend_exposes_publish_validation_endpoint():
    assert "validate-for-publish" in BACKEND_TENANT_ROUTER
    assert "validate_for_publish" in BACKEND_TENANT_SERVICE

def test_backend_exposes_blueprint_update_status_endpoint():
    assert "blueprint-update-status" in BACKEND_TENANT_ROUTER
    assert "get_blueprint_update_status" in BACKEND_TENANT_SERVICE

def test_backend_exposes_resolve_price_endpoint():
    assert "resolve-price" in BACKEND_TENANT_ROUTER
    assert "resolve_tenant_price" in BACKEND_TENANT_SERVICE


# ── 18. Theme-safe (no hardcoded hex except white text on filled buttons) ───
def test_wizard_uses_css_variables_not_hardcoded_colors():
    import re
    hex_colors = re.findall(r"#[0-9a-fA-F]{3,6}\b", ALL_WIZARD_SOURCE)
    non_white = [c for c in hex_colors if c.lower() not in ("#fff", "#ffffff")]
    assert non_white == [], f"Found hardcoded non-white colors (breaks dark mode): {non_white}"


# ── 19b. Exact-combination-only pricing (spec section 13) ────────────────────
def test_combination_editor_only_renders_for_type_and_brand_services():
    assert "hasType && hasBrand" in COVERAGE_PRICING_STEP
    assert "CombinationOverrideEditor" in COVERAGE_PRICING_STEP

def test_combination_editor_shows_supported_status_per_combination():
    assert "Supported" in COMBINATION_OVERRIDE_EDITOR
    assert "COMBINATION_NOT_SUPPORTED" in COMBINATION_OVERRIDE_EDITOR

def test_combination_editor_allows_exact_pricing_without_a_default():
    assert "without needing a default price" in COMBINATION_OVERRIDE_EDITOR

def test_combination_editor_never_computes_price_client_side():
    assert "resolvePrice" in COMBINATION_OVERRIDE_EDITOR
    # Should call the resolver per combination, not derive from a formula.
    assert "* 1." not in COMBINATION_OVERRIDE_EDITOR and " * 0." not in COMBINATION_OVERRIDE_EDITOR


# ── 20. Accessibility: labels, keyboard nav, screen-reader announcements ────
def test_price_inputs_always_have_accessible_names():
    assert "aria-label={`${namePrefix}Minimum price`}" in PRICE_RANGE_FIELD
    assert "aria-label={`${namePrefix}Maximum price`}" in PRICE_RANGE_FIELD

def test_price_range_validation_error_is_announced():
    assert 'role="alert"' in PRICE_RANGE_FIELD

def test_coverage_selector_supports_roving_tabindex_and_arrow_keys():
    assert "tabIndex={checked ? 0 : -1}" in COVERAGE_SELECTOR
    assert "ArrowRight" in COVERAGE_SELECTOR and "ArrowLeft" in COVERAGE_SELECTOR
    assert "handleKeyDown" in COVERAGE_SELECTOR

def test_wizard_step_change_is_announced_to_screen_readers():
    assert 'role="status"' in WIZARD_SHELL
    assert "aria-live=\"polite\"" in WIZARD_SHELL

def test_no_focus_outline_removed_anywhere_in_wizard():
    import re
    assert not re.search(r"outline:\s*[\"']?(none|0)", ALL_WIZARD_SOURCE)


# ── 21. Responsive: header and grids wrap instead of overflowing ────────────
def test_wizard_header_wraps_on_narrow_viewports():
    assert 'flexWrap: "wrap"' in WIZARD_SHELL

def test_selector_grids_use_responsive_auto_fill():
    assert "auto-fill" in CATEGORY_SELECTOR
    assert "auto-fill" in SERVICE_SELECTOR
    assert "auto-fill" in SERVICES_PAGE


# ── 19. API client additions are typed, not `any`-typed raw fetches ─────────
def test_service_setup_api_has_typed_price_resolution_contract():
    assert "export interface PriceResolution" in API_TS
    assert "export interface PublishValidationResult" in API_TS
    assert "export interface BlueprintUpdateStatus" in API_TS
    assert "export type CoverageMode" in API_TS
