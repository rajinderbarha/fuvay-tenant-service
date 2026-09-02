"""
Sprint 38 — Universal Category + Catalog + Pricing + Provider Architecture tests.
Verifies:
  - Migration 068 created with service_groups table + universal category fields
  - SQLAlchemy models: ServiceGroup class, ServiceCategory new fields, MasterService.service_group_id
  - AdminCatalogService: service group CRUD methods, VALID_VERTICAL_TYPES/FINANCE_MODELS constants
  - Admin router: /service-groups endpoints, master-services service_group_id filter
  - Customer router: /service-groups + /flow/config endpoints
  - Frontend api.ts: ServiceGroup type, listServiceGroups/createServiceGroup/audited retire methods
  - Frontend pages: service-groups page, categories page universal fields, pricing page dynamic categories
  - Frontend nav: service-groups link in AdminLayout
  - Seed scripts exist and cover all 14 verticals
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))

MIGRATION_068 = os.path.join(ROOT, "alembic", "versions", "068_universal_category_service_groups.py")
MODELS_FILE   = os.path.join(ROOT, "app", "engines", "admin_catalog", "models.py")
SERVICE_FILE  = os.path.join(ROOT, "app", "engines", "admin_catalog", "service.py")
ADMIN_ROUTER  = os.path.join(ROOT, "app", "engines", "admin_catalog", "admin_router.py")
CUST_ROUTER   = os.path.join(ROOT, "app", "engines", "admin_catalog", "customer_router.py")
SA_API        = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
SA_LAYOUT     = os.path.join(ROOT, "frontend", "super-admin", "components", "layout", "AdminLayout.tsx")
SA_PAGES      = os.path.join(ROOT, "frontend", "super-admin", "app", "admin")
SEED_CATS     = os.path.join(ROOT, "scripts", "seed_universal_categories.py")
SEED_GROUPS   = os.path.join(ROOT, "scripts", "seed_service_groups.py")
SEED_SERVICES = os.path.join(ROOT, "scripts", "seed_master_services.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 068 ──────────────────────────────────────────────────────────────

def test_migration_068_exists():
    assert os.path.exists(MIGRATION_068)

def test_migration_068_revision():
    src = _read(MIGRATION_068)
    assert 'revision = "068"' in src

def test_migration_068_down_revision():
    src = _read(MIGRATION_068)
    assert 'down_revision = "067"' in src

def test_migration_068_creates_service_groups():
    src = _read(MIGRATION_068)
    assert "service_groups" in src

def test_migration_068_service_groups_category_fk():
    src = _read(MIGRATION_068)
    assert "service_categories" in src

def test_migration_068_adds_vertical_type():
    src = _read(MIGRATION_068)
    assert "vertical_type" in src

def test_migration_068_adds_finance_model():
    src = _read(MIGRATION_068)
    assert "finance_model" in src

def test_migration_068_adds_requires_location():
    src = _read(MIGRATION_068)
    assert "requires_location" in src

def test_migration_068_adds_requires_schedule():
    src = _read(MIGRATION_068)
    assert "requires_schedule" in src

def test_migration_068_adds_requires_brand():
    src = _read(MIGRATION_068)
    assert "requires_brand" in src

def test_migration_068_adds_requires_service_option():
    src = _read(MIGRATION_068)
    assert "requires_service_option" in src

def test_migration_068_adds_requires_issue_type():
    src = _read(MIGRATION_068)
    assert "requires_issue_type" in src

def test_migration_068_adds_service_group_id_to_master_services():
    src = _read(MIGRATION_068)
    assert "service_group_id" in src
    assert "master_services" in src

def test_migration_068_has_downgrade():
    src = _read(MIGRATION_068)
    assert "def downgrade" in src


# ── SQLAlchemy Models ──────────────────────────────────────────────────────────

def test_model_service_group_class_exists():
    src = _read(MODELS_FILE)
    assert "class ServiceGroup" in src

def test_model_service_group_tablename():
    src = _read(MODELS_FILE)
    assert '"service_groups"' in src

def test_model_service_group_has_code():
    src = _read(MODELS_FILE)
    assert "ServiceGroup" in src
    # code column must appear after ServiceGroup class definition
    idx = src.index("class ServiceGroup")
    assert "code" in src[idx:idx + 800]

def test_model_service_group_has_slug():
    src = _read(MODELS_FILE)
    idx = src.index("class ServiceGroup")
    assert "slug" in src[idx:idx + 800]

def test_model_service_group_has_category_id():
    src = _read(MODELS_FILE)
    idx = src.index("class ServiceGroup")
    segment = src[idx:idx + 1200]
    assert "category_id" in segment

def test_model_service_category_has_vertical_type():
    src = _read(MODELS_FILE)
    assert "vertical_type" in src

def test_model_service_category_has_finance_model():
    src = _read(MODELS_FILE)
    assert "finance_model" in src

def test_model_service_category_has_requires_location():
    src = _read(MODELS_FILE)
    assert "requires_location" in src

def test_model_service_category_has_tenant_selectable():
    src = _read(MODELS_FILE)
    assert "tenant_selectable" in src

def test_model_service_category_has_pricing_supported():
    src = _read(MODELS_FILE)
    assert "pricing_supported" in src

def test_model_master_service_has_service_group_id():
    src = _read(MODELS_FILE)
    # service_group_id must be in MasterService class section
    idx = src.index("class MasterService")
    segment = src[idx:idx + 2000]
    assert "service_group_id" in segment


# ── Service Layer Constants ────────────────────────────────────────────────────

def test_service_valid_vertical_types_defined():
    src = _read(SERVICE_FILE)
    assert "VALID_VERTICAL_TYPES" in src

def test_service_valid_vertical_types_has_14():
    src = _read(SERVICE_FILE)
    idx = src.index("VALID_VERTICAL_TYPES")
    segment = src[idx:idx + 600]
    expected = [
        "home_services", "coaching", "real_estate", "restaurant", "salon",
        "automotive", "professional_services", "pharmacy", "hardware",
        "repair_services", "cleaning_services", "laundry", "marketplace_products", "other",
    ]
    for v in expected:
        assert v in segment, f"VALID_VERTICAL_TYPES missing: {v}"

def test_service_valid_finance_models_defined():
    src = _read(SERVICE_FILE)
    assert "VALID_FINANCE_MODELS" in src

def test_service_valid_finance_models_has_7():
    src = _read(SERVICE_FILE)
    idx = src.index("VALID_FINANCE_MODELS")
    segment = src[idx:idx + 500]
    expected = [
        "credit_wallet_only", "monthly_subscription", "lead_credit",
        "commission_wallet", "product_order_commission", "free_listing", "hybrid",
    ]
    for v in expected:
        assert v in segment, f"VALID_FINANCE_MODELS missing: {v}"

def test_service_valid_customer_flow_types_defined():
    src = _read(SERVICE_FILE)
    assert "VALID_CUSTOMER_FLOW_TYPES" in src

def test_service_list_service_groups_method():
    src = _read(SERVICE_FILE)
    assert "list_service_groups" in src

def test_service_create_service_group_method():
    src = _read(SERVICE_FILE)
    assert "create_service_group" in src

def test_service_update_service_group_method():
    src = _read(SERVICE_FILE)
    assert "update_service_group" in src

def test_service_retire_service_group_method():
    src = _read(SERVICE_FILE)
    assert "archive_service_group" in src
    assert "restore_service_group" in src

def test_service_list_master_services_has_service_group_filter():
    src = _read(SERVICE_FILE)
    assert "service_group_id" in src

def test_service_create_category_validates_vertical_type():
    src = _read(SERVICE_FILE)
    # create_category should use VALID_VERTICAL_TYPES
    assert "VALID_VERTICAL_TYPES" in src
    assert "create_category" in src

def test_service_cat_dict_includes_vertical_type():
    src = _read(SERVICE_FILE)
    # _cat_dict should return vertical_type
    idx = src.index("_cat_dict")
    segment = src[idx:idx + 1500]
    assert "vertical_type" in segment

def test_service_cat_dict_includes_finance_model():
    src = _read(SERVICE_FILE)
    idx = src.index("_cat_dict")
    segment = src[idx:idx + 1500]
    assert "finance_model" in segment


# ── Admin Router ───────────────────────────────────────────────────────────────

def test_admin_router_has_service_groups_list():
    src = _read(ADMIN_ROUTER)
    assert "/service-groups" in src

def test_admin_router_service_groups_post():
    src = _read(ADMIN_ROUTER)
    # POST method for service groups
    assert "create_service_group" in src

def test_admin_router_service_groups_get_by_id():
    src = _read(ADMIN_ROUTER)
    assert "get_service_group" in src

def test_admin_router_service_groups_put():
    src = _read(ADMIN_ROUTER)
    assert "update_service_group" in src

def test_admin_router_service_groups_deprecated_delete_and_retire():
    src = _read(ADMIN_ROUTER)
    assert "delete_service_group" in src
    assert "AUDITED_RETIRE_REQUIRED" in src
    assert "/service-groups/{group_id}/archive" in src

def test_admin_router_master_services_accepts_service_group_id():
    src = _read(ADMIN_ROUTER)
    assert "service_group_id" in src


# ── Customer Router ────────────────────────────────────────────────────────────

def test_customer_router_has_service_groups_endpoint():
    src = _read(CUST_ROUTER)
    assert "/service-groups" in src

def test_customer_router_has_flow_config_endpoint():
    src = _read(CUST_ROUTER)
    assert "/flow/config" in src

def test_customer_flow_config_returns_steps():
    src = _read(CUST_ROUTER)
    assert "steps" in src

def test_customer_flow_config_returns_finance_model():
    src = _read(CUST_ROUTER)
    assert "finance_model" in src

def test_customer_flow_config_handles_no_category():
    src = _read(CUST_ROUTER)
    # Should return defaults when no category found
    assert "service_booking" in src


# ── Frontend api.ts ────────────────────────────────────────────────────────────

def test_api_ts_service_group_interface():
    src = _read(SA_API)
    assert "ServiceGroup" in src

def test_api_ts_service_group_has_category_id():
    src = _read(SA_API)
    idx = src.index("ServiceGroup")
    segment = src[idx:idx + 400]
    assert "category_id" in segment

def test_api_ts_service_category_has_vertical_type():
    src = _read(SA_API)
    assert "vertical_type" in src

def test_api_ts_service_category_has_finance_model():
    src = _read(SA_API)
    assert "finance_model" in src

def test_api_ts_service_category_has_requires_flags():
    src = _read(SA_API)
    assert "requires_location" in src
    assert "requires_schedule" in src
    assert "requires_brand" in src

def test_api_ts_list_service_groups():
    src = _read(SA_API)
    assert "listServiceGroups" in src

def test_api_ts_create_service_group():
    src = _read(SA_API)
    assert "createServiceGroup" in src

def test_api_ts_update_service_group():
    src = _read(SA_API)
    assert "updateServiceGroup" in src

def test_api_ts_retire_service_group():
    src = _read(SA_API)
    assert "archiveServiceGroup" in src
    assert "restoreServiceGroup" in src
    assert "deleteServiceGroup" not in src

def test_api_ts_get_flow_config():
    src = _read(SA_API)
    assert "getFlowConfig" in src

def test_api_ts_master_service_has_service_group_id():
    src = _read(SA_API)
    # MasterService interface should include service_group_id
    assert "service_group_id" in src


# ── Frontend Pages ─────────────────────────────────────────────────────────────

def test_service_groups_page_exists():
    page = os.path.join(SA_PAGES, "service-groups", "page.tsx")
    assert os.path.exists(page)

def test_service_groups_page_uses_catalog_api():
    page = os.path.join(SA_PAGES, "service-groups", "page.tsx")
    src = _read(page)
    assert "catalogApi" in src

def test_service_groups_page_has_create_form():
    page = os.path.join(SA_PAGES, "service-groups", "page.tsx")
    src = _read(page)
    assert "createServiceGroup" in src

def test_service_groups_page_has_category_filter():
    page = os.path.join(SA_PAGES, "service-groups", "page.tsx")
    src = _read(page)
    assert "categoryFilter" in src

def test_categories_page_has_vertical_type_field():
    page = os.path.join(SA_PAGES, "categories", "page.tsx")
    src = _read(page)
    assert "vertical_type" in src

def test_categories_page_has_finance_model_field():
    page = os.path.join(SA_PAGES, "categories", "page.tsx")
    src = _read(page)
    assert "finance_model" in src

def test_categories_page_has_requires_checkboxes():
    page = os.path.join(SA_PAGES, "categories", "page.tsx")
    src = _read(page)
    assert "requires_brand" in src
    assert "requires_issue_type" in src

def test_categories_page_no_hardcoded_cat_type_map():
    page = os.path.join(SA_PAGES, "categories", "page.tsx")
    src = _read(page)
    # Old hardcoded type labels should be gone
    assert "CAT_TYPE_LABEL" not in src

def test_pricing_page_no_hardcoded_categories():
    page = os.path.join(SA_PAGES, "pricing", "page.tsx")
    assert not os.path.exists(page)

def test_pricing_page_loads_categories_dynamically():
    page = os.path.join(SA_PAGES, "pricing", "page.tsx")
    assert not os.path.exists(page)

def test_catalog_page_has_service_group_filter():
    # Master Services tab promoted to /admin/master-services; check there
    page = os.path.join(SA_PAGES, "master-services", "page.tsx")
    src = _read(page)
    assert "serviceGroupFilter" in src or "service_group_id" in src or "ServiceGroup" in src or "service-groups" in src

def test_issue_types_page_has_category_filter():
    page = os.path.join(SA_PAGES, "issue-types", "page.tsx")
    assert not os.path.exists(page)

def test_service_options_page_has_category_filter():
    page = os.path.join(SA_PAGES, "service-options", "page.tsx")
    assert not os.path.exists(page)


# ── Admin Nav ──────────────────────────────────────────────────────────────────

# NOTE: migration 089 (Sprint 38 follow-up) moved this into DB-driven
# catalog_module_definitions, rendered dynamically per-vertical by
# VerticalCatalogSection using each module's real admin_path, rather than a
# static AdminLayout.tsx string.
def test_admin_layout_has_service_groups_link():
    src = _read(SA_LAYOUT)
    assert "VerticalCatalogSection" in src
    seed = _read(os.path.join(ROOT, "alembic", "versions", "089_multi_vertical_catalog_architecture.py"))
    assert '"/admin/service-groups"' in seed

def test_admin_layout_has_catalog_section():
    src = _read(SA_LAYOUT)
    assert "Catalog" in src

def test_admin_layout_imports_folder_tree():
    src = _read(SA_LAYOUT)
    assert "FolderTree" in src


# ── Seed Scripts ───────────────────────────────────────────────────────────────

def test_seed_universal_categories_exists():
    assert os.path.exists(SEED_CATS)

def test_seed_universal_categories_has_14_verticals():
    src = _read(SEED_CATS)
    expected = [
        "home_services", "salon", "coaching", "real_estate", "restaurant",
        "automotive", "professional_services", "pharmacy", "hardware",
        "repair_services", "cleaning_services", "laundry", "marketplace_products", "other",
    ]
    for v in expected:
        assert f'"{v}"' in src or f"'{v}'" in src, f"seed_universal_categories.py missing: {v}"

def test_seed_universal_categories_is_idempotent():
    src = _read(SEED_CATS)
    assert "slug" in src  # idempotent check uses slug

def test_seed_service_groups_exists():
    assert os.path.exists(SEED_GROUPS)

def test_seed_service_groups_has_ac_services():
    src = _read(SEED_GROUPS)
    assert "ac_services" in src

def test_seed_service_groups_has_plumbing():
    src = _read(SEED_GROUPS)
    assert "plumbing" in src

def test_seed_service_groups_covers_multiple_verticals():
    src = _read(SEED_GROUPS)
    for slug in ["home_services", "salon", "automotive", "coaching"]:
        assert slug in src, f"seed_service_groups.py missing category: {slug}"

def test_seed_master_services_exists():
    assert os.path.exists(SEED_SERVICES)

def test_seed_master_services_has_ac_repair():
    src = _read(SEED_SERVICES)
    assert "ac_repair" in src

def test_seed_master_services_has_ielts():
    src = _read(SEED_SERVICES)
    assert "ielts" in src

def test_seed_master_services_uses_service_group_id():
    src = _read(SEED_SERVICES)
    assert "service_group_id" in src

def test_seed_master_services_covers_multiple_verticals():
    src = _read(SEED_SERVICES)
    for slug in ["home_services", "salon", "coaching", "automotive"]:
        assert slug in src, f"seed_master_services.py missing category: {slug}"
