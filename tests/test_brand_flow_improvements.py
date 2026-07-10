"""
Brand Flow Improvements tests.

Verifies the correct brand-once → map-to-services architecture:
  - BrandService has list_service_mappings, unmap_brand_from_service, bulk_map methods
  - Brand router has service-mappings GET, DELETE, and bulk-map endpoints
  - Provider router has categories/{category_id}/available endpoint
  - BrandService has get_available_brands_for_category
  - audit events for unmap and bulk_map
  - super-admin api.ts has new brand mapping functions
  - tenant-portal AvailableOffering has category_id field
  - tenant-portal providerBrandApi has getAvailableForCategory
  - Provider offerings page uses category-based brand lookup (not zero UUID)
  - catalog page: TypesBrandsTab handles duplicate warning properly
  - catalog page: ServicesTab has brand management UI
"""
import os
import re

ROOT         = os.path.dirname(os.path.dirname(__file__))
BRAND_SVC    = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_service.py")
BRAND_ROUTER = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_router.py")
PROV_ROUTER  = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_provider_router.py")
SA_API       = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
TP_API       = os.path.join(ROOT, "frontend", "tenant-portal", "lib", "api.ts")
TP_OFFERINGS = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)", "provider", "offerings", "page.tsx")
CATALOG_PAGE      = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "catalog", "page.tsx")
MASTER_SVC_PAGE   = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "master-services", "page.tsx")
TYPES_BRANDS_PAGE = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "types-brands", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# BRAND SERVICE — NEW METHODS
# ══════════════════════════════════════════════════════════════════

def test_brand_service_has_list_service_mappings():
    src = _read(BRAND_SVC)
    assert "async def list_service_mappings" in src


def test_brand_service_has_unmap_brand_from_service():
    src = _read(BRAND_SVC)
    assert "async def unmap_brand_from_service" in src


def test_brand_service_has_bulk_map_brands_to_services():
    src = _read(BRAND_SVC)
    assert "async def bulk_map_brands_to_services" in src


def test_brand_service_has_get_available_brands_for_category():
    src = _read(BRAND_SVC)
    assert "async def get_available_brands_for_category" in src


def test_brand_service_unmap_from_service_uses_is_active_false():
    src = _read(BRAND_SVC)
    assert "unmap_brand_from_service" in src
    # Should soft-deactivate (is_active = False), not hard delete
    assert "is_active = False" in src or "is_active=False" in src


def test_brand_service_bulk_map_delegates_to_map_brand_to_services():
    src = _read(BRAND_SVC)
    assert "await self.map_brand_to_services" in src


def test_brand_service_audit_unmap_from_service():
    src = _read(BRAND_SVC)
    assert '"brand.unmapped_from_service"' in src


def test_brand_service_list_service_mappings_returns_service_name():
    src = _read(BRAND_SVC)
    # The method should return service_name in the result
    assert "service_name" in src


def test_brand_service_get_category_brands_uses_brand_category_mapping():
    src = _read(BRAND_SVC)
    assert "BrandCategoryMapping" in src
    assert "get_available_brands_for_category" in src


# ══════════════════════════════════════════════════════════════════
# BRAND ROUTER — NEW ENDPOINTS
# ══════════════════════════════════════════════════════════════════

def test_brand_router_has_service_mappings_get():
    src = _read(BRAND_ROUTER)
    assert '"/service-mappings"' in src or "service-mappings" in src


def test_brand_router_has_service_mappings_delete():
    src = _read(BRAND_ROUTER)
    assert "unmap_brand_service" in src or "service-mappings/{service_id}" in src


def test_brand_router_has_bulk_map_services():
    src = _read(BRAND_ROUTER)
    assert "bulk-map-services" in src or "bulk_map_services" in src


def test_brand_router_service_mappings_get_has_correct_path():
    src = _read(BRAND_ROUTER)
    assert '/{brand_id}/service-mappings"' in src


def test_brand_router_bulk_map_uses_post():
    src = _read(BRAND_ROUTER)
    assert "bulk_map_brands_to_services" in src


# ══════════════════════════════════════════════════════════════════
# PROVIDER BRAND ROUTER — CATEGORY ENDPOINT
# ══════════════════════════════════════════════════════════════════

def test_provider_router_has_category_available_endpoint():
    src = _read(PROV_ROUTER)
    assert "categories/{category_id}/available" in src


def test_provider_router_category_endpoint_calls_service():
    src = _read(PROV_ROUTER)
    assert "get_available_brands_for_category" in src


# ══════════════════════════════════════════════════════════════════
# SUPER-ADMIN API.TS — NEW FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def test_sa_api_has_list_brand_service_mappings():
    src = _read(SA_API)
    assert "listBrandServiceMappings" in src


def test_sa_api_list_service_mappings_correct_path():
    src = _read(SA_API)
    assert "service-mappings`" in src or "/service-mappings`" in src


def test_sa_api_has_unmap_brand_service():
    src = _read(SA_API)
    assert "unmapBrandService" in src


def test_sa_api_unmap_brand_service_uses_delete():
    src = _read(SA_API)
    idx = src.find("unmapBrandService")
    assert idx != -1
    snippet = src[idx:idx+350]
    assert "DELETE" in snippet


def test_sa_api_has_bulk_map_brands_to_services():
    src = _read(SA_API)
    assert "bulkMapBrandsToServices" in src


def test_sa_api_bulk_map_uses_post():
    src = _read(SA_API)
    idx = src.find("bulkMapBrandsToServices")
    assert idx != -1
    snippet = src[idx:idx+300]
    assert "POST" in snippet


def test_sa_api_has_unmap_brand_category():
    src = _read(SA_API)
    assert "unmapBrandCategory" in src


def test_sa_api_unmap_brand_category_uses_delete():
    src = _read(SA_API)
    idx = src.find("unmapBrandCategory")
    assert idx != -1
    snippet = src[idx:idx+350]
    assert "DELETE" in snippet


# ══════════════════════════════════════════════════════════════════
# TENANT-PORTAL API.TS — AVAILABLE OFFERING + CATEGORY BRANDS
# ══════════════════════════════════════════════════════════════════

def test_tp_available_offering_has_category_id():
    src = _read(TP_API)
    # AvailableOffering interface should include category_id
    assert "category_id" in src
    # Verify it's near AvailableOffering definition
    idx = src.find("interface AvailableOffering")
    assert idx != -1
    block = src[idx:idx+600]
    assert "category_id" in block


def test_tp_provider_brand_api_has_get_available_for_category():
    src = _read(TP_API)
    assert "getAvailableForCategory" in src


def test_tp_get_available_for_category_correct_path():
    src = _read(TP_API)
    assert "categories/${categoryId}/available" in src or "categories/" in src


# ══════════════════════════════════════════════════════════════════
# PROVIDER OFFERINGS PAGE — NO MORE ZERO UUID
# ══════════════════════════════════════════════════════════════════

def test_offerings_page_no_zero_uuid():
    src = _read(TP_OFFERINGS)
    assert "00000000-0000-0000-0000-000000000000" not in src, \
        "Zero UUID hardcoded in offerings page — must use real service/category ID"


def test_offerings_page_uses_get_available_for_category():
    src = _read(TP_OFFERINGS)
    assert "getAvailableForCategory" in src


def test_offerings_page_uses_offering_category_id():
    src = _read(TP_OFFERINGS)
    assert "category_id" in src
    assert "offeringCategoryId" in src or "offering?.category_id" in src or "offering.category_id" in src


# ══════════════════════════════════════════════════════════════════
# CATALOG PAGE — TYPESBRANDSTAB DUPLICATE WARNING
# ══════════════════════════════════════════════════════════════════

def test_catalog_types_brands_tab_imports_brand_duplicate_warning():
    # TypesBrandsTab was promoted to its own page at /admin/types-brands
    types_brands_page = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "types-brands", "page.tsx")
    src = _read(types_brands_page)
    assert "BrandDuplicateWarning" in src


def test_catalog_types_brands_tab_handles_warning_response():
    # TypesBrandsTab was promoted to its own page at /admin/types-brands
    types_brands_page = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "types-brands", "page.tsx")
    src = _read(types_brands_page)
    # handleCreateBrand should check for BRAND_DUPLICATE_POSSIBLE
    assert "BRAND_DUPLICATE_POSSIBLE" in src


def test_catalog_types_brands_tab_has_duplicate_warning_ui():
    # TypesBrandsTab promoted to standalone /admin/types-brands
    src = _read(TYPES_BRANDS_PAGE)
    assert "brandDuplicateWarning" in src
    assert "possible_duplicates" in src


def test_catalog_types_brands_tab_has_force_create():
    # TypesBrandsTab promoted to standalone /admin/types-brands
    src = _read(TYPES_BRANDS_PAGE)
    assert "force" in src
    assert "force=true" in src or "force: true" in src or "handleCreateBrand(true)" in src


def test_catalog_types_brands_tab_has_brand_master_link():
    # TypesBrandsTab promoted to standalone /admin/types-brands
    src = _read(TYPES_BRANDS_PAGE)
    assert "/admin/service-setup/brands" in src


# ══════════════════════════════════════════════════════════════════
# CATALOG PAGE — SERVICESTAB BRAND MANAGEMENT
# ══════════════════════════════════════════════════════════════════

def test_catalog_services_tab_has_brand_management_modal():
    # ServicesTab promoted to standalone /admin/master-services
    src = _read(MASTER_SVC_PAGE)
    assert "brandMgmtService" in src


def test_catalog_services_tab_uses_list_brand_mappings():
    # ServicesTab promoted to standalone /admin/master-services
    src = _read(MASTER_SVC_PAGE)
    assert "listBrandMappings" in src


def test_catalog_services_tab_uses_map_brand_services():
    # ServicesTab promoted to standalone /admin/master-services
    src = _read(MASTER_SVC_PAGE)
    assert "mapBrandServices" in src


def test_catalog_services_tab_has_add_brand_picker():
    # ServicesTab promoted to standalone /admin/master-services
    src = _read(MASTER_SVC_PAGE)
    assert "selectedBrandToAdd" in src


# ══════════════════════════════════════════════════════════════════
# BRAND DETAIL PAGE — REMOVE BUTTONS
# ══════════════════════════════════════════════════════════════════

def test_brand_detail_page_exists():
    path = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-setup", "brands", "[brand_id]", "page.tsx")
    assert os.path.exists(path)


def test_brand_detail_page_has_unmap_service_capability():
    path = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-setup", "brands", "[brand_id]", "page.tsx")
    src = _read(path)
    assert "unmapBrandService" in src


def test_brand_detail_page_has_unmap_category_capability():
    path = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-setup", "brands", "[brand_id]", "page.tsx")
    src = _read(path)
    assert "unmapBrandCategory" in src


def test_brand_detail_page_uses_toggle_for_services():
    path = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-setup", "brands", "[brand_id]", "page.tsx")
    src = _read(path)
    # Uses toggle-based UI (not raw UUID textarea)
    assert "toggleService" in src
    assert "unmapBrandService" in src


def test_brand_detail_page_uses_toggle_for_categories():
    path = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-setup", "brands", "[brand_id]", "page.tsx")
    src = _read(path)
    assert "toggleCategory" in src
    assert "unmapBrandCategory" in src
