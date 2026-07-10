"""P0 Tenant Service Setup — Enterprise Wizard + Card Flow.

Static source-inspection tests (consistent with other page-redesign suites in
this repo) verifying the new `/provider/service-setup` page: breadcrumb,
readiness hero, catalog cards, 10-step wizard, enabled services table,
readiness issues panel, activity timeline — all wired to real backend APIs
discovered in prior sprints (provider offerings/brands/service-options/
service-areas/team-members/availability/pricing/status), not fictional
`/v1/tenant/services`-style endpoints, and no mock runtime data.
"""
import os

PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "tenant-portal", "app", "(tenant)", "provider", "service-setup", "page.tsx")
LAYOUT = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "tenant-portal", "components", "layout", "TenantLayout.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestFileExists:
    def test_page_exists(self):
        assert os.path.exists(PAGE)


class TestPageStructure:
    def test_breadcrumb_present(self):
        src = _read(PAGE)
        assert "Tenant Portal / Setup / Service Setup" in src

    def test_header_title_and_subtitle(self):
        src = _read(PAGE)
        assert "Service Setup" in src
        assert "Choose platform-approved services" in src

    def test_header_actions_present(self):
        src = _read(PAGE)
        for action in ["Add Service", "Refresh Catalog", "Validate Setup", "View Activity"]:
            assert action in src

    def test_readiness_hero_fields(self):
        src = _read(PAGE)
        for field in ["Enabled Services", "Bookable Services", "Setup Issues",
                      "Service Areas", "Technicians", "Pricing", "Availability"]:
            assert field in src

    def test_catalog_cards_section(self):
        src = _read(PAGE)
        assert "Service Catalog" in src
        assert "Enable Service" in src
        assert "Manage Setup" in src

    def test_enabled_services_table(self):
        src = _read(PAGE)
        assert "Enabled Services" in src
        for col in ["Service", "Types", "Brands", "Pricing", "Bookable", "Status", "Actions"]:
            assert f'"{col}"' in src

    def test_readiness_issues_panel(self):
        src = _read(PAGE)
        assert "Readiness Issues" in src

    def test_activity_timeline(self):
        src = _read(PAGE)
        assert "showActivity" in src
        assert "getAuditLog" in src


class TestWizard:
    def test_ten_wizard_steps_defined(self):
        src = _read(PAGE)
        for label in [
            "1. Service", "2. Type", "3. Brands", "4. Issues", "5. Options",
            "6. Service Areas", "7. Technician", "8. Pricing", "9. Availability", "10. Review",
        ]:
            assert label in src

    def test_service_step_is_readonly_catalog(self):
        src = _read(PAGE)
        assert "managed by the platform catalog" in src

    def test_type_step_uses_real_coverage_api(self):
        src = _read(PAGE)
        assert "offeringCoverageApi.getTypes" in src

    def test_brand_step_uses_real_brand_api(self):
        src = _read(PAGE)
        assert "providerBrandApi.getAvailableForService" in src

    def test_issues_step_uses_real_diagnostics_api(self):
        src = _read(PAGE)
        assert "customerServiceDiagnosticsApi.getIssueTypes" in src

    def test_options_step_uses_real_service_option_api(self):
        src = _read(PAGE)
        assert "providerServiceOptionApi.getAvailableForService" in src

    def test_service_area_step_uses_real_api(self):
        src = _read(PAGE)
        assert "providerServiceAreasApi.list" in src

    def test_technician_step_uses_real_team_api(self):
        src = _read(PAGE)
        assert "providerTeamMembersApi.list" in src

    def test_pricing_step_uses_backend_resolver(self):
        src = _read(PAGE)
        assert "offeringPricingApi.preview" in src
        assert "cannot set an authoritative price" in src

    def test_availability_step_uses_real_api(self):
        src = _read(PAGE)
        assert "providerAvailabilityApi.list" in src

    def test_review_checklist_items(self):
        src = _read(PAGE)
        for item in ["Service selected", "Type selected", "Brand selected",
                     "Service area linked", "Technician assigned", "Availability ready"]:
            assert item in src

    def test_enable_blocked_when_not_ready(self):
        src = _read(PAGE)
        assert "disabled={!readyToEnable}" in src

    def test_save_draft_action_exists(self):
        src = _read(PAGE)
        assert "Save Draft" in src
        assert "handleSave(false)" in src

    def test_enable_uses_real_offerings_api(self):
        src = _read(PAGE)
        assert "providerOfferingsApi.enable" in src
        assert "providerOfferingsApi.update" in src
        assert "providerOfferingsApi.activate" in src


class TestErrorHandling:
    def test_section_error_shows_request_id(self):
        src = _read(PAGE)
        assert "SectionError" in src
        assert "Request ID:" in src
        assert "Copy Request ID" in src

    def test_no_generic_unexpected_error_only(self):
        src = _read(PAGE)
        assert "We couldn't load" in src


class TestNoForbiddenLabels:
    def test_no_forbidden_home_services_labels(self):
        src = _read(PAGE)
        forbidden = [
            "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
            "Tenant Payout", "Provider Earnings Wallet", "Escrow",
            "Platform Collected Service Payment", "Provider Cash Balance",
        ]
        for label in forbidden:
            assert label not in src, f"Forbidden label found: {label}"

    def test_customer_pays_provider_directly_language_used(self):
        src = _read(PAGE)
        assert "Customer pays the provider directly" in src


class TestNoMockData:
    def test_no_hardcoded_sample_catalog_arrays(self):
        src = _read(PAGE)
        # The wizard must not hardcode fictional catalog data like "LG", "Samsung", "Split AC"
        # as literal arrays — all such values must come from API responses.
        assert "const BRANDS = [" not in src
        assert "const SERVICE_TYPES = [" not in src

    def test_uses_use_api_hook_not_static_state(self):
        src = _read(PAGE)
        assert src.count("useApi(useCallback(") >= 8


class TestNavIntegration:
    def test_nav_points_to_service_setup(self):
        # HS0 cleanup: the active Setup nav item now points at the
        # canonical /tenant/setup/services wizard; /provider/service-setup
        # is the superseded duplicate and only remains reachable directly
        # (with a "moved" banner), not as a live nav destination.
        src = _read(LAYOUT)
        assert '"/tenant/setup/services"' in src
        assert "tenant-setup-services" in src
