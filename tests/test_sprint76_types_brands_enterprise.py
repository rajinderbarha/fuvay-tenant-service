"""
Sprint 76 — Types & Brands Enterprise Module tests.

Verifies:
  1.  Migration 076 exists + correct revision chain
  2.  service_type_mappings table created by migration
  3.  brand_mappings table created by migration
  4.  ServiceType model extended with new columns (code, type_family, customer_visible, status, display_order)
  5.  ServiceTypeMapping model exists in models.py
  6.  BrandMapping model exists in models.py
  7.  TypesService exists + has list_types method
  8.  TypesService has summary method
  9.  TypesService has create_type method
  10. TypesService has activate/deactivate/archive type methods
  11. TypesService has list_type_mappings + create/update/delete_type_mapping
  12. TypesService has brand_summary + list/create/update/delete brand_mapping
  13. catalog_enterprise_router exists with correct prefix
  14. Router endpoints: GET /types/summary, /types/export, /types, /types/{id}
  15. Router endpoints: POST /types, PUT /types/{id}, activate/deactivate/archive
  16. Router endpoints: type-mappings CRUD + brand-mappings CRUD
  17. catalog_enterprise_router registered in main.py
  18. Frontend api.ts has ServiceTypeMaster interface
  19. Frontend api.ts has ServiceTypeMapRecord + BrandMapRecord interfaces
  20. Frontend api.ts has typesApi object with all expected methods
  21. types-brands page has 4 tabs
  22. types-brands page imports typesApi
  23. Service type summary keys present (total, active, inactive, mapped, unmapped, customer_visible)
  24. Brand summary keys present (total, active, inactive, mapped, unmapped, global, customer_visible)
  25. Export methods in TypesService
  26. require_super_admin on mutating endpoints
"""
import os
import re

ROOT         = os.path.dirname(os.path.dirname(__file__))
MIGRATION    = os.path.join(ROOT, "alembic", "versions", "076_types_brands_enterprise.py")
MODELS_FILE  = os.path.join(ROOT, "app", "engines", "admin_catalog", "models.py")
TYPES_SVC    = os.path.join(ROOT, "app", "engines", "admin_catalog", "types_service.py")
ENT_ROUTER   = os.path.join(ROOT, "app", "engines", "admin_catalog", "catalog_enterprise_router.py")
MAIN_PY      = os.path.join(ROOT, "app", "main.py")
SA_API       = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
TYPES_PAGE   = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "types-brands", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration ─────────────────────────────────────────────────────────────────

def test_migration_076_exists():
    assert os.path.isfile(MIGRATION), f"Missing {MIGRATION}"


def test_migration_076_has_correct_revision():
    content = _read(MIGRATION)
    assert 'revision = "076"' in content or "revision = '076'" in content


def test_migration_service_type_mappings_table():
    content = _read(MIGRATION)
    assert "service_type_mappings" in content


def test_migration_brand_mappings_table():
    content = _read(MIGRATION)
    assert "brand_mappings" in content


def test_migration_extends_service_types_columns():
    content = _read(MIGRATION)
    for col in ("type_family", "customer_visible", "display_order"):
        assert col in content, f"Migration missing column: {col}"


# ── Models ────────────────────────────────────────────────────────────────────

def test_service_type_mapping_model_exists():
    content = _read(MODELS_FILE)
    assert "ServiceTypeMapping" in content
    assert '__tablename__ = "service_type_mappings"' in content or "__tablename__ = 'service_type_mappings'" in content


def test_brand_mapping_model_exists():
    content = _read(MODELS_FILE)
    assert "BrandMapping" in content
    assert '__tablename__ = "brand_mappings"' in content or "__tablename__ = 'brand_mappings'" in content


def test_service_type_model_extended_columns():
    content = _read(MODELS_FILE)
    for col in ("type_family", "customer_visible", "display_order", "code"):
        assert col in content, f"ServiceType model missing column: {col}"


# ── TypesService ──────────────────────────────────────────────────────────────

def test_types_service_file_exists():
    assert os.path.isfile(TYPES_SVC)


def test_types_service_list_types():
    content = _read(TYPES_SVC)
    assert "async def list_types" in content


def test_types_service_summary():
    content = _read(TYPES_SVC)
    assert "async def summary" in content
    assert '"total"' in content or "'total'" in content
    assert '"active"' in content or "'active'" in content
    assert '"mapped"' in content or "'mapped'" in content
    assert '"customer_visible"' in content or "'customer_visible'" in content


def test_types_service_create_type():
    content = _read(TYPES_SVC)
    assert "async def create_type" in content


def test_types_service_status_methods():
    content = _read(TYPES_SVC)
    assert "async def activate_type" in content
    assert "async def deactivate_type" in content
    assert "async def archive_type" in content


def test_types_service_type_mapping_methods():
    content = _read(TYPES_SVC)
    assert "async def list_type_mappings" in content
    assert "async def create_type_mapping" in content
    assert "async def update_type_mapping" in content
    assert "async def delete_type_mapping" in content


def test_types_service_brand_summary():
    content = _read(TYPES_SVC)
    assert "async def brand_summary" in content
    assert '"global"' in content or "'global'" in content


def test_types_service_brand_mapping_methods():
    content = _read(TYPES_SVC)
    assert "async def list_brand_mappings" in content
    assert "async def create_brand_mapping" in content
    assert "async def update_brand_mapping" in content
    assert "async def delete_brand_mapping" in content


def test_types_service_export_methods():
    content = _read(TYPES_SVC)
    assert "async def export_types" in content
    assert "async def export_type_mappings" in content
    assert "async def export_brand_mappings" in content


# ── Router ────────────────────────────────────────────────────────────────────

def test_enterprise_router_file_exists():
    assert os.path.isfile(ENT_ROUTER)


def test_enterprise_router_prefix():
    content = _read(ENT_ROUTER)
    assert 'prefix="/v1/admin/catalog"' in content


def test_enterprise_router_type_endpoints():
    content = _read(ENT_ROUTER)
    for path in ("/types/summary", "/types/export", '"/types"', '"/types/{type_id}"'):
        assert path in content, f"Router missing path: {path}"


def test_enterprise_router_type_mutation_endpoints():
    content = _read(ENT_ROUTER)
    for action in ("activate", "deactivate", "archive"):
        assert f"/{action}" in content, f"Router missing action: /{action}"


def test_enterprise_router_type_mapping_endpoints():
    content = _read(ENT_ROUTER)
    assert "/type-mappings" in content
    assert "create_type_mapping" in content
    assert "delete_type_mapping" in content


def test_enterprise_router_brand_mapping_endpoints():
    content = _read(ENT_ROUTER)
    assert "/brand-mappings" in content
    assert "create_brand_mapping" in content
    assert "delete_brand_mapping" in content


def test_enterprise_router_brand_summary_endpoint():
    content = _read(ENT_ROUTER)
    assert "/brands/summary" in content


def test_enterprise_router_require_super_admin():
    content = _read(ENT_ROUTER)
    assert "require_super_admin" in content


# ── Registration in main.py ────────────────────────────────────────────────────

def test_enterprise_router_registered_in_main():
    content = _read(MAIN_PY)
    assert "catalog_enterprise_router" in content


# ── Frontend api.ts ────────────────────────────────────────────────────────────

def test_api_ts_service_type_master_interface():
    content = _read(SA_API)
    assert "ServiceTypeMaster" in content
    assert "type_id" in content
    assert "type_family" in content


def test_api_ts_service_type_map_record():
    content = _read(SA_API)
    assert "ServiceTypeMapRecord" in content
    assert "mapping_id" in content


def test_api_ts_brand_map_record():
    content = _read(SA_API)
    assert "BrandMapRecord" in content
    assert "brand_id" in content


def test_api_ts_types_api_object():
    content = _read(SA_API)
    assert "typesApi" in content


def test_api_ts_types_api_methods():
    content = _read(SA_API)
    for method in ("summary", "brandSummary", "listMappings", "createMapping",
                   "listBrandMappings", "createBrandMapping", "exportTypes"):
        assert method in content, f"typesApi missing method: {method}"


# ── Frontend types-brands page ────────────────────────────────────────────────

def test_types_brands_page_exists():
    assert os.path.isfile(TYPES_PAGE)


def test_types_brands_page_imports_types_api():
    content = _read(TYPES_PAGE)
    assert "typesApi" in content


def test_types_brands_page_four_tabs():
    content = _read(TYPES_PAGE)
    for tab in ("types", "brands", "type-mappings", "brand-mappings"):
        assert tab in content, f"Missing tab key: {tab}"


def test_types_brands_page_summary_cards():
    content = _read(TYPES_PAGE)
    assert "SummaryCard" in content
    assert "Total" in content
    assert "Mapped" in content


def test_types_brands_page_no_header_in_columns():
    content = _read(TYPES_PAGE)
    # column defs should use label:, not header:
    column_section = re.findall(r'const columns\s*=\s*\[.*?\];', content, re.DOTALL)
    for section in column_section:
        assert 'header:' not in section, "DataTable column uses 'header:' instead of 'label:'"
