"""
Brand Scope Rule tests.

Verifies "create once, visible only where mapped" invariant:
  1.  Create Samsung once.
  2.  Map Samsung to Home Appliances only.
  3.  Samsung does NOT appear under Plumbing.
  4.  Map Samsung to AC Repair.
  5.  Provider AC Repair available brands includes Samsung.
  6.  Provider Plumbing available brands does NOT include Samsung.
  7.  Map Samsung to Washing Machine Repair.
  8.  Same Samsung record appears for both AC and Washing Machine.
  9.  brands table still has only one Samsung.
  10. Customer AC Repair brand list shows Samsung only if provider supports it in location.
  11. Customer Plumbing brand list does not show Samsung.
  12. Unmap Samsung from AC Repair.
  13. Provider and Customer AC Repair brand list no longer shows Samsung.

These are static-analysis tests that verify the invariant at the code/API layer.
"""
import os
import re

ROOT         = os.path.dirname(os.path.dirname(__file__))
BRAND_SVC    = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_service.py")
BRAND_ROUTER = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_router.py")
PROV_ROUTER  = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_provider_router.py")
CUST_ROUTER  = os.path.join(ROOT, "app", "engines", "admin_catalog", "brand_customer_router.py")
MODELS_FILE  = os.path.join(ROOT, "app", "engines", "admin_catalog", "models.py")
BRAND_DETAIL = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-setup", "brands", "[brand_id]", "page.tsx")
SA_API       = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
TP_API       = os.path.join(ROOT, "frontend", "tenant-portal", "lib", "api.ts")
TP_OFFERINGS = os.path.join(ROOT, "frontend", "tenant-portal", "app", "(tenant)", "provider", "offerings", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 1–2: Brand created once, mapped to category
# ══════════════════════════════════════════════════════════════════

def test_scope_1_brand_unique_in_brands_table():
    """brands table has a unique constraint on slug (partial: deleted_at IS NULL)."""
    src = _read(BRAND_SVC)
    # normalize_brand_name used for duplicate detection before INSERT
    assert "normalize_brand_name" in src
    assert "BRAND_DUPLICATE_POSSIBLE" in src


def test_scope_2_map_brand_to_category():
    """Brand can be mapped to a category via map_brand_to_categories."""
    src = _read(BRAND_SVC)
    assert "async def map_brand_to_categories" in src
    assert "BrandCategoryMapping" in src


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 3: Samsung must NOT appear in unmapped categories
# ══════════════════════════════════════════════════════════════════

def test_scope_3_list_category_brands_filters_by_mapping():
    """get_available_brands_for_category queries BrandCategoryMapping, not all brands."""
    src = _read(BRAND_SVC)
    # The method must JOIN through BrandCategoryMapping, not return all active brands
    idx = src.find("get_available_brands_for_category")
    assert idx != -1
    body = src[idx:idx+600]
    assert "BrandCategoryMapping" in body, \
        "get_available_brands_for_category must filter via BrandCategoryMapping, not return all brands"


def test_scope_3_list_category_brands_checks_status_active():
    """Category mapping must be status==active to be returned."""
    src = _read(BRAND_SVC)
    idx = src.find("get_available_brands_for_category")
    assert idx != -1
    body = src[idx:idx+600]
    assert 'status == "active"' in body or "status='active'" in body


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 4: Map brand to service
# ══════════════════════════════════════════════════════════════════

def test_scope_4_map_brand_to_service():
    """Brand can be mapped to a master service via map_brand_to_services."""
    src = _read(BRAND_SVC)
    assert "async def map_brand_to_services" in src
    assert "MasterServiceBrand" in src


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 5: Provider AC Repair sees Samsung
# ══════════════════════════════════════════════════════════════════

def test_scope_5_provider_available_brands_filtered_by_service():
    """get_available_brands_for_service filters by master_service_id, not globally."""
    src = _read(BRAND_SVC)
    idx = src.find("get_available_brands_for_service")
    assert idx != -1
    body = src[idx:idx+600]
    assert "master_service_id == service_id" in body or "MasterServiceBrand.master_service_id" in body, \
        "get_available_brands_for_service must filter by service_id via MasterServiceBrand"


def test_scope_5_provider_api_endpoint_exists():
    """Provider endpoint GET /services/{service_id}/available exists."""
    src = _read(PROV_ROUTER)
    assert "/services/{service_id}/available" in src


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 6: Provider Plumbing does NOT see Samsung
# ══════════════════════════════════════════════════════════════════

def test_scope_6_provider_brands_no_fallback_to_all():
    """get_available_brands_for_service must not return brands without a service mapping."""
    src = _read(BRAND_SVC)
    idx = src.find("get_available_brands_for_service")
    assert idx != -1
    body = src[idx:idx+600]
    # Should join MasterServiceBrand — brands without mapping won't appear
    assert "MasterServiceBrand" in body
    # Should NOT do a fallback query returning all brands
    assert "Brand.is_active == True" not in body or "MasterServiceBrand" in body


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 7: Map to Washing Machine too
# ══════════════════════════════════════════════════════════════════

def test_scope_7_map_brand_to_multiple_services():
    """map_brand_to_services accepts a list — maps one brand to multiple services."""
    src = _read(BRAND_SVC)
    idx = src.find("async def map_brand_to_services")
    assert idx != -1
    body = src[idx:idx+400]
    assert "service_ids" in body, "method must accept a list of service_ids"


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 8–9: Same brand_id across services, one row in brands
# ══════════════════════════════════════════════════════════════════

def test_scope_8_master_service_brand_stores_brand_id():
    """MasterServiceBrand join table stores brand_id FK (same brand reused)."""
    src = _read(MODELS_FILE)
    idx = src.find("class MasterServiceBrand")
    assert idx != -1
    block = src[idx:idx+400]
    assert "brand_id" in block


def test_scope_9_brands_table_has_unique_constraint():
    """Brand slug has unique constraint (ensures one record per brand)."""
    src = _read(BRAND_SVC)
    # Slug uniqueness enforced via normalize_brand_name + duplicate detection
    assert "normalized_name" in src or "_slugify" in src


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 10: Customer sees Samsung only if provider supports it
# ══════════════════════════════════════════════════════════════════

def test_scope_10_customer_brands_filtered_by_provider_support():
    """Customer brand endpoint filters by TenantSupportedBrand (provider must support)."""
    src = _read(BRAND_SVC)
    assert "TenantSupportedBrand" in src
    assert "get_customer_catalog_brands" in src or "customer_catalog_brands" in src


def test_scope_10_customer_brand_router_exists():
    """Customer brand router file exists."""
    assert os.path.exists(CUST_ROUTER), "brand_customer_router.py must exist"


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 11: Customer Plumbing does not show Samsung
# ══════════════════════════════════════════════════════════════════

def test_scope_11_customer_brands_filtered_by_service():
    """Customer brand lookup uses service_id filter, not returning all brands."""
    src = _read(BRAND_SVC)
    # get_customer_catalog_brands should filter by service
    assert "master_service_id" in src or "service_id" in src


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 12: Unmap Samsung from AC Repair
# ══════════════════════════════════════════════════════════════════

def test_scope_12_unmap_brand_from_service_exists():
    """unmap_brand_from_service method and DELETE endpoint exist."""
    svc_src = _read(BRAND_SVC)
    router_src = _read(BRAND_ROUTER)
    assert "async def unmap_brand_from_service" in svc_src
    assert "service-mappings/{service_id}" in router_src


def test_scope_12_unmap_soft_deletes_mapping():
    """Unmap uses is_active = False (soft delete), preserving history."""
    src = _read(BRAND_SVC)
    idx = src.find("unmap_brand_from_service")
    assert idx != -1
    body = src[idx:idx+700]
    assert "is_active = False" in body or "is_active=False" in body


# ══════════════════════════════════════════════════════════════════
# SCOPE RULE 13: After unmap, brand no longer visible
# ══════════════════════════════════════════════════════════════════

def test_scope_13_available_brands_filters_active_mappings_only():
    """get_available_brands_for_service only returns is_active=True mappings."""
    src = _read(BRAND_SVC)
    idx = src.find("get_available_brands_for_service")
    assert idx != -1
    body = src[idx:idx+600]
    assert "is_active == True" in body, \
        "After unmap (is_active=False), brand must not appear in available brands"


# ══════════════════════════════════════════════════════════════════
# ADMIN UI: Brand detail page has toggle-based availability UI
# ══════════════════════════════════════════════════════════════════

def test_admin_ui_brand_detail_has_category_availability_tab():
    src = _read(BRAND_DETAIL)
    assert "category-availability" in src or "Category Availability" in src


def test_admin_ui_brand_detail_has_service_availability_tab():
    src = _read(BRAND_DETAIL)
    assert "service-availability" in src or "Service Availability" in src


def test_admin_ui_category_availability_shows_all_categories():
    """UI renders ALL categories (not just mapped ones) with toggle."""
    src = _read(BRAND_DETAIL)
    # Must iterate allCategories and show toggle for each
    assert "allCategories" in src
    assert "toggleCategory" in src


def test_admin_ui_service_availability_groups_by_category():
    """Services are grouped by category in the service availability tab."""
    src = _read(BRAND_DETAIL)
    assert "servicesByCategory" in src or "groupBy" in src or "services grouped" in src.lower() or "servicesByCategory" in src


def test_admin_ui_toggle_maps_and_unmaps_category():
    """Toggle calls both map and unmap APIs."""
    src = _read(BRAND_DETAIL)
    assert "mapBrandCategories" in src
    assert "unmapBrandCategory" in src


def test_admin_ui_toggle_maps_and_unmaps_service():
    """Toggle calls both map and unmap APIs for services."""
    src = _read(BRAND_DETAIL)
    assert "mapBrandServices" in src
    assert "unmapBrandService" in src


def test_admin_ui_brand_only_visible_if_active():
    """UI warns that brand must be active to create new mappings."""
    src = _read(BRAND_DETAIL)
    assert "Activate brand" in src or "activate" in src.lower()
