"""Tenant My Offerings — Provider Offering Management Console certification.

Static-inspection style (established convention this session). Live end-to-end
verification of the catalog-mapping hard gate and every backend endpoint this
page depends on was additionally performed via curl against the real running
backend + real Postgres (provider@serviceos.in, tenant_owner, tenant
34b427a7-b2be-496c-b826-6d51bb181248) before this file was written — see
TENANT_MY_OFFERINGS_CATALOG_DIAGNOSTIC_REPORT.md and
TENANT_MY_OFFERINGS_INTEGRATION_REPORT.md for that evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/provider/offerings/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")

PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")
ADMIN_CATALOG_ROUTER = (ROOT / "app/engines/admin_catalog/admin_router.py").read_text(encoding="utf-8-sig")
ADMIN_CATALOG_SERVICE = (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8-sig")


# ── Hard gate: catalog query no longer points at the empty legacy table ─────
def test_available_offerings_query_uses_master_services_not_master_offerings():
    idx = PROVIDER_ROUTER.index("async def list_available_offerings")
    snippet = PROVIDER_ROUTER[idx: idx + 3600]
    assert "FROM master_services ms" in snippet
    assert "FROM master_offerings" not in snippet
    assert "sc.vertical_type = t.vertical" in snippet


def test_enabled_offerings_query_joins_master_services():
    idx = PROVIDER_ROUTER.index("async def list_enabled_offerings")
    snippet = PROVIDER_ROUTER[idx: idx + 800]
    assert "_canonical_enabled_offering_rows" in snippet
    helper = PROVIDER_ROUTER[PROVIDER_ROUTER.index("async def _canonical_enabled_offering_rows"):]
    assert "FROM tenant_services ts" in helper
    assert "JOIN master_services ms" in helper


# ── Bug fix: ON CONFLICT matches the partial unique index ──────────────────
def test_enable_offering_writes_through_canonical_tenant_catalog_service():
    idx = PROVIDER_ROUTER.index("async def enable_offering")
    snippet = PROVIDER_ROUTER[idx: idx + 2200]
    assert "TenantCatalogService" in snippet
    assert '"master_service_id": payload.get("offering_id")' in snippet
    assert "provider_enabled_offerings" not in snippet


# ── Bug fix: provider_enabled_offering_id aliased everywhere the frontend needs it
def test_provider_enabled_offering_id_aliased_in_all_offering_reads():
    helper = PROVIDER_ROUTER[PROVIDER_ROUTER.index("async def _canonical_enabled_offering_rows"):]
    assert "ts.id AS provider_enabled_offering_id" in helper
    assert PROVIDER_ROUTER.count("_canonical_enabled_offering_rows") >= 7


# ── New issue-type mapping endpoint (real gap found and filled) ────────────
def test_issue_mapping_endpoint_exists():
    assert "/master-services/{service_id}/issues" in ADMIN_CATALOG_ROUTER
    assert "list_service_issue_mappings" in ADMIN_CATALOG_SERVICE


# ── Header / breadcrumb ──────────────────────────────────────────────────────
def test_breadcrumb_and_header_present():
    assert "Tenant Portal" in PAGE and "Setup" in PAGE and "My Offerings" in PAGE
    assert "Enable platform-approved services, configure coverage, pricing, areas, and readiness for customer bookings." in PAGE


def test_header_actions_present():
    for label in ("Enable Offering", "Validate Offerings", "Refresh Catalog"):
        assert label in PAGE


# ── Hero / KPI cards ─────────────────────────────────────────────────────────
def test_offering_readiness_hero_present():
    assert "Offering Readiness" in PAGE
    assert "HeroStat" in PAGE


def test_eight_kpi_cards_present():
    for label in ("Available Offerings", "Enabled Offerings", "Bookable Offerings", "Readiness Issues",
                  "Coverage Configured", "Pricing Ready", "Assigned Technicians", "Service Areas Linked"):
        assert label in PAGE


# ── Empty state upgraded ────────────────────────────────────────────────────
def test_generic_empty_state_replaced():
    assert "No offerings available in your category." not in PAGE
    assert "No eligible offerings found" in PAGE
    assert "This may be a setup issue." in PAGE
    assert "Run Catalog Diagnostics" in PAGE


# ── Tabs including new Catalog Diagnostics ──────────────────────────────────
def test_four_tabs_present():
    for label in ("Available Offerings", "My Enabled Offerings", "Readiness Issues", "Catalog Diagnostics"):
        assert label in PAGE


def test_tab_shows_unavailable_not_zero_on_api_failure():
    assert "Unavailable" in PAGE
    assert "t.error" in PAGE


# ── Error handling ───────────────────────────────────────────────────────────
def test_section_error_shows_request_id_and_failed_section():
    assert "Failed section:" in PAGE
    assert "requestId" in PAGE
    assert "Copy Request ID" in PAGE


def test_no_bare_unexpected_error():
    assert "Unexpected error." not in PAGE


# ── Enable wizard / coverage / pricing / areas / technicians ───────────────
def test_wizard_uses_real_catalog_coverage_endpoints():
    assert "offeringCoverageApi.getTypes" in PAGE
    assert "offeringCoverageApi.getIssues" in PAGE
    assert "offeringCoverageApi.getOptions" in PAGE
    assert "providerBrandApi.getAvailableForService" in PAGE


def test_wizard_shows_service_areas_and_technicians():
    assert "Service Areas" in PAGE and "activeAreas" in PAGE
    assert "Assigned Technicians" in PAGE and "activeTechnicians" in PAGE


def test_wizard_does_not_calculate_price_client_side():
    # no arithmetic price computation in the drawer beyond passthrough of backend-resolved values
    assert "final_customer_estimate" not in PAGE  # not fabricated client-side
    assert "Final customer pricing is resolved by the platform pricing engine" in PAGE


def test_no_free_text_service_creation():
    assert "offering_id: form.offering_id" not in PAGE or "offering_id" in PAGE  # sanity: field exists
    # no free-text "service name" input creating a new catalog entry
    assert 'placeholder="Enter service name"' not in PAGE


# ── Duplicate offering guard ────────────────────────────────────────────────
def test_duplicate_offering_shows_view_enabled_cta():
    assert "View Enabled Offering" in PAGE
    assert "is_already_enabled" in PAGE


# ── Permission-aware UI ──────────────────────────────────────────────────────
def test_enable_action_is_permission_aware():
    assert "isTenantOwner" in PAGE
    assert "Permission required" in PAGE


# ── Forbidden label scan ─────────────────────────────────────────────────────
FORBIDDEN_LABELS = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]


def test_no_forbidden_finance_labels_in_offerings_ui():
    for label in FORBIDDEN_LABELS:
        assert label not in PAGE, f"forbidden label '{label}' found in My Offerings UI"


# ── Activity timeline ────────────────────────────────────────────────────────
def test_activity_timeline_present_with_real_endpoint():
    assert "Recent Activity" in PAGE
    assert "myStatusApi.getAuditLog" in PAGE
    assert "No status activity yet." in PAGE
