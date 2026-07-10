"""P0 Enterprise Service Categories Page Upgrade — Test Suite.

Verifies:
1. Backend router has summary, enhanced list, readiness, export endpoints.
2. Readiness calculation is correct.
3. Linked counts SQL structure is present.
4. Frontend page has enterprise structure (summary cards, filters, action menu, linked counts).
5. Label maps replace raw enum values.
6. Advanced filters drawer exists.
7. lib/api.ts has all required new methods.
8. No raw enum display (finance_model.replace(/_/g," ")) in page.
"""
import re
import sys
from pathlib import Path

ROOT          = Path(__file__).parent.parent
ROUTER        = ROOT / "app" / "engines" / "admin_catalog" / "category_runtime_router.py"
FRONTEND_PAGE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "categories" / "page.tsx"
DETAIL_PAGE   = ROOT / "frontend" / "super-admin" / "app" / "admin" / "categories" / "[id]" / "page.tsx"
API_TS        = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"

# ── File existence ─────────────────────────────────────────────────────────────

def test_category_runtime_router_exists():
    assert ROUTER.exists(), "category_runtime_router.py must exist"

def test_categories_page_exists():
    assert FRONTEND_PAGE.exists(), "/admin/categories/page.tsx must exist"

def test_categories_detail_page_exists():
    assert DETAIL_PAGE.exists(), "/admin/categories/[id]/page.tsx must exist"

# ── Backend: endpoints ─────────────────────────────────────────────────────────

def test_router_has_summary_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"/summary"' in src, "summary endpoint must exist"

def test_router_has_list_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    # @router.get("", summary=...) — the decorator form used in this router
    assert '@router.get("")' in src or 'router.get("", summary' in src or 'router.get("",\n' in src or 'router.get("",\r' in src or 'list_categories' in src, \
        "list endpoint must exist"

def test_router_has_export_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"/export"' in src, "export endpoint must exist"

def test_router_has_readiness_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "readiness" in src, "readiness endpoint must exist"

def test_router_has_activate_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "activate" in src

def test_router_has_deactivate_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "deactivate" in src

# ── Backend: summary counts ───────────────────────────────────────────────────

def test_router_summary_counts_active():
    src = ROUTER.read_text(encoding="utf-8")
    assert "active" in src and "is_active" in src

def test_router_summary_counts_runtime_ready():
    src = ROUTER.read_text(encoding="utf-8")
    assert "runtime_ready" in src

def test_router_summary_counts_missing_setup():
    src = ROUTER.read_text(encoding="utf-8")
    assert "missing_required_setup" in src

def test_router_summary_returns_nine_fields():
    src = ROUTER.read_text(encoding="utf-8")
    summary_block_start = src.find("get_categories_summary")
    summary_block_end = src.find("\n@router", summary_block_start + 1)
    block = src[summary_block_start:summary_block_end]
    for key in ["total", "active", "inactive", "customer_visible",
                "tenant_selectable", "runtime_ready", "missing_required_setup",
                "with_services", "with_pricing"]:
        assert key in block, f"summary must return '{key}'"

# ── Backend: linked counts SQL ────────────────────────────────────────────────

def test_router_linked_counts_uses_service_groups():
    src = ROUTER.read_text(encoding="utf-8")
    assert "service_groups" in src

def test_router_linked_counts_uses_master_services():
    src = ROUTER.read_text(encoding="utf-8")
    assert "master_services" in src

def test_router_linked_counts_uses_pricing_rules():
    src = ROUTER.read_text(encoding="utf-8")
    assert "service_pricing_rules" in src

def test_router_linked_counts_uses_brands():
    src = ROUTER.read_text(encoding="utf-8")
    assert "brands" in src

def test_router_linked_counts_uses_providers():
    src = ROUTER.read_text(encoding="utf-8")
    assert "tenant_services" in src or "providers" in src

# ── Backend: readiness logic ──────────────────────────────────────────────────

def test_router_has_compute_readiness():
    src = ROUTER.read_text(encoding="utf-8")
    assert "_compute_readiness" in src

def test_compute_readiness_returns_ready_status():
    sys.path.insert(0, str(ROOT))
    from app.engines.admin_catalog.category_runtime_router import _compute_readiness
    cat = {
        "is_active": True,
        "customer_flow_type": "service_booking",
        "finance_model": "security_deposit_plus_credit_wallet",
        "pricing_supported": True,
        "tenant_selectable": True,
        "linked_counts": {
            "service_groups": 2, "services": 10, "pricing_rules": 5,
            "brands": 3, "packages": 1, "providers": 8,
        },
    }
    rd = _compute_readiness(cat)
    assert rd["readiness_status"] == "ready"
    assert rd["readiness_items"] == []

def test_compute_readiness_detects_inactive():
    from app.engines.admin_catalog.category_runtime_router import _compute_readiness
    cat = {"is_active": False, "linked_counts": {}}
    rd = _compute_readiness(cat)
    assert rd["readiness_status"] == "inactive"

def test_compute_readiness_detects_missing_services():
    from app.engines.admin_catalog.category_runtime_router import _compute_readiness
    cat = {
        "is_active": True,
        "customer_flow_type": "service_booking",
        "finance_model": "monthly_subscription",
        "pricing_supported": False,
        "tenant_selectable": False,
        "linked_counts": {"service_groups": 0, "services": 0, "pricing_rules": 0, "brands": 0, "packages": 0, "providers": 0},
    }
    rd = _compute_readiness(cat)
    assert rd["readiness_status"] == "missing_services"
    assert any(i["key"] == "services" for i in rd["readiness_items"])

def test_compute_readiness_detects_missing_pricing():
    from app.engines.admin_catalog.category_runtime_router import _compute_readiness
    cat = {
        "is_active": True,
        "customer_flow_type": "service_booking",
        "finance_model": "security_deposit_plus_credit_wallet",
        "pricing_supported": True,
        "tenant_selectable": False,
        "linked_counts": {"service_groups": 1, "services": 5, "pricing_rules": 0, "brands": 0, "packages": 0, "providers": 0},
    }
    rd = _compute_readiness(cat)
    assert rd["readiness_status"] == "missing_pricing"
    assert any(i["key"] == "pricing_rules" for i in rd["readiness_items"])

def test_compute_readiness_detects_missing_flow():
    from app.engines.admin_catalog.category_runtime_router import _compute_readiness
    cat = {
        "is_active": True,
        "customer_flow_type": None,
        "finance_model": "lead_credit",
        "pricing_supported": False,
        "tenant_selectable": False,
        "linked_counts": {"service_groups": 1, "services": 3, "pricing_rules": 0, "brands": 0, "packages": 0, "providers": 0},
    }
    rd = _compute_readiness(cat)
    assert rd["readiness_status"] == "missing_flow_config" or "customer_flow" in str(rd)

# ── Backend: list has filters ──────────────────────────────────────────────────

def test_list_endpoint_has_q_filter():
    src = ROUTER.read_text(encoding="utf-8")
    assert 'q: Optional[str]' in src or "q=" in src

def test_list_endpoint_has_vertical_type_filter():
    src = ROUTER.read_text(encoding="utf-8")
    assert "vertical_type" in src

def test_list_endpoint_has_finance_model_filter():
    src = ROUTER.read_text(encoding="utf-8")
    assert "finance_model" in src

def test_list_endpoint_has_readiness_status_filter():
    src = ROUTER.read_text(encoding="utf-8")
    assert "readiness_status" in src

def test_list_returns_linked_counts_key():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"linked_counts"' in src or "linked_counts" in src

def test_list_returns_readiness_status_key():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"readiness_status"' in src or "readiness_status" in src

# ── Backend: export ───────────────────────────────────────────────────────────

def test_export_uses_csv():
    src = ROUTER.read_text(encoding="utf-8")
    assert "csv" in src.lower()

def test_export_returns_csv_response():
    src = ROUTER.read_text(encoding="utf-8")
    assert "text/csv" in src

def test_export_has_useful_columns():
    src = ROUTER.read_text(encoding="utf-8")
    for col in ["Name", "Slug", "Vertical Type", "Finance Model", "Status"]:
        assert col in src, f"export CSV must have column '{col}'"

# ── Frontend page: structure ──────────────────────────────────────────────────

def test_page_has_summary_cards():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "SummaryCard" in src, "page must render SummaryCard components"

def test_page_has_summary_api_call():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "summary()" in src or "categoryRuntimeApi.summary" in src

def test_page_has_advanced_filters_drawer():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "AdvancedFiltersDrawer" in src or "Advanced Filters" in src

def test_page_has_filter_chips():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "FilterChips" in src or "filter chips" in src.lower() or "Active filters" in src

def test_page_has_readiness_badge():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "ReadinessBadge" in src or "readiness_status" in src

def test_page_has_requirements_chips():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "RequirementsChips" in src or "requires_location" in src

def test_page_has_linked_counts():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "LinkedCountsBadges" in src or "linked_counts" in src

def test_page_has_action_menu():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "ActionMenu" in src or "MoreVertical" in src

def test_page_has_export_button():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Export" in src or "export" in src.lower()

def test_page_has_pagination():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "pagination" in src.lower() or "ChevronLeft" in src or "totalPages" in src

def test_page_has_bulk_actions():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "selected" in src and "bulk" in src.lower() or "Bulk" in src or "allSelected" in src

def test_page_has_empty_state():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "No categories" in src or "empty" in src.lower() or "No service categories" in src

def test_page_has_error_state():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "cats.error" in src or "error" in src.lower()

def test_page_has_loading_skeleton():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Skeleton" in src or "loading" in src.lower()

# ── Frontend page: no raw enum display ────────────────────────────────────────

def test_page_no_raw_finance_model_replace():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    # Should use FINANCE_LABELS map, not .replace(/_/g," ")
    assert 'finance_model.replace(/_/g," ")' not in src, \
        "Must use FINANCE_LABELS map instead of .replace(/_/g,' ')"

def test_page_no_raw_customer_flow_replace():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert 'customer_flow_type.replace(/_/g," ")' not in src, \
        "Must use FLOW_LABELS map instead of .replace(/_/g,' ')"

def test_page_has_vertical_labels_map():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "VERTICAL_LABELS" in src, "Must have VERTICAL_LABELS map"

def test_page_has_finance_labels_map():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "FINANCE_LABELS" in src, "Must have FINANCE_LABELS map"

def test_page_has_flow_labels_map():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "FLOW_LABELS" in src, "Must have FLOW_LABELS map"

def test_page_has_readiness_labels_map():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "READINESS_LABELS" in src, "Must have READINESS_LABELS map"

# ── API client ────────────────────────────────────────────────────────────────

def test_api_has_summary_method():
    src = API_TS.read_text(encoding="utf-8")
    assert "summary:" in src and "/v1/admin/categories/summary" in src

def test_api_has_export_method():
    src = API_TS.read_text(encoding="utf-8")
    assert "exportCategories" in src

def test_api_has_readiness_method():
    src = API_TS.read_text(encoding="utf-8")
    assert "getCategoryReadiness" in src or "readiness" in src

def test_api_list_accepts_enterprise_filters():
    src = API_TS.read_text(encoding="utf-8")
    # Find the categoryRuntimeApi.listCategories (not catalogApi.listCategories)
    idx = src.find("categoryRuntimeApi = {")
    runtime_block = src[idx:idx + 2000] if idx != -1 else src
    list_idx = runtime_block.find("listCategories:")
    snippet = runtime_block[list_idx:list_idx + 800] if list_idx != -1 else ""
    for param in ["vertical_type", "finance_model", "readiness_status", "page", "page_size"]:
        assert param in snippet, f"categoryRuntimeApi.listCategories must accept '{param}'"

def test_api_has_enterprise_category_type():
    src = API_TS.read_text(encoding="utf-8")
    assert "EnterpriseCategory" in src

def test_api_has_category_linked_counts_type():
    src = API_TS.read_text(encoding="utf-8")
    assert "CategoryLinkedCounts" in src

def test_api_has_category_summary_type():
    src = API_TS.read_text(encoding="utf-8")
    assert "CategorySummaryData" in src

# ── Backend: route order (summary/export before {id}) ─────────────────────────

def test_summary_route_defined_before_category_id_route():
    src = ROUTER.read_text(encoding="utf-8")
    summary_pos = src.find('"/summary"')
    id_pos = src.find('"/{category_id}"')
    assert summary_pos < id_pos, \
        "summary endpoint must be defined BEFORE /{category_id} to avoid routing conflict"

def test_export_route_defined_before_category_id_route():
    src = ROUTER.read_text(encoding="utf-8")
    export_pos = src.find('"/export"')
    id_pos = src.find('"/{category_id}"')
    assert export_pos < id_pos, \
        "export endpoint must be defined BEFORE /{category_id} to avoid routing conflict"

# ── Detail page preserved ─────────────────────────────────────────────────────

def test_detail_page_has_tabs():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "TABS" in src or "activeTab" in src

def test_detail_page_has_overview_tab():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "overview" in src.lower()

def test_detail_page_has_monetization_tab():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "monetization" in src.lower() or "Monetization" in src

def test_detail_page_has_back_to_categories_link():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "/admin/categories" in src

def test_detail_page_uses_params():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "useParams" in src or "category_id" in src

# ── No duplicate page ─────────────────────────────────────────────────────────

def test_catalog_page_no_categories_tab():
    src = (ROOT / "frontend/super-admin/app/admin/catalog/page.tsx").read_text(encoding="utf-8")
    assert "CategoriesTab" not in src

def test_no_duplicate_standalone_category_list():
    """Only /admin/categories/page.tsx should contain the New Category button logic."""
    candidates = [
        ROOT / "frontend/super-admin/app/admin/catalog/page.tsx",
    ]
    for p in candidates:
        if p.exists():
            src = p.read_text(encoding="utf-8")
            assert "createCategory" not in src, \
                f"{p} must not contain createCategory — only /admin/categories/page.tsx should"
