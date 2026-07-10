"""Admin Home Services Catalog Setup Console certification.

Static-inspection style (established convention this session). Almost the
entire data layer already existed and was real — master services, service
types, brands, pricing rules, issue types, service options, pricing tiers
all had complete admin CRUD. This sprint's real work: (1) a new
`compute_symmetric_customer_price_tiers` pure function (bargain_engine.py)
implementing the ticket's exact Low/Mid/High formula — distinct from the
existing asymmetric compute_price_tiers used by the certified
provider-first-matching flow, which this sprint does not touch; (2) new
type-scoped and brand-scoped admin floor/ceiling upsert methods reusing the
existing ServicePricingRule table; (3) migration 118 adding
can_override_price/is_routing_only to master_service_brands; (4) a new
consolidated console router composing all of the above into one
Home-Services-scoped admin surface.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/super-admin"

PAGE = (FRONTEND / "app/admin/home-services/service-catalog/page.tsx").read_text(encoding="utf-8-sig")
LAYOUT = (FRONTEND / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
BARGAIN_ENGINE = (ROOT / "app/engines/admin_catalog/bargain_engine.py").read_text(encoding="utf-8-sig")
CONSOLE_ROUTER = (ROOT / "app/engines/admin_catalog/home_services_catalog_console_router.py").read_text(encoding="utf-8-sig")
SERVICE_PY = (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8-sig")
MIGRATION_118 = (ROOT / "alembic/versions/118_home_services_catalog_console_brand_behavior.py").read_text(encoding="utf-8-sig")
MAIN_PY = (ROOT / "app/main.py").read_text(encoding="utf-8-sig")


# ── 1. Route / navigation ────────────────────────────────────────────────────
def test_route_exists():
    assert (FRONTEND / "app/admin/home-services/service-catalog/page.tsx").exists()


def test_nav_has_service_catalog_and_overview():
    assert '"hs-service-catalog"' in LAYOUT
    assert 'label: "Service Catalog"' in LAYOUT
    assert 'label: "Overview"' in LAYOUT
    assert '"Bargain Rules"' not in LAYOUT.split('label: "Home Services"')[1].split("],")[0]


# ── 2. Page structure ────────────────────────────────────────────────────────
# HS2 cleanup: title/subtitle updated to the ticket's exact required copy;
# pricing-configuration language removed from the subtitle since HS2 is
# catalog-only (pricing moved to Pricing Rules — see HS2 scope tests below).
def test_title_and_subtitle():
    assert "Home Services Catalog" in PAGE
    assert "Manage platform-approved Home Services, service types, brands, customer questions, options, and provider setup rules." in PAGE


def test_top_actions():
    assert "Add Service" in PAGE and "Refresh" in PAGE


def test_left_service_list_grouped():
    assert "function ServiceRow" in PAGE
    assert "grouped.map" in PAGE


def test_service_row_fields():
    assert "types_count" in PAGE and "brands_count" in PAGE


# ── 3. Tabs ───────────────────────────────────────────────────────────────────
# HS2 cleanup: tabs renamed to match the ticket's catalog-only tab list;
# the standalone "Zones / Tiers" pricing tab was removed (tier-scoped
# pricing belongs to Pricing Rules, not the catalog console).
def test_all_tabs_present():
    for label in ["General", "Types", "Brands", "Questions / Issues", "Options / Add-ons",
                  "Customer Preview", "Activity"]:
        assert label in PAGE


# ── 4. General tab ────────────────────────────────────────────────────────────
def test_general_tab_fields():
    assert "function GeneralTab" in PAGE
    for label in ["Service Name", "Pricing Model", "Category", "Status", "Sort Order"]:
        assert label in PAGE
    assert "Tenants can only select this service from the admin-approved catalog" in PAGE


# ── 5. Types tab (HS2: catalog-only, no pricing) ─────────────────────────────
def test_types_pricing_tab_columns():
    # HS2 cleanup: Floor/Ceiling/Platform Fee/Deduction pricing columns were
    # removed from the catalog Types tab (moved to Pricing Rules) — replaced
    # with catalog-scope columns (visibility/selectability/status).
    assert "function TypesTab" in PAGE
    for col in ["Customer Visible", "Provider Selectable", "Status"]:
        assert col in PAGE
    assert "Pricing is configured in Pricing Rules." in PAGE


def test_types_tab_has_no_pricing_form():
    types_fn = PAGE.split("function TypesTab")[1].split("function BrandsTab")[0]
    assert "Floor" not in types_fn and "Ceiling" not in types_fn and "Platform Fee" not in types_fn


# The backend upsert_home_services_type_limits method itself is out of HS2
# scope (pricing logic, certified separately) — no longer asserted from
# this catalog-UI test file.


# ── 6. Brands tab (HS2: catalog-only, no pricing) ────────────────────────────
def test_brands_tab_behavior_controls():
    # HS2 cleanup: "Set Override Limits" (floor/ceiling entry form) removed
    # from the catalog Brands tab — brand price-override *eligibility* is
    # still shown (can_override_price/routing-only), the actual price range
    # is configured in Pricing Rules.
    assert "function BrandsTab" in PAGE
    assert "Price override allowed later" in PAGE or "Routing-only" in PAGE
    assert "Set Override Limits" not in PAGE
    assert "Pricing is configured in Pricing Rules." in PAGE


# ── 7. Issues, Options — real reads + link-out ────────────────────────────────
def test_issues_tab_real_and_links_out():
    assert "function IssuesTab" in PAGE
    assert "masterDataApi.listIssueTypes" in PAGE
    assert "master_service_id: serviceId" in PAGE
    assert "/admin/service-setup/issue-types" in PAGE


def test_options_tab_real_and_links_out():
    assert "function OptionsTab" in PAGE
    assert "masterDataApi.listServiceOptions" in PAGE
    assert "/admin/service-options" in PAGE


# ── 8. Customer Preview (HS2: catalog experience only, no pricing) ──────────
def test_preview_tab_inputs_and_output():
    # HS2 cleanup: the pricing-calculator preview (provider min/max/fee
    # inputs producing a Low/Mid/High result) was removed — Customer
    # Preview now shows only the catalog experience (service info, type
    # selector, brand question), never a computed price.
    assert "function PreviewTab" in PAGE
    assert "Type selector" in PAGE
    assert "Provider Min" not in PAGE and "Platform Fee %" not in PAGE
    assert "Pricing is configured in Pricing Rules." in PAGE


def test_symmetric_formula_matches_ticket_example():
    """₹550-₹700 @ 10% platform fee → Low ₹605, Mid ₹690, High ₹770."""
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r = compute_symmetric_customer_price_tiers(550, 700, 10)
    assert r["low_price"] == 605.0
    assert r["mid_price"] == 690.0
    assert r["high_price"] == 770.0


def test_never_shows_raw_provider_min_as_customer_low():
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r = compute_symmetric_customer_price_tiers(550, 700, 10)
    assert r["low_price"] != 550.0


# ── 9. Manual bargain disabled / forbidden labels ────────────────────────────
def test_no_manual_bargain_builder_ui():
    assert "Bargain Rule Builder" not in PAGE
    assert "Manual Bargain Setup" not in PAGE.replace("Manual bargain setup is disabled", "")


FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in PAGE, f"forbidden label found: {term}"


# ── HS2B — Blocker fixes ──────────────────────────────────────────────────────
def test_hs2b_provider_setup_rules_tab_present():
    assert "function ProviderSetupRulesTab" in PAGE
    assert '{ key: "provider", label: "Provider Setup Rules" }' in PAGE


def test_hs2b_provider_setup_rules_no_pricing_fields():
    fn = PAGE.split("function ProviderSetupRulesTab")[1].split("function PricingRulesLink")[0]
    for forbidden in ["Floor", "Ceiling", "Platform Fee", "Low", "Mid", "High", "admin_floor", "admin_ceiling"]:
        assert forbidden not in fn


def test_hs2b_permission_aware_ui():
    assert "usePermissions" in PAGE
    assert 'canCreate = perm.has("catalog:services:write")' in PAGE
    assert "canRead" in PAGE and "canAudit" in PAGE


def test_hs2b_no_read_permission_blocks_page():
    assert "You don't have access to the Home Services Catalog" in PAGE


def test_hs2b_add_service_group_gated_by_create_permission():
    assert "Add Service Group" in PAGE
    block = PAGE.split("Add Service Group")[0][-400:]
    assert "canCreate &&" in block


def test_hs2b_activity_tab_gated_by_audit_permission():
    assert 'canAudit && <ActivityTab' in PAGE
    assert 't.key !== "activity" || canAudit' in PAGE


def test_hs2b_catalog_health_cards_present():
    assert "function CatalogHealthCards" in PAGE
    for label in ["Total Services", "Active Services", "Customer Visible Services",
                  "Provider Selectable Services", "Services Missing Types",
                  "Services Missing Questions", "Services Missing Brands", "Inactive Services"]:
        assert label in PAGE


def test_hs2b_service_group_crud_linked():
    # Full Service Group CRUD (create/edit/activate/deactivate/delete-with-
    # usage-check) already exists as a real, complete backend + a dedicated
    # enterprise frontend page (/admin/service-groups) — HS2B links to it
    # rather than duplicating full CRUD inline, matching the established
    # link-out pattern already used for Issues/Options/Pricing Rules.
    assert "/admin/service-groups" in PAGE


def test_hs2b_hard_delete_service_type_checks_usage():
    # HS2B delete-safety fix: hard_delete_service_type previously deleted
    # unconditionally even if a tenant had enabled the type or an admin
    # pricing rule referenced it — real gap, fixed this sprint.
    fn = SERVICE_PY.split("async def hard_delete_service_type")[1].split("def _type_dict")[0]
    assert "SERVICE_TYPE_IN_USE" in fn
    assert "ServicePricingRule" in fn
    assert "TenantServiceType" in fn


def test_hs2b_delete_service_group_already_checks_usage():
    fn = SERVICE_PY.split("async def delete_service_group")[1].split("async def _load_service_group")[0]
    assert "SERVICE_GROUP_HAS_SERVICES" in fn


def test_hs2b_hard_delete_master_service_already_checks_usage():
    fn = SERVICE_PY.split("async def hard_delete_master_service")[1].split("async def _load_master_service")[0]
    assert "MASTER_SERVICE_HAS_RULES" in fn


def test_hs2b_still_no_pricing_forms():
    # Regression guard (again, explicitly): the HS2B additions must not
    # reintroduce any pricing form.
    for forbidden in ["Admin Floor Price", "Admin Ceiling Price", "Platform Fee %",
                       "Completed Job Deduction", "Set Override Limits"]:
        assert forbidden not in PAGE
    assert "function ZonesTab" not in PAGE
    assert "Low {safeCurrency" not in PAGE


# ── 10. Home Services scope guard ────────────────────────────────────────────
def test_scope_guard_message():
    assert "only available for Home Services" in PAGE
    assert "Other verticals use their own setup model." in PAGE


def test_backend_scope_hard_boundary():
    assert "async def get_home_services_category_id" in SERVICE_PY
    assert 'vertical_type == "home_services"' in SERVICE_PY
    assert "NOT_HOME_SERVICES_CATEGORY" in SERVICE_PY


# ── 11. API integration ──────────────────────────────────────────────────────
def test_backend_routes_registered():
    assert 'prefix="/v1/admin/home-services/service-catalog"' in CONSOLE_ROUTER
    for path in ['"/services"', '"/services/{service_id}"', '"/services/{service_id}/types"',
                 '"/services/{service_id}/types/{service_type_id}/limits"',
                 '"/services/{service_id}/brands"', '"/services/{service_id}/brands/{mapping_id}/behavior"',
                 '"/services/{service_id}/brands/{brand_id}/limits"',
                 '"/price-preview"', '"/services/{service_id}/audit"']:
        assert path in CONSOLE_ROUTER


def test_router_registered_in_main():
    assert "home_services_catalog_console_router" in MAIN_PY


def test_migration_118_adds_brand_behavior_columns():
    assert "can_override_price" in MIGRATION_118
    assert "is_routing_only" in MIGRATION_118
    assert "master_service_brands" in MIGRATION_118


# ── 12. Permission handling ───────────────────────────────────────────────────
def test_read_endpoints_permission_gated():
    assert "require_permission(P.CATALOG_PRICING_READ)" in CONSOLE_ROUTER


def test_write_endpoints_permission_gated():
    assert "require_permission(P.CATALOG_PRICING_WRITE)" in CONSOLE_ROUTER


# ── 13. Error handling ────────────────────────────────────────────────────────
def test_error_section_has_request_id_and_retry():
    assert "function SectionError" in PAGE
    assert "Request ID:" in PAGE
    assert "Retry" in PAGE


def test_no_bare_unexpected_error():
    assert '"Unexpected error"' not in PAGE


# ── 14. Data normalization ────────────────────────────────────────────────────
def test_safe_formatters_present():
    assert "safeText" in PAGE and "safeNum" in PAGE and "safeCurrency" in PAGE and "safePercent" in PAGE and "safeDate" in PAGE
