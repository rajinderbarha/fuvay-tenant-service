"""
P0 Category Engine Matrix Completion Sprint — backend + frontend tests.
Migration 082 | category_engine_matrix governance fields | 14 new endpoints |
categories/options dropdown | seed templates | enable/disable preview + workflow |
tenant impact + runtime policy | audit logging.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


MIGRATION      = ROOT / "alembic" / "versions" / "082_category_engine_matrix_governance.py"
MODELS         = ROOT / "app" / "engines" / "engine_mgmt" / "models.py"
SERVICE        = ROOT / "app" / "engines" / "engine_mgmt" / "service.py"
ROUTER         = ROOT / "app" / "engines" / "engine_mgmt" / "admin_router.py"
CATALOG_ROUTER = ROOT / "app" / "engines" / "admin_catalog" / "admin_router.py"
SEED_SCRIPT    = ROOT / "scripts" / "seed_universal_categories.py"
API_TS         = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
ENGINES_PAGE   = ROOT / "frontend" / "super-admin" / "app" / "admin" / "engines" / "page.tsx"


# ════════════════════════════════════════════════════════════════════════════
# Migration 082
# ════════════════════════════════════════════════════════════════════════════
class TestMigration082:
    def test_migration_file_exists(self):
        assert MIGRATION.exists()

    def test_revision(self):
        assert 'revision = "082"' in _read(MIGRATION)

    def test_down_revision(self):
        assert 'down_revision = "081"' in _read(MIGRATION)

    def test_recommendation_status_column(self):
        assert "recommendation_status" in _read(MIGRATION)

    def test_dependency_status_column(self):
        assert "dependency_status" in _read(MIGRATION)

    def test_runtime_risk_column(self):
        assert "runtime_risk" in _read(MIGRATION)

    def test_status_column(self):
        assert '"status"' in _read(MIGRATION)

    def test_created_by_user_id_column(self):
        assert "created_by_user_id" in _read(MIGRATION)

    def test_updated_by_user_id_column(self):
        assert "updated_by_user_id" in _read(MIGRATION)

    def test_downgrade_exists(self):
        assert "def downgrade" in _read(MIGRATION)


# ════════════════════════════════════════════════════════════════════════════
# Model fields
# ════════════════════════════════════════════════════════════════════════════
class TestCategoryEngineMatrixModel:
    def test_model_file_exists(self):
        assert MODELS.exists()

    def test_recommendation_status_field(self):
        assert "recommendation_status" in _read(MODELS)

    def test_dependency_status_field(self):
        assert "dependency_status" in _read(MODELS)

    def test_runtime_risk_field(self):
        assert "runtime_risk" in _read(MODELS)

    def test_created_by_user_id_field(self):
        assert "created_by_user_id" in _read(MODELS)

    def test_updated_by_user_id_field(self):
        assert "updated_by_user_id" in _read(MODELS)

    def test_unique_constraint_category_engine(self):
        assert 'uq_cat_engine' in _read(MODELS)


# ════════════════════════════════════════════════════════════════════════════
# Service — Category Matrix Governance
# ════════════════════════════════════════════════════════════════════════════
class TestCategoryMatrixService:
    def test_service_file_exists(self):
        assert SERVICE.exists()

    def test_templates_dict_exists(self):
        assert "CATEGORY_ENGINE_TEMPLATES" in _read(SERVICE)

    def test_home_services_template(self):
        assert "home_services_default" in _read(SERVICE)

    def test_real_estate_template(self):
        assert "real_estate_default" in _read(SERVICE)

    def test_restaurant_template(self):
        assert "restaurant_default" in _read(SERVICE)

    def test_coaching_template(self):
        assert "coaching_default" in _read(SERVICE)

    def test_professional_services_template(self):
        assert "professional_services_default" in _read(SERVICE)

    def test_marketplace_products_template(self):
        assert "marketplace_products_default" in _read(SERVICE)

    def test_get_category_matrix_for_category(self):
        assert "get_category_matrix_for_category" in _read(SERVICE)

    def test_get_category_matrix_summary(self):
        assert "get_category_matrix_summary" in _read(SERVICE)

    def test_seed_defaults_preview(self):
        assert "seed_defaults_preview" in _read(SERVICE)

    def test_seed_defaults(self):
        assert "def seed_defaults" in _read(SERVICE)

    def test_category_engine_action_preview(self):
        assert "category_engine_action_preview" in _read(SERVICE)

    def test_enable_category_engine(self):
        assert "async def enable_category_engine" in _read(SERVICE)

    def test_disable_category_engine(self):
        assert "async def disable_category_engine" in _read(SERVICE)

    def test_disable_blocks_required_engine_with_active_tenants(self):
        src = _read(SERVICE)
        assert "is_required and tenant_count > 0" in src

    def test_mark_category_engine_required(self):
        assert "mark_category_engine_required" in _read(SERVICE)

    def test_mark_category_engine_optional(self):
        assert "mark_category_engine_optional" in _read(SERVICE)

    def test_tenant_impact_method(self):
        assert "get_category_engine_tenant_impact" in _read(SERVICE)

    def test_dependency_status_computation(self):
        assert "_compute_dependency_status" in _read(SERVICE)

    def test_audit_events_present(self):
        src = _read(SERVICE)
        for event in [
            "engine.category_matrix.seeded",
            "engine.category_matrix.enabled",
            "engine.category_matrix.disabled",
            "engine.category_matrix.marked_required",
            "engine.category_matrix.marked_optional",
            "engine.category_matrix.validation_failed",
        ]:
            assert event in src, f"Missing audit event: {event}"

    def test_seed_preview_does_not_mutate(self):
        src = _read(SERVICE)
        # preview function must not call db.add / db.commit
        start = src.index("async def seed_defaults_preview")
        end = src.index("async def seed_defaults(")
        body = src[start:end]
        assert "self.db.add(" not in body
        assert "self.db.commit()" not in body


# ════════════════════════════════════════════════════════════════════════════
# Admin Router — Category Matrix endpoints
# ════════════════════════════════════════════════════════════════════════════
class TestCategoryMatrixRouter:
    def test_router_file_exists(self):
        assert ROUTER.exists()

    def test_matrix_detail_route(self):
        assert '"/category-matrix/{category_id}"' in _read(ROUTER)

    def test_matrix_summary_route(self):
        assert '"/category-matrix/{category_id}/summary"' in _read(ROUTER)

    def test_seed_preview_route(self):
        assert '"/category-matrix/{category_id}/seed-defaults/preview"' in _read(ROUTER)

    def test_seed_apply_route(self):
        assert '"/category-matrix/{category_id}/seed-defaults"' in _read(ROUTER)

    def test_enable_preview_route(self):
        assert "enable-preview" in _read(ROUTER)

    def test_disable_preview_route(self):
        assert "disable-preview" in _read(ROUTER)

    def test_mark_optional_route(self):
        assert "mark-optional" in _read(ROUTER)

    def test_tenant_impact_route(self):
        assert '"/category-matrix/{category_id}/engines/{engine_key}/tenant-impact"' in _read(ROUTER)

    def test_export_route(self):
        assert '"/category-matrix/export"' in _read(ROUTER)

    def test_export_route_before_detail_route(self):
        """Route ordering: /export must be registered before /{category_id} to avoid UUID-parse shadowing."""
        src = _read(ROUTER)
        export_pos = src.index('"/category-matrix/export"')
        detail_pos = src.index('"/category-matrix/{category_id}"')
        assert export_pos < detail_pos

    def test_all_routes_require_super_admin(self):
        src = _read(ROUTER)
        start = src.index('"/category-matrix/{category_id}"')
        end = src.index("# ── Dependencies")
        section = src[start:end]
        assert section.count("require_super_admin") >= 10


# ════════════════════════════════════════════════════════════════════════════
# Categories Options dropdown endpoint
# ════════════════════════════════════════════════════════════════════════════
class TestCategoryOptionsEndpoint:
    def test_catalog_router_file_exists(self):
        assert CATALOG_ROUTER.exists()

    def test_options_route_exists(self):
        assert '"/catalog/categories/options"' in _read(CATALOG_ROUTER)

    def test_options_supports_search(self):
        src = _read(CATALOG_ROUTER)
        start = src.index('"/catalog/categories/options"')
        section = src[start:start + 1500]
        assert "q: str | None" in section

    def test_options_supports_vertical_filter(self):
        src = _read(CATALOG_ROUTER)
        start = src.index('"/catalog/categories/options"')
        section = src[start:start + 1500]
        assert "vertical_type" in section

    def test_options_returns_no_raw_uuid_requirement(self):
        """The options endpoint returns name/slug/vertical_type — not just IDs — for a searchable UI."""
        src = _read(CATALOG_ROUTER)
        start = src.index('"/catalog/categories/options"')
        section = src[start:start + 1500]
        assert '"name": c.name' in section
        assert '"vertical_type": c.vertical_type' in section


# ════════════════════════════════════════════════════════════════════════════
# Seed script (categories exist so matrix isn't permanently empty)
# ════════════════════════════════════════════════════════════════════════════
class TestCategorySeedData:
    def test_seed_script_exists(self):
        assert SEED_SCRIPT.exists()

    def test_home_services_seeded(self):
        assert '"slug": "home_services"' in _read(SEED_SCRIPT)

    def test_idempotent_by_slug(self):
        assert "slug == slug" in _read(SEED_SCRIPT) or "ServiceCategory.slug == slug" in _read(SEED_SCRIPT)


# ════════════════════════════════════════════════════════════════════════════
# Frontend — api.ts client methods
# ════════════════════════════════════════════════════════════════════════════
class TestFrontendApiClient:
    def test_api_file_exists(self):
        assert API_TS.exists()

    def test_get_category_matrix_detail_method(self):
        assert "getCategoryMatrixDetail" in _read(API_TS) or "category-matrix/${" in _read(API_TS)

    def test_seed_defaults_methods_exist(self):
        src = _read(API_TS)
        assert "seedCategoryDefaults" in src or "seed-defaults" in src

    def test_category_options_method(self):
        src = _read(API_TS)
        assert "categoryOptions" in src or "categories/options" in src

    def test_no_raw_category_id_input_in_page(self):
        """Regression guard: raw 'Filter by category ID' text input must not reappear."""
        src = _read(ENGINES_PAGE)
        assert "Filter by category ID" not in src


# ════════════════════════════════════════════════════════════════════════════
# Frontend — Category Matrix tab UI elements
# ════════════════════════════════════════════════════════════════════════════
class TestFrontendCategoryMatrixOwnership:
    def test_engines_page_exists(self):
        assert ENGINES_PAGE.exists()

    def test_category_matrix_is_not_duplicated_in_engine_console(self):
        src = _read(ENGINES_PAGE)
        assert "CategorySelector" not in src
        assert '"category-matrix": "verticals"' in src

    def test_vertical_usage_replaces_package_matrix(self):
        src = _read(ENGINES_PAGE)
        assert "getVerticalUsage" in src
        assert "Vertical usage" in src

    def test_runtime_summary_cards_present(self):
        src = _read(ENGINES_PAGE)
        assert "function Metric" in src

    def test_labeled_actions_not_icon_only(self):
        src = _read(ENGINES_PAGE)
        assert "Manage vertical" in src and "Inspect" in src
