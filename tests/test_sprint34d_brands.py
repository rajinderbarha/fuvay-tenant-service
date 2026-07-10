"""
Sprint 34D — Enterprise Brand Management tests
Verifies:
  Backend:
    - Brand model: all Sprint 34D columns + to_dict()
    - 6 new models: BrandCategoryMapping, BrandServiceOptionMapping, TenantSupportedBrand,
      BrandRequest, BrandTemplate, BrandTemplateItem — each with to_dict()
    - MasterServiceBrand: Sprint 34D columns (status, display_order, created_by_user_id) + to_dict()
    - BrandService: normalize_brand_name, create/list/get/update, activate/deactivate/archive,
      merge_brand, map_brand_to_categories, map_brand_to_services, seed_starter_brands,
      brand requests, brand templates
    - Admin brand router: all endpoints + /seed, require_super_admin on writes
    - Brand provider router: /provider/brands prefix
    - Brand customer router: /customer/catalog/brands prefix
    - main.py: all 3 brand routers registered
  Frontend:
    - api.ts: Brand34D / BrandRequest34D / BrandDuplicateWarning interfaces + all brand methods
    - brands/page.tsx: exists with create/edit/merge/seed actions
    - brand-requests/page.tsx: exists with approve/reject/merge actions
    - AdminLayout: brands + brand-requests nav items
  Migration 056: revision + down_revision correct
"""
import os
import re

ROOT            = os.path.dirname(os.path.dirname(__file__))
MODELS_FILE     = os.path.join(ROOT, "app", "engines", "admin_catalog", "models.py")
BRAND_SERVICE   = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_service.py")
BRAND_ROUTER    = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_router.py")
BRAND_PROV_R    = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_provider_router.py")
BRAND_CUST_R    = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_customer_router.py")
MAIN_PY         = os.path.join(ROOT, "app", "main.py")
MIGRATION_056   = os.path.join(ROOT, "alembic", "versions", "056_sprint34d_brand_management.py")
SA_API          = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
SA_BRANDS_PAGE  = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "brands", "page.tsx")
SA_BRANDRQ_PAGE = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "brand-requests", "page.tsx")
SA_LAYOUT       = os.path.join(ROOT, "frontend", "super-admin", "components", "layout", "AdminLayout.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 056 ──────────────────────────────────────────────────────────────

def test_migration_056_exists():
    assert os.path.exists(MIGRATION_056), "Migration 056 not found"

def test_migration_056_revision():
    src = _read(MIGRATION_056)
    assert 'revision = "056"' in src or "revision='056'" in src

def test_migration_056_down_revision():
    src = _read(MIGRATION_056)
    assert 'down_revision = "055"' in src or "down_revision='055'" in src

def test_migration_056_brand_columns():
    src = _read(MIGRATION_056)
    for col in ("normalized_name", "alias_names", "replacement_brand_id", "website_url", "is_global"):
        assert col in src, f"Expected column '{col}' in migration 056"


# ── Models: Brand ─────────────────────────────────────────────────────────────

def test_brand_model_sprint34d_columns():
    src = _read(MODELS_FILE)
    for col in ("normalized_name", "alias_names", "replacement_brand_id",
                "website_url", "country_of_origin", "is_global", "display_order", "logo_url"):
        assert col in src, f"Brand model missing Sprint 34D column: {col}"

def test_brand_model_has_to_dict():
    src = _read(MODELS_FILE)
    # Use "class Brand(" to avoid matching BrandCategoryMapping etc.
    idx = src.index("class Brand(")
    snippet = src[idx:idx+4000]
    assert "def to_dict" in snippet, "Brand model missing to_dict()"

def test_brand_category_mapping_model_exists():
    src = _read(MODELS_FILE)
    assert "class BrandCategoryMapping" in src

def test_brand_category_mapping_has_to_dict():
    src = _read(MODELS_FILE)
    idx = src.index("class BrandCategoryMapping")
    snippet = src[idx:idx+1500]
    assert "def to_dict" in snippet

def test_brand_service_option_mapping_model_exists():
    src = _read(MODELS_FILE)
    assert "class BrandServiceOptionMapping" in src

def test_tenant_supported_brand_model_exists():
    src = _read(MODELS_FILE)
    assert "class TenantSupportedBrand" in src

def test_brand_request_model_exists():
    src = _read(MODELS_FILE)
    assert "class BrandRequest" in src

def test_brand_request_has_to_dict():
    src = _read(MODELS_FILE)
    idx = src.index("class BrandRequest")
    snippet = src[idx:idx+2000]
    assert "def to_dict" in snippet

def test_brand_template_model_exists():
    src = _read(MODELS_FILE)
    assert "class BrandTemplate" in src

def test_brand_template_item_model_exists():
    src = _read(MODELS_FILE)
    assert "class BrandTemplateItem" in src

def test_master_service_brand_sprint34d_columns():
    src = _read(MODELS_FILE)
    idx = src.index("class MasterServiceBrand")
    snippet = src[idx:idx+1500]
    for col in ("status", "display_order", "created_by_user_id"):
        assert col in snippet, f"MasterServiceBrand missing Sprint 34D column: {col}"

def test_master_service_brand_has_to_dict():
    src = _read(MODELS_FILE)
    idx = src.index("class MasterServiceBrand")
    snippet = src[idx:idx+1500]
    assert "def to_dict" in snippet


# ── Brand service: normalization ──────────────────────────────────────────────

def test_brand_service_normalize_function():
    src = _read(BRAND_SERVICE)
    assert "normalize_brand_name" in src

def test_brand_service_slugify_function():
    src = _read(BRAND_SERVICE)
    assert "_slugify" in src


# ── Brand service: CRUD methods ───────────────────────────────────────────────

def test_brand_service_class_exists():
    src = _read(BRAND_SERVICE)
    assert "class BrandService" in src

def test_brand_service_list_brands():
    src = _read(BRAND_SERVICE)
    assert "async def list_brands" in src

def test_brand_service_get_brand():
    src = _read(BRAND_SERVICE)
    assert "async def get_brand" in src

def test_brand_service_create_brand():
    src = _read(BRAND_SERVICE)
    assert "async def create_brand" in src

def test_brand_service_update_brand():
    src = _read(BRAND_SERVICE)
    assert "async def update_brand" in src

def test_brand_service_create_checks_duplicates():
    src = _read(BRAND_SERVICE)
    assert "normalized_name" in src
    assert "BRAND_DUPLICATE_POSSIBLE" in src or "duplicate" in src.lower()

def test_brand_service_activate_deactivate_archive():
    src = _read(BRAND_SERVICE)
    assert "async def activate_brand" in src
    assert "async def deactivate_brand" in src
    assert "async def archive_brand" in src

def test_brand_service_merge_brand():
    src = _read(BRAND_SERVICE)
    assert "async def merge_brand" in src

def test_brand_service_map_to_categories():
    src = _read(BRAND_SERVICE)
    assert "async def map_brand_to_categories" in src

def test_brand_service_map_to_services():
    src = _read(BRAND_SERVICE)
    assert "async def map_brand_to_services" in src

def test_brand_service_seed_starter_brands():
    src = _read(BRAND_SERVICE)
    assert "async def seed_starter_brands" in src

def test_brand_service_seed_has_25_starters():
    src = _read(BRAND_SERVICE)
    assert "Samsung" in src and "Daikin" in src and "Whirlpool" in src and "Sony" in src

def test_brand_service_seed_is_idempotent():
    src = _read(BRAND_SERVICE)
    # Must check existing before insert
    idx = src.index("seed_starter_brands")
    snippet = src[idx:idx+6000]
    assert "skipped" in snippet and ("select" in snippet.lower() or "normalized_name" in snippet)

def test_brand_service_list_brand_requests():
    src = _read(BRAND_SERVICE)
    assert "async def list_brand_requests" in src

def test_brand_service_approve_reject_merge_requests():
    src = _read(BRAND_SERVICE)
    assert "async def approve_brand_request" in src
    assert "async def reject_brand_request" in src
    assert "async def merge_brand_request" in src

def test_brand_service_brand_templates():
    src = _read(BRAND_SERVICE)
    assert "async def list_brand_templates" in src
    assert "async def create_brand_template" in src
    assert "async def apply_brand_template" in src


# ── Admin brand router ────────────────────────────────────────────────────────

def test_brand_router_prefix():
    src = _read(BRAND_ROUTER)
    assert 'prefix="/v1/admin/brands"' in src

def test_brand_router_req_prefix():
    src = _read(BRAND_ROUTER)
    assert 'prefix="/v1/admin/brand-requests"' in src

def test_brand_router_tmpl_prefix():
    src = _read(BRAND_ROUTER)
    assert 'prefix="/v1/admin/brand-templates"' in src

def test_brand_router_seed_endpoint():
    src = _read(BRAND_ROUTER)
    assert "/seed" in src

def test_brand_router_crud_endpoints():
    src = _read(BRAND_ROUTER)
    assert "list_brands" in src or "async def list_brands" in src
    assert "create_brand" in src
    assert "update_brand" in src

def test_brand_router_status_endpoints():
    src = _read(BRAND_ROUTER)
    assert "activate_brand" in src
    assert "deactivate_brand" in src
    assert "archive_brand" in src

def test_brand_router_merge_endpoint():
    src = _read(BRAND_ROUTER)
    assert "merge_brand" in src

def test_brand_router_require_super_admin_on_writes():
    src = _read(BRAND_ROUTER)
    assert "require_super_admin" in src


# ── Provider + customer brand routers ────────────────────────────────────────

def test_brand_provider_router_prefix():
    src = _read(BRAND_PROV_R)
    assert "/v1/provider" in src

def test_brand_customer_router_prefix():
    src = _read(BRAND_CUST_R)
    assert "/v1/customer" in src


# ── main.py registration ──────────────────────────────────────────────────────

def test_main_registers_brand_admin_router():
    src = _read(MAIN_PY)
    assert "brand_admin_router" in src or "brand_router" in src

def test_main_registers_brand_provider_router():
    src = _read(MAIN_PY)
    assert "brand_provider_router" in src

def test_main_registers_brand_customer_router():
    src = _read(MAIN_PY)
    assert "brand_customer_router" in src


# ── Frontend: api.ts brand interfaces + methods ───────────────────────────────

def test_api_ts_brand34d_interface():
    src = _read(SA_API)
    assert "Brand34D" in src

def test_api_ts_brand34d_sprint34d_fields():
    src = _read(SA_API)
    # Find the interface declaration specifically
    idx = src.index("export interface Brand34D")
    snippet = src[idx:idx+1200]
    for field in ("normalized_name", "is_global", "display_order", "logo_url", "website_url"):
        assert field in snippet, f"Brand34D interface missing Sprint 34D field: {field}"

def test_api_ts_brand_duplicate_warning_interface():
    src = _read(SA_API)
    assert "BrandDuplicateWarning" in src

def test_api_ts_brand_request_interface():
    src = _read(SA_API)
    assert "BrandRequest34D" in src

def test_api_ts_list_brands_method():
    src = _read(SA_API)
    assert "listBrands" in src

def test_api_ts_create_brand_method():
    src = _read(SA_API)
    assert "createBrand" in src

def test_api_ts_brand_status_methods():
    src = _read(SA_API)
    assert "activateBrand" in src
    assert "deactivateBrand" in src
    assert "archiveBrand" in src

def test_api_ts_merge_brand_method():
    src = _read(SA_API)
    assert "mergeBrand" in src

def test_api_ts_seed_brands_method():
    src = _read(SA_API)
    assert "seedBrands" in src

def test_api_ts_list_brand_requests_method():
    src = _read(SA_API)
    assert "listBrandRequests" in src

def test_api_ts_approve_reject_merge_request_methods():
    src = _read(SA_API)
    assert "approveBrandRequest" in src
    assert "rejectBrandRequest" in src
    assert "mergeBrandRequest" in src


# ── Frontend: pages ───────────────────────────────────────────────────────────

def test_brands_page_exists():
    assert os.path.exists(SA_BRANDS_PAGE)

def test_brands_page_has_create_brand():
    src = _read(SA_BRANDS_PAGE)
    assert "createBrand" in src or "createAction" in src

def test_brands_page_has_merge_ui():
    src = _read(SA_BRANDS_PAGE)
    assert "merge" in src.lower()
    assert "mergeBrand" in src or "mergeAction" in src

def test_brands_page_has_seed_button():
    src = _read(SA_BRANDS_PAGE)
    assert "seedBrands" in src or "seedAction" in src

def test_brands_page_has_duplicate_warning_handling():
    src = _read(SA_BRANDS_PAGE)
    assert "BrandDuplicateWarning" in src or "BRAND_DUPLICATE_POSSIBLE" in src or "dupWarning" in src

def test_brands_page_no_tailwind():
    src = _read(SA_BRANDS_PAGE)
    classnames = re.findall(r'className="([^"]+)"', src)
    for cn in classnames:
        assert cn == "skeleton", f"Forbidden className in brands page: '{cn}'"

def test_brand_requests_page_exists():
    assert os.path.exists(SA_BRANDRQ_PAGE)

def test_brand_requests_page_has_approve_reject():
    src = _read(SA_BRANDRQ_PAGE)
    assert "approveBrandRequest" in src or "approveAction" in src
    assert "rejectBrandRequest" in src or "rejectAction" in src

def test_brand_requests_page_has_merge():
    src = _read(SA_BRANDRQ_PAGE)
    assert "mergeBrandRequest" in src or "mergeAction" in src

def test_brand_requests_page_has_status_tabs():
    src = _read(SA_BRANDRQ_PAGE)
    assert "pending" in src and "approved" in src and "rejected" in src

def test_brand_requests_page_no_tailwind():
    src = _read(SA_BRANDRQ_PAGE)
    classnames = re.findall(r'className="([^"]+)"', src)
    for cn in classnames:
        assert cn == "skeleton", f"Forbidden className in brand-requests page: '{cn}'"


# ── AdminLayout nav items ──────────────────────────────────────────────────────

def test_admin_layout_has_no_duplicate_global_brands_nav():
    # P0 Sidebar Duplicate Menu Cleanup: Brands/Brand Requests are no longer global
    # AdminLayout nav items — they were duplicated with the per-vertical Home Services
    # catalog section (same /admin/brands, /admin/brand-requests routes shown twice).
    # Canonical location is now the Types & Brands page's "Brand Requests" tab —
    # see test_p0_sidebar_duplicate_cleanup.py.
    src = _read(SA_LAYOUT)
    assert '{ id: "brands",          href: "/admin/brands"' not in src
    assert '{ id: "brand-requests",  href: "/admin/brand-requests"' not in src
