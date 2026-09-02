"""
P0 Enterprise Platform Settings + System Configuration Center Upgrade — test suite
Static source-inspection style, consistent with test_p0_security_enterprise.py /
test_p0_customers_enterprise.py conventions in this repo — no live DB fixture required.
"""
import os

ROOT           = os.path.dirname(os.path.dirname(__file__))
MODELS         = os.path.join(ROOT, "app", "engines", "settings_engine", "models.py")
SERVICE        = os.path.join(ROOT, "app", "engines", "settings_engine", "service.py")
SEED_DATA      = os.path.join(ROOT, "app", "engines", "settings_engine", "seed_data.py")
ADMIN_ROUTER   = os.path.join(ROOT, "app", "engines", "settings_engine", "admin_router.py")
PERMISSIONS    = os.path.join(ROOT, "app", "core", "permissions.py")
FILTER_REGISTRY = os.path.join(ROOT, "app", "engines", "enterprise_grid", "filter_registry.py")
MAIN_PY        = os.path.join(ROOT, "app", "main.py")
MIGRATION_088  = os.path.join(ROOT, "alembic", "versions", "088_settings_enterprise_upgrade.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 088 ────────────────────────────────────────────────────────────

def test_migration_088_exists():
    assert os.path.exists(MIGRATION_088)


def test_migration_088_revision_chain():
    src = _read(MIGRATION_088)
    assert 'revision = "088"' in src
    assert 'down_revision = "087"' in src


def test_migration_088_platform_settings_metadata_columns():
    src = _read(MIGRATION_088)
    for col in ("label", "category", "allowed_values_json", "is_secret", "risk_level",
                "requires_approval", "requires_restart", "is_runtime_editable",
                "owner_module", "status"):
        assert col in src


def test_migration_088_tenant_settings_columns():
    src = _read(MIGRATION_088)
    assert "expires_at" in src
    assert "requires_approval" in src


def test_migration_088_setting_audit_logs_columns():
    src = _read(MIGRATION_088)
    assert "request_id" in src
    assert "action_type" in src


def test_migration_088_creates_feature_flags_table():
    src = _read(MIGRATION_088)
    assert '"feature_flags"' in src
    assert "flag_key" in src
    assert "rollout_type" in src


# ── models.py ─────────────────────────────────────────────────────────────────

def test_models_importable():
    import importlib
    mod = importlib.import_module("app.engines.settings_engine.models")
    assert hasattr(mod, "FeatureFlag")


def test_platform_setting_has_metadata_fields():
    src = _read(MODELS)
    for field in ("category:", "is_secret:", "risk_level:", "requires_approval:",
                  "requires_restart:", "is_runtime_editable:", "owner_module:"):
        assert field in src


def test_feature_flag_model_exists():
    src = _read(MODELS)
    assert "class FeatureFlag(" in src
    assert "def to_dict(self)" in src


# ── seed_data.py ──────────────────────────────────────────────────────────────

def test_seed_data_importable():
    from app.engines.settings_engine.seed_data import SERVICEOS_DEFAULT_SETTINGS, SETTING_KEYS
    assert len(SERVICEOS_DEFAULT_SETTINGS) >= 80
    assert len(SETTING_KEYS) == len(SERVICEOS_DEFAULT_SETTINGS)


def test_seed_data_covers_home_services_business_rules():
    from app.engines.settings_engine.seed_data import SERVICEOS_DEFAULT_SETTINGS
    by_key = {s["key"]: s for s in SERVICEOS_DEFAULT_SETTINGS}
    assert by_key["payment_collection_enabled"]["value"] is False
    assert by_key["tenant_payouts_enabled"]["value"] is False
    assert by_key["provider_usage_credits_enabled"]["value"] is True
    assert by_key["usage_credit_is_cash_wallet"]["value"] is False
    assert by_key["usage_credit_is_withdrawable"]["value"] is False
    assert by_key["customer_service_credits_enabled"]["value"] is True
    assert by_key["customer_service_credit_is_cash_refund"]["value"] is False
    assert "security_deposit_enabled" not in by_key
    assert by_key["customer_pays_provider_directly"]["value"] is True


def test_seed_data_ai_rule_backend_is_source_of_truth():
    from app.engines.settings_engine.seed_data import SERVICEOS_DEFAULT_SETTINGS
    by_key = {s["key"]: s for s in SERVICEOS_DEFAULT_SETTINGS}
    assert by_key["llm_can_invent_prices"]["value"] is False
    assert by_key["llm_can_create_services"]["value"] is False
    assert by_key["backend_is_source_of_truth"]["value"] is True


def test_seed_data_no_duplicate_keys():
    from app.engines.settings_engine.seed_data import SETTING_KEYS
    assert len(SETTING_KEYS) == len(set(SETTING_KEYS))


# ── service.py ────────────────────────────────────────────────────────────────

def test_service_importable():
    import importlib
    mod = importlib.import_module("app.engines.settings_engine.service")
    assert hasattr(mod, "SettingsService")


def test_service_has_seed_defaults():
    src = _read(SERVICE)
    assert "async def seed_defaults" in src


def test_service_has_impact_preview():
    src = _read(SERVICE)
    assert "async def check_impact" in src


def test_service_impact_rule_blocks_tenant_payouts_without_payment_collection():
    src = _read(SERVICE)
    assert "tenant_payouts_enabled" in src
    assert "payment_collection_enabled" in src
    assert "IMPACT_RULES" in src


def test_service_has_rollback():
    src = _read(SERVICE)
    assert "async def rollback_setting" in src
    # Rollback must create a new audit entry, never delete history
    assert "self.db.delete" not in src.split("async def rollback_setting")[1].split("async def")[0]


def test_service_rollback_blocks_secrets():
    src = _read(SERVICE)
    body = src.split("async def rollback_setting")[1].split("async def")[0]
    assert "is_secret" in body


def test_service_has_feature_flag_methods():
    src = _read(SERVICE)
    for m in ("list_feature_flags", "create_feature_flag", "update_feature_flag", "set_feature_flag_status"):
        assert f"async def {m}" in src


def test_service_has_resolve_effective_value():
    src = _read(SERVICE)
    assert "async def resolve_effective_value" in src


def test_service_has_summary():
    src = _read(SERVICE)
    assert "async def get_summary" in src


def test_service_masks_secrets_in_reads():
    src = _read(SERVICE)
    assert "MASKED_VALUE" in src
    assert "is_secret else" in src


def test_service_masks_secrets_in_write_response():
    """create/update responses must not echo the raw secret value back."""
    src = _read(SERVICE)
    body = src.split("async def set_platform_setting")[1].split("async def delete_platform_setting")[0]
    assert "effective_is_secret" in body
    assert "response_value" in body


def test_service_critical_settings_require_reason():
    src = _read(SERVICE)
    body = src.split("async def set_platform_setting")[1].split("async def delete_platform_setting")[0]
    assert 'risk_level == "critical" and not reason' in body


def test_service_tenant_override_requires_reason():
    src = _read(SERVICE)
    body = src.split("async def set_tenant_setting")[1].split("async def delete_tenant_setting")[0]
    assert "A reason is required to create a tenant override" in body


# ── admin_router.py ──────────────────────────────────────────────────────────

def test_admin_router_importable():
    import importlib
    mod = importlib.import_module("app.engines.settings_engine.admin_router")
    assert hasattr(mod, "router")


def test_admin_router_prefix():
    src = _read(ADMIN_ROUTER)
    assert '/v1/admin/settings' in src


def test_admin_router_endpoints_present():
    src = _read(ADMIN_ROUTER)
    for path in ('"/summary"', '"/seed-defaults/preview"', '"/seed-defaults"',
                 '"/groups"', '"/{setting_key}"', '"/{setting_key}/enable"',
                 '"/{setting_key}/disable"', '"/{setting_key}/impact-preview"',
                 '"/{setting_key}/rollback"', '"/{setting_key}/history"',
                 '"/resolve-effective-value"',
                 '"/categories"', '"/categories/{category_id}"',
                 '"/tenant-overrides"', '"/tenant-overrides/{override_id}"',
                 '"/tenant-overrides/{override_id}/revoke"',
                 '"/feature-flags"', '"/feature-flags/{flag_id}"',
                 '"/feature-flags/{flag_id}/enable"', '"/feature-flags/{flag_id}/disable"',
                 '"/audit-logs"'):
        assert path in src, f"missing route {path}"


def test_admin_router_catchall_setting_key_registered_last():
    """GET /{setting_key} must be the LAST route registered, or it swallows every
    literal-path GET above it (a real bug found live: /plans, /categories,
    /tenant-overrides, /feature-flags, /audit-logs, /groups all 404'd until fixed)."""
    src = _read(ADMIN_ROUTER)
    last_catchall_pos = src.rfind('@router.get("/{setting_key}"')
    for literal in ('@router.get("/audit-logs"', '@router.get("/feature-flags"',
                    '@router.get("/tenant-overrides"', '@router.get("/categories"',
                    '@router.get("/groups"'):
        assert src.find(literal) < last_catchall_pos, f"{literal} must be registered before the catch-all"


def test_admin_router_permission_guarded():
    src = _read(ADMIN_ROUTER)
    for perm in ("P.SETTINGS_READ", "P.SETTINGS_CREATE", "P.SETTINGS_UPDATE",
                 "P.SETTINGS_ENABLE", "P.SETTINGS_DISABLE", "P.SETTINGS_IMPACT_PREVIEW",
                 "P.SETTINGS_ROLLBACK", "P.SETTINGS_SEED_DEFAULTS",
                 "P.SETTINGS_CATEGORY_READ", "P.SETTINGS_CATEGORY_UPDATE",
                 "P.SETTINGS_TENANT_OVERRIDES_READ", "P.SETTINGS_TENANT_OVERRIDES_CREATE",
                 "P.SETTINGS_TENANT_OVERRIDES_REVOKE", "P.SETTINGS_FEATURE_FLAGS_READ",
                 "P.SETTINGS_FEATURE_FLAGS_UPDATE", "P.SETTINGS_AUDIT_READ", "P.SETTINGS_HISTORY_READ"):
        assert perm in src


def test_admin_router_registered_in_main():
    src = _read(MAIN_PY)
    assert "settings_engine.admin_router" in src
    assert "settings_admin_router" in src


# ── permissions.py ───────────────────────────────────────────────────────────

def test_permissions_settings_constants_exist():
    src = _read(PERMISSIONS)
    for const in ("SETTINGS_CREATE", "SETTINGS_UPDATE", "SETTINGS_DELETE", "SETTINGS_ENABLE",
                  "SETTINGS_DISABLE", "SETTINGS_IMPACT_PREVIEW", "SETTINGS_ROLLBACK",
                  "SETTINGS_SEED_DEFAULTS", "SETTINGS_IMPORT", "SETTINGS_EXPORT",
                  "SETTINGS_CATEGORY_READ", "SETTINGS_CATEGORY_UPDATE", "SETTINGS_TENANT_OVERRIDES_READ",
                  "SETTINGS_TENANT_OVERRIDES_CREATE", "SETTINGS_TENANT_OVERRIDES_REVOKE",
                  "SETTINGS_FEATURE_FLAGS_READ", "SETTINGS_FEATURE_FLAGS_UPDATE",
                  "SETTINGS_AUDIT_READ", "SETTINGS_HISTORY_READ"):
        assert const in src


# ── enterprise_grid/filter_registry.py ──────────────────────────────────────

def test_filter_registry_settings_resources_present():
    src = _read(FILTER_REGISTRY)
    for key in ("admin_settings", "admin_feature_flags", "admin_setting_audit_logs"):
        assert f'"{key}": {{' in src


def test_filter_registry_resource_count_is_current_and_expanded():
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    assert len(EnterpriseFilterRegistry.all_resource_keys()) >= 46
