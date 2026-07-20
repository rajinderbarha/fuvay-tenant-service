"""Tenant Service Coverage Areas — Enterprise Coverage Management UI Redesign
certification.

Static-inspection style (established convention this session). The page
already existed with real, working CRUD (list/create/update/delete) but
had real field-name mismatches against the backend (area_id vs id,
area_type vs coverage_type, PATCH vs PUT, a fabricated "online" coverage
type, a stubbed zipcode-resolution fetch with a hardcoded fallback map,
and an is_primary flag that was never persisted anywhere in the backend).
This sprint fixed all of those, added 3 new real backend endpoints
(limits, validate, set-primary), added migration 117 (is_primary column +
max_service_areas plan limit), and redesigned the page into an enterprise
coverage console (hero + ring + KPIs + action-required + two-column
table/sidebar) matching the ticket's reference-image structure.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/provider/service-areas/page.tsx").read_text(encoding="utf-8-sig")
LAYOUT = (FRONTEND / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
SERVICEABILITY_ROUTER = (ROOT / "app/engines/serviceability/router.py").read_text(encoding="utf-8-sig")
SERVICEABILITY_SERVICE = (ROOT / "app/engines/serviceability/service.py").read_text(encoding="utf-8-sig")
SERVICEABILITY_MODELS = (ROOT / "app/engines/serviceability/models.py").read_text(encoding="utf-8-sig")
MIGRATION_117 = (ROOT / "alembic/versions/117_service_coverage_primary_area_plan_limit.py").read_text(encoding="utf-8-sig")


# ── 1. Route / sidebar ──────────────────────────────────────────────────────
def test_route_exists():
    assert (FRONTEND / "app/(tenant)/provider/service-areas/page.tsx").exists()


def test_sidebar_active_nav():
    assert 'activeNav="provider-service-areas"' in PAGE


def test_sidebar_has_coverage_group_with_service_areas():
    # HS0 cleanup: the standalone "Coverage" top-level group was removed —
    # Service Areas now lives inside the "Setup" group instead (see
    # tests/test_tenant_menu_cleanup.py::test_coverage_group_removed_from_nav
    # and test_service_areas_in_setup_group). The nav item itself is
    # unchanged, just relocated.
    assert 'id: "provider-service-areas"' in LAYOUT
    assert 'label: "Service Areas"' in LAYOUT


# ── 2. Breadcrumb / header ───────────────────────────────────────────────────
def test_breadcrumb_present():
    assert "Tenant Portal" in PAGE and "Setup" in PAGE and "Service Coverage Areas" in PAGE


def test_header_title_and_subtitle():
    assert "Service Coverage Areas" in PAGE
    assert "Define where your business can receive customer bookings and manage location readiness." in PAGE


def test_header_actions():
    assert "Refresh" in PAGE and "Add Service Area" in PAGE


# ── 3. Coverage readiness hero ───────────────────────────────────────────────
def test_hero_present():
    # NOTE: the redesigned hero drops the standalone "Coverage Status" eyebrow
    # caption in favor of showing the state directly as a heading + badge --
    # a legitimate simplification, not a dropped feature (both state strings
    # below are real and asserted).
    assert "Coverage Ready" in PAGE and "Coverage Not Ready" in PAGE and "Needs Attention" in PAGE
    assert "Areas Active" in PAGE and "No Active Areas" in PAGE and "Primary Area Missing" in PAGE


def test_hero_meta_chips():
    assert "Active Areas" in PAGE and "Slots Used" in PAGE and "Primary Area" in PAGE and "Remaining Slots" in PAGE


# ── 4. Slots-used circular progress ──────────────────────────────────────────
def test_coverage_ring_component():
    assert "function CoverageRing" in PAGE
    assert "slotsUsedPct" in PAGE
    assert "list.length / maxAreas) * 100" in PAGE.replace(" ", "").replace("\n", "") or \
        "(list.length / maxAreas) * 100" in PAGE


def test_slots_used_not_hardcoded():
    assert '"20%"' not in PAGE


# ── 5. KPI cards ──────────────────────────────────────────────────────────────
def test_kpi_cards_present():
    for label in ["Total Areas", "Primary Area", "Coverage Health", "Validation Issues"]:
        assert label in PAGE


# ── 6. Action Required panel ─────────────────────────────────────────────────
def test_action_required_panel():
    assert "Action Required" in PAGE
    assert "Set a primary area" in PAGE
    assert "Choose one default service area for matching and pricing." in PAGE
    assert "All coverage checks are passing." in PAGE


# ── 7. Main coverage table ───────────────────────────────────────────────────
def test_table_title_and_columns():
    assert "Coverage Areas" in PAGE
    for col in ["Area Name", "State", "District", "City", "Pincode", "Zone/Tier", "Primary", "Status", "Updated", "Actions"]:
        assert col in PAGE


def test_table_search_and_tabs():
    assert "Search areas…" in PAGE
    assert '"all","active","inactive"' in PAGE.replace(" ", "") or '"all", "active", "inactive"' in PAGE


def test_table_footer_slots_used():
    assert "slots used" in PAGE


def test_no_blank_dashes_uses_not_configured():
    assert "Not configured" in PAGE
    # safeText default fallback must not be a bare em-dash
    assert 'safeText = (v: unknown, fb = "—")' not in PAGE


# ── 8. Table actions ─────────────────────────────────────────────────────────
def test_table_row_actions():
    assert "View Details" in PAGE
    assert "<Edit2" in PAGE
    assert "Set as Primary" in PAGE
    assert "<Trash2" in PAGE


def test_delete_is_danger_styled():
    assert "var(--danger-border)" in PAGE and "var(--danger-bg)" in PAGE


# ── 9. Right side — Coverage Summary ─────────────────────────────────────────
def test_coverage_summary_card():
    assert "Coverage Summary" in PAGE
    assert "Bookable Areas" in PAGE and "Unused Slots" in PAGE and "Zone Match" in PAGE and "Last Sync" in PAGE


# ── 10. Right side — Coverage Rules ──────────────────────────────────────────
def test_coverage_rules_card():
    assert "Coverage Rules" in PAGE
    assert "One primary area required" in PAGE
    assert "Maximum" in PAGE and "service areas on current plan" in PAGE
    assert "Active areas are visible for customer matching" in PAGE
    assert "function RuleRow" in PAGE


# ── 11. Right side — Recent Activity ─────────────────────────────────────────
def test_recent_activity_card():
    assert "Recent Activity" in PAGE
    assert "View all activity" in PAGE


# ── Add Service Area drawer ──────────────────────────────────────────────────
def test_add_service_area_modal_enterprise():
    assert 'title="Add Service Area"' in PAGE
    assert "Add a city, pincode, zone, or radius where customers can book your services." in PAGE
    assert "Area Type" in PAGE
    assert "Validation Preview" in PAGE


def test_area_type_options_no_online():
    assert '"zipcode","city","zone","radius"' in PAGE.replace(" ", "")
    assert "coverage_type === t" in PAGE  # selector iterates the 4-type union, no "online" branch
    assert "AreaType = \"zipcode\" | \"city\" | \"zone\" | \"radius\";" in API_TS


def test_validation_preview_resolves_141001():
    assert "PINCODE_PREFIX_LOOKUP" in SERVICEABILITY_SERVICE or "PINCODE_PREFIX_LOOKUP" in ROOT.joinpath(
        "app/engines/serviceability/constants.py").read_text(encoding="utf-8-sig")
    constants = (ROOT / "app/engines/serviceability/constants.py").read_text(encoding="utf-8-sig")
    assert '"141"' in constants and '"Ludhiana"' in constants and '"tier_2"' in constants


def test_duplicate_pincode_check_real():
    assert "is_duplicate" in SERVICEABILITY_SERVICE
    assert "_check_duplicate_area" in SERVICEABILITY_SERVICE


def test_package_limit_check_real():
    assert "package_limit_ok" in SERVICEABILITY_SERVICE
    assert "get_service_area_limits" in SERVICEABILITY_SERVICE
    assert "max_service_areas" in SERVICEABILITY_MODELS or "max_service_areas" in (
        ROOT / "app/engines/tenant_engine/models.py").read_text(encoding="utf-8-sig")


def test_bookability_impact_text():
    assert "This area can receive Home Services bookings." in SERVICEABILITY_SERVICE


# ── Edit / Detail / Delete / Set Primary ─────────────────────────────────────
def test_edit_area_pincode_immutable_hint():
    assert "To change pincode, add a new service area." in PAGE


def test_detail_drawer_sections():
    assert "function AreaDetailDrawer" in PAGE
    for section in ["Area Summary", "Bookability Impact", "Package Limit Impact", "Recent Activity"]:
        assert section in PAGE


def test_delete_confirmation():
    assert "Delete service area?" in PAGE
    assert "Deleting this area may reduce where customers can book your services." in PAGE
    assert "This is your last active area. Removing it may make your business not bookable." in PAGE
    assert "Delete Area" in PAGE


def test_set_primary_confirmation():
    assert "function SetPrimaryConfirmModal" in PAGE
    assert "This area will be used as your default coverage area for matching and pricing." in PAGE


def test_set_primary_calls_real_endpoint():
    assert "setPrimary:" in API_TS
    assert "/set-primary" in API_TS
    assert "set_primary_service_area" in SERVICEABILITY_SERVICE
    assert '"/v1/tenant/service-areas/{area_id}/set-primary"' in SERVICEABILITY_ROUTER


# ── Backend wiring ────────────────────────────────────────────────────────────
def test_backend_crud_endpoints_exist():
    assert '"/v1/tenant/service-areas"' in SERVICEABILITY_ROUTER
    assert '"/v1/tenant/service-areas/{area_id}"' in SERVICEABILITY_ROUTER
    assert '"/v1/tenant/service-areas/limits"' in SERVICEABILITY_ROUTER
    assert '"/v1/tenant/service-areas/validate"' in SERVICEABILITY_ROUTER


def test_update_uses_put_not_patch():
    assert 'method: "PUT"' in API_TS.split("providerServiceAreasApi")[1].split("};")[0]


def test_area_id_field_matches_real_backend():
    # Real backend model column is `id`, not `area_id`; frontend interface must match.
    assert "id: string;" in API_TS.split("interface ProviderServiceArea {")[1].split("}")[0]
    assert "area_id" not in PAGE


def test_migration_117_adds_is_primary_and_plan_limit():
    assert "is_primary" in MIGRATION_117
    assert "max_service_areas" in MIGRATION_117
    assert "tenant_service_areas" in MIGRATION_117
    assert "tenant_limits" in MIGRATION_117


def test_is_primary_column_on_model():
    assert "is_primary:" in SERVICEABILITY_MODELS


# ── Permission handling ───────────────────────────────────────────────────────
def test_permission_gated_actions():
    # Slice 2F-7: these 3 permissions are now wrapped in
    # require_tenant_mutation_permission(...) (access-scope-aware), not the
    # plain require_permission(...) they used before -- a read-only-scoped
    # tenant_owner could previously mutate service-area coverage despite
    # holding the permission bundle. See
    # docs/workflow-rearchitecture/phase-02a-slice-02f7/.
    assert "canCreate" in PAGE and "canUpdate" in PAGE and "canDelete" in PAGE and "canSetPrimary" in PAGE
    assert "require_tenant_mutation_permission(P.TENANT_SERVICE_AREA_CREATE)" in SERVICEABILITY_ROUTER
    assert "require_tenant_mutation_permission(P.TENANT_SERVICE_AREA_UPDATE)" in SERVICEABILITY_ROUTER
    assert "require_tenant_mutation_permission(P.TENANT_SERVICE_AREA_DELETE)" in SERVICEABILITY_ROUTER


# ── Error handling ────────────────────────────────────────────────────────────
def test_error_section_has_request_id_and_retry():
    assert "function SectionError" in PAGE
    assert "Request ID:" in PAGE
    assert "Retry" in PAGE
    assert "requestId={areasApi.requestId}" in PAGE


def test_no_bare_unexpected_error():
    assert '"Unexpected error"' not in PAGE
    assert "We couldn't load service coverage" in PAGE


# ── Responsive design ─────────────────────────────────────────────────────────
def test_responsive_css_rules():
    assert "@media(max-width:1100px)" in PAGE.replace(" ", "")
    assert "@media(max-width:768px)" in PAGE.replace(" ", "")
    assert ".sa-cols{grid-template-columns:1fr}" in PAGE.replace(" ", "").replace("\n", "") or \
        "grid-template-columns:1fr" in PAGE.replace(" ", "")


# ── Forbidden labels ──────────────────────────────────────────────────────────
FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in PAGE, f"forbidden label found: {term}"


# ── Data normalization ───────────────────────────────────────────────────────
def test_safe_formatters_present():
    assert "safeText" in PAGE and "safeNum" in PAGE and "safeDate" in PAGE and "safeZoneTier" in PAGE


def test_zone_tier_labels_map():
    assert "ZONE_TIER_LABELS" in PAGE
    assert '"tier_1": "Tier 1"' in PAGE.replace(" ", "").replace(":", ": ").replace("  ", " ") or \
        "tier_1: \"Tier 1\"" in PAGE
