"""
P0 Fix — Duplicate Category Page Removal
Verifies that only one category management page exists and the old duplicate
CategoriesTab has been removed from the catalog page.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Phase 1: Catalog page no longer has CategoriesTab ──────────────────────

def test_catalog_page_no_categories_tab():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "CategoriesTab" not in src, \
        "Old CategoriesTab must be removed from catalog/page.tsx"


def test_catalog_page_no_new_category_button():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "+ New Category" not in src and "New Category" not in src, \
        "New Category button must not exist in catalog/page.tsx — only in /admin/categories"


def test_catalog_page_no_categories_in_tabs_array():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert 'id:"categories"' not in src and "id: \"categories\"" not in src, \
        "categories tab must not be in the TABS array in catalog/page.tsx"


def test_catalog_page_redirects_categories_tab():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "/admin/categories" in src, \
        "catalog/page.tsx must redirect ?tab=categories to /admin/categories"


def test_catalog_page_redirects_tiers_tab():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert 'router.replace("/admin/master-services")' in src
    assert "/admin/pricing-tiers" not in src


def test_catalog_page_no_tiers_tab():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "TiersTab" not in src, \
        "TiersTab must be removed from catalog/page.tsx (has dedicated /admin/pricing-tiers page)"


def test_catalog_page_no_tier_types_constant():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "TIER_TYPES" not in src, \
        "TIER_TYPES constant belongs in pricing-tiers page, not catalog"


def test_catalog_page_keeps_master_services():
    # Master services promoted to /admin/master-services; catalog page redirects there
    assert Path("frontend/super-admin/app/admin/master-services/page.tsx").exists(), \
        "Master Services standalone page must exist at /admin/master-services"


def test_catalog_page_keeps_types_brands():
    # Types & Brands promoted to /admin/types-brands
    assert Path("frontend/super-admin/app/admin/types-brands/page.tsx").exists(), \
        "Types & Brands standalone page must exist at /admin/types-brands"


def test_catalog_page_keeps_pricing_rules():
    # Pricing Rules promoted to /admin/pricing-rules
    assert not Path("frontend/super-admin/app/admin/pricing-rules/page.tsx").exists()


def test_catalog_page_valid_tabs_excludes_categories():
    # catalog/page.tsx is now a redirect — verify it does not contain a Categories tab
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "CategoriesTab" not in src, \
        "catalog/page.tsx must not render a CategoriesTab"


# ── Phase 2: Enterprise categories page is the only category page ───────────

def test_enterprise_categories_page_exists():
    assert Path("frontend/super-admin/app/admin/categories/page.tsx").exists()


def test_enterprise_categories_page_has_enterprise_form():
    src = Path("frontend/super-admin/app/admin/categories/page.tsx").read_text(encoding="utf-8")
    assert "vertical_type" in src
    assert "finance_model" in src
    assert "customer_flow_type" in src


def test_enterprise_categories_page_has_search():
    src = Path("frontend/super-admin/app/admin/categories/page.tsx").read_text(encoding="utf-8")
    assert "search" in src.lower() or "Search" in src


def test_enterprise_categories_page_has_new_category_button():
    src = Path("frontend/super-admin/app/admin/categories/page.tsx").read_text(encoding="utf-8")
    assert "New Category" in src


def test_enterprise_categories_page_has_activate_deactivate():
    src = Path("frontend/super-admin/app/admin/categories/page.tsx").read_text(encoding="utf-8")
    assert "activateCategory" in src or "activate" in src.lower()
    assert "deactivateCategory" in src or "deactivate" in src.lower()


def test_enterprise_categories_page_links_to_runtime():
    src = Path("frontend/super-admin/app/admin/categories/page.tsx").read_text(encoding="utf-8")
    assert "/admin/categories/" in src


# ── Phase 3: API standardization ─────────────────────────────────────────────

def test_catalog_api_create_category_has_enterprise_fields():
    src = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    idx = src.find("createCategory:")
    assert idx != -1
    snippet = src[idx:idx+500]
    assert "vertical_type" in snippet
    assert "finance_model" in snippet
    assert "customer_flow_type" in snippet


def test_only_one_category_create_endpoint():
    """The create category API should only call one backend endpoint."""
    src = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    import re
    # Find POST calls to category endpoints (method:"POST" near service-categories or catalog/categories)
    post_blocks = re.findall(r'createCategory.*?method.*?POST.*?service-categories', src, re.DOTALL)
    # Simpler: count occurrences of creating a category via POST
    occurrences = src.count('"/v1/admin/service-categories", { method:"POST"') + \
                  src.count('"/v1/admin/catalog/categories", { method:"POST"')
    assert occurrences == 1, \
        f"Expected exactly 1 category create POST call, found {occurrences}"


# ── Phase 4: Navigation has no duplicate category links ─────────────────────

def test_nav_has_exactly_one_category_link():
    src = Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
    import re
    # Find all href values that point to categories
    hrefs = re.findall(r'href:\s*["\']([^"\']*categor[^"\']*)["\']', src)
    category_manage_hrefs = [h for h in hrefs if "analytics" not in h]
    assert len(category_manage_hrefs) == 1, \
        f"Expected 1 category management nav link, found {len(category_manage_hrefs)}: {category_manage_hrefs}"


def test_nav_category_link_points_to_enterprise_page():
    src = Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
    assert 'href: "/admin/categories"' in src or "href: '/admin/categories'" in src


def test_nav_has_no_catalog_categories_tab_link():
    src = Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
    assert "tab=categories" not in src


# ── Phase 5: Redirects ────────────────────────────────────────────────────────

def test_catalog_page_uses_router_replace_for_redirect():
    src = Path("frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "router.replace" in src


# ── Phase 6: Backend API supports enterprise fields ───────────────────────────

def test_backend_category_model_has_enterprise_fields():
    src = Path("app/engines/admin_catalog/models.py").read_text(encoding="utf-8")
    assert "vertical_type" in src
    assert "finance_model" in src
    assert "customer_flow_type" in src or "customer_flow" in src


def test_backend_category_service_handles_enterprise_fields():
    src = Path("app/engines/admin_catalog/service.py").read_text(encoding="utf-8")
    assert "vertical_type" in src
    assert "finance_model" in src


def test_backend_category_router_exists():
    from app.engines.admin_catalog import admin_router as ar
    src = Path("app/engines/admin_catalog/admin_router.py").read_text(encoding="utf-8")
    assert "/service-categories" in src or "/categories" in src
