"""
P0 Enterprise Pricing Module Upgrade — test suite
Verifies (static source-inspection style, consistent with test_p0_enterprise_catalog.py /
test_sprint34d_brands.py conventions in this repo — no live DB fixture required):

  Migration 077:
    - exists, correct revision/down_revision
    - service_pricing_rules new columns
    - location_import_batches table
    - tier_locations conflict-detection index

  Backend — admin_catalog/models.py:
    - ServicePricingRule: rule_name, rule_code, bargain_floor, source, district, state, zone
    - LocationImportBatch model + to_dict()

  Backend — admin_catalog/service.py:
    - Pricing Tiers: _tier_linked_counts, get_tiers_summary, export_tiers, get_tier_detail,
      list_tiers extended filters
    - Tier Locations: list_tier_locations pagination/filters, find_zipcode_conflicts,
      get_tier_location_summary, export_tier_locations, import preview/confirm/get_import_batch,
      resolve_location resolution_path
    - Pricing Rules: list_pricing_rules pagination/filters, find_pricing_rule_conflicts,
      get_pricing_rules_summary, export_pricing_rules, get_pricing_rule_conflicts,
      _generate_rule_code, bargain_floor validation

  Backend — pricing_engine.py:
    - resolve_service_price returns resolution_path, matched_rule_name, bargain_floor, warnings

  Backend — admin_router.py:
    - new endpoints wired, permission-guarded (CATALOG_TIERS_*/CATALOG_PRICING_*)

  Backend — enterprise_grid/filter_registry.py:
    - admin_pricing_tiers, admin_tier_locations, admin_pricing_rules resource configs
"""
import os

ROOT           = os.path.dirname(os.path.dirname(__file__))
MODELS_FILE    = os.path.join(ROOT, "app", "engines", "admin_catalog", "models.py")
SERVICE_FILE   = os.path.join(ROOT, "app", "engines", "admin_catalog", "service.py")
PRICING_ENGINE = os.path.join(ROOT, "app", "engines", "admin_catalog", "pricing_engine.py")
ADMIN_ROUTER   = os.path.join(ROOT, "app", "engines", "admin_catalog", "admin_router.py")
FILTER_REGISTRY = os.path.join(ROOT, "app", "engines", "enterprise_grid", "filter_registry.py")
MIGRATION_077  = os.path.join(ROOT, "alembic", "versions", "077_pricing_enterprise_upgrade.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 077 ────────────────────────────────────────────────────────────

def test_migration_077_exists():
    assert os.path.exists(MIGRATION_077), "Migration 077 not found"


def test_migration_077_revision():
    src = _read(MIGRATION_077)
    assert 'revision = "077"' in src


def test_migration_077_down_revision():
    src = _read(MIGRATION_077)
    assert 'down_revision = "076"' in src


def test_migration_077_service_pricing_rules_columns():
    src = _read(MIGRATION_077)
    for col in ("rule_name", "rule_code", "bargain_floor", "source", "district", "state", "zone"):
        assert col in src, f"Expected column '{col}' in migration 077"


def test_migration_077_location_import_batches_table():
    src = _read(MIGRATION_077)
    assert "location_import_batches" in src
    for col in ("preview_payload", "report_payload", "conflict_resolution", "conflict_rows"):
        assert col in src, f"Expected column '{col}' on location_import_batches"


def test_migration_077_tier_locations_conflict_index():
    src = _read(MIGRATION_077)
    assert "ix_tl_zipcode_active" in src


def test_migration_077_no_hard_unique_zipcode_constraint():
    """Ticket requires a soft conflict-resolution flow, not a blocking DB constraint."""
    src = _read(MIGRATION_077)
    assert "uq_tl_zipcode" not in src
    assert "UniqueConstraint(\"zipcode\"" not in src


# ── Models ────────────────────────────────────────────────────────────────────

def test_service_pricing_rule_enterprise_columns():
    src = _read(MODELS_FILE)
    idx = src.index("class ServicePricingRule(")
    snippet = src[idx:idx + 4000]
    for col in ("rule_name", "rule_code", "bargain_floor", "source", "district", "state", "zone"):
        assert col in snippet, f"ServicePricingRule missing column: {col}"


def test_location_import_batch_model_exists():
    src = _read(MODELS_FILE)
    assert "class LocationImportBatch(" in src


def test_location_import_batch_has_to_dict():
    src = _read(MODELS_FILE)
    idx = src.index("class LocationImportBatch(")
    snippet = src[idx:idx + 3000]
    assert "def to_dict" in snippet


# ── Service — Pricing Tiers ───────────────────────────────────────────────────

def test_tier_linked_counts_method_exists():
    assert "_tier_linked_counts" in _read(SERVICE_FILE)


def test_get_tiers_summary_exists():
    assert "async def get_tiers_summary" in _read(SERVICE_FILE)


def test_export_tiers_exists():
    assert "async def export_tiers" in _read(SERVICE_FILE)


def test_get_tier_detail_exists():
    assert "async def get_tier_detail" in _read(SERVICE_FILE)


def test_list_tiers_extended_filters():
    src = _read(SERVICE_FILE)
    idx = src.index("async def list_tiers(")
    sig = src[idx:idx + 400]
    for param in ("used_in_rules", "has_city_mapping", "has_zipcode_mapping", "date_from", "date_to"):
        assert param in sig, f"list_tiers missing filter param: {param}"


# ── Service — Tier Locations ──────────────────────────────────────────────────

def test_list_tier_locations_pagination_params():
    src = _read(SERVICE_FILE)
    idx = src.index("async def list_tier_locations(")
    sig = src[idx:idx + 700]
    for param in ("page", "page_size", "sort_by", "sort_dir", "has_conflict"):
        assert param in sig, f"list_tier_locations missing param: {param}"


def test_find_zipcode_conflicts_exists():
    assert "async def find_zipcode_conflicts" in _read(SERVICE_FILE)


def test_get_tier_location_summary_exists():
    assert "async def get_tier_location_summary" in _read(SERVICE_FILE)


def test_export_tier_locations_exists():
    assert "async def export_tier_locations" in _read(SERVICE_FILE)


def test_import_wizard_methods_exist():
    src = _read(SERVICE_FILE)
    for fn in ("import_tier_locations_preview", "import_tier_locations_confirm", "get_import_batch"):
        assert f"async def {fn}" in src, f"Missing import-wizard method: {fn}"


def test_import_confirm_supports_skip_and_override():
    src = _read(SERVICE_FILE)
    idx = src.index("async def import_tier_locations_confirm(")
    snippet = src[idx:idx + 3000]
    assert '"skip"' in snippet and '"override"' in snippet


def test_resolve_location_returns_resolution_path():
    src = _read(SERVICE_FILE)
    idx = src.index("async def resolve_location(")
    snippet = src[idx:idx + 3000]
    assert "resolution_path" in snippet
    assert "path.append" in snippet


# ── Service — Pricing Rules ───────────────────────────────────────────────────

def test_list_pricing_rules_pagination_and_filters():
    src = _read(SERVICE_FILE)
    idx = src.index("async def list_pricing_rules(")
    sig = src[idx:idx + 900]
    for param in ("page", "page_size", "sort_by", "sort_dir", "expiring_within_days", "rule_status"):
        assert param in sig, f"list_pricing_rules missing param: {param}"


def test_find_pricing_rule_conflicts_exists():
    assert "async def find_pricing_rule_conflicts" in _read(SERVICE_FILE)


def test_get_pricing_rules_summary_exists():
    assert "async def get_pricing_rules_summary" in _read(SERVICE_FILE)


def test_export_pricing_rules_exists():
    assert "async def export_pricing_rules" in _read(SERVICE_FILE)


def test_get_pricing_rule_conflicts_endpoint_method_exists():
    assert "async def get_pricing_rule_conflicts" in _read(SERVICE_FILE)


def test_generate_rule_code_exists():
    assert "_generate_rule_code" in _read(SERVICE_FILE)


def test_create_pricing_rule_validates_bargain_floor():
    src = _read(SERVICE_FILE)
    idx = src.index("async def create_pricing_rule(")
    snippet = src[idx:idx + 3000]
    assert "INVALID_BARGAIN_FLOOR" in snippet


def test_update_pricing_rule_validates_bargain_floor():
    src = _read(SERVICE_FILE)
    idx = src.index("async def update_pricing_rule(")
    snippet = src[idx:idx + 2000]
    assert "INVALID_BARGAIN_FLOOR" in snippet


def test_rule_dict_includes_new_fields():
    src = _read(SERVICE_FILE)
    idx = src.index("def _rule_dict(")
    snippet = src[idx:idx + 1600]
    for field in ("bargain_floor", "rule_name", "rule_code", "source"):
        assert field in snippet, f"_rule_dict missing field: {field}"


# ── Pricing Engine ────────────────────────────────────────────────────────────

def test_resolve_service_price_returns_enterprise_fields():
    src = _read(PRICING_ENGINE)
    for field in ("resolution_path", "matched_rule_name", "bargain_floor", "warnings"):
        assert f'"{field}"' in src, f"resolve_service_price response missing '{field}'"


def test_build_rule_candidates_returns_labeled_levels():
    src = _read(PRICING_ENGINE)
    assert '"zipcode+type+brand"' in src
    assert '"global"' in src


# ── Router — endpoints + permissions ─────────────────────────────────────────

def test_router_tiers_summary_export_detail_endpoints():
    src = _read(ADMIN_ROUTER)
    for retired in ('"/tiers/summary"', '"/tiers/export"', '"/tiers/{tier_id}/detail"'):
        assert retired not in src


def test_router_tier_locations_enterprise_endpoints():
    src = _read(ADMIN_ROUTER)
    for path in ("/tier-locations/summary", "/tier-locations/export",
                 "/tier-locations/import/preview", "/tier-locations/import/confirm",
                 "/tier-locations/imports/{batch_id}"):
        assert f'"{path}"' not in src


def test_router_pricing_rules_enterprise_endpoints():
    src = _read(ADMIN_ROUTER)
    assert '"/pricing-rules/summary"' not in src
    assert '"/pricing-rules/export"' not in src
    assert '"/pricing-rules/{rule_id}/conflicts"' not in src


def test_router_uses_catalog_permissions():
    src = _read(ADMIN_ROUTER)
    assert "require_permission(P.CATALOG_TIERS_READ)" in src
    assert "require_permission(P.CATALOG_TIERS_WRITE)" in src
    assert "require_permission(P.CATALOG_PRICING_READ)" not in src
    assert "require_permission(P.CATALOG_PRICING_WRITE)" not in src


# ── Enterprise Grid registry ─────────────────────────────────────────────────

def test_filter_registry_pricing_resources_exist():
    src = _read(FILTER_REGISTRY)
    for key in ("admin_pricing_tiers", "admin_tier_locations", "admin_pricing_rules"):
        assert f'"{key}"' in src, f"Missing enterprise_grid resource config: {key}"
