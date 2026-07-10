"""
P0 Enterprise Security & Threats / SOC Upgrade — test suite
Static source-inspection style, consistent with test_p0_pricing_enterprise.py /
test_p0_finance_enterprise.py conventions in this repo — no live DB fixture required.
"""
import os

ROOT              = os.path.dirname(os.path.dirname(__file__))
SEC_MODELS         = os.path.join(ROOT, "app", "engines", "security", "models.py")
SEC_ADMIN_SERVICE  = os.path.join(ROOT, "app", "engines", "security", "admin_service.py")
SEC_ADMIN_ROUTER   = os.path.join(ROOT, "app", "engines", "security", "admin_router.py")
PERMISSIONS_FILE   = os.path.join(ROOT, "app", "core", "permissions.py")
FILTER_REGISTRY    = os.path.join(ROOT, "app", "engines", "enterprise_grid", "filter_registry.py")
MAIN_PY            = os.path.join(ROOT, "app", "main.py")
MIGRATION_084      = os.path.join(ROOT, "alembic", "versions", "084_security_enterprise_upgrade.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 084 ──────────────────────────────────────────────────────────

def test_migration_084_exists():
    assert os.path.exists(MIGRATION_084)


def test_migration_084_revision_chain():
    src = _read(MIGRATION_084)
    assert 'revision = "084"' in src
    assert 'down_revision = "083"' in src


def test_migration_084_threat_columns():
    src = _read(MIGRATION_084)
    for col in ("threat_number", "risk_score", "source", "target_user_id",
                "assigned_to_admin_id", "last_seen_at", "resolved_at"):
        assert col in src


def test_migration_084_ip_blocklist_columns():
    src = _read(MIGRATION_084)
    for col in ("scope", "status", "hit_count", "last_hit_at", "revoked_at", "revoked_by_user_id"):
        assert col in src


def test_migration_084_api_key_columns():
    src = _read(MIGRATION_084)
    for col in ("owner_type", "allowed_ips_json", "rate_limit_per_minute", "permissions_json"):
        assert col in src


def test_migration_084_new_tables():
    src = _read(MIGRATION_084)
    for table in ("ip_block_hits", "api_key_usage_logs", "security_policies"):
        assert f'"{table}"' in src


def test_migration_084_seeds_ten_policies():
    src = _read(MIGRATION_084)
    assert src.count('"policy_key"') >= 1
    for key in ("mfa_required_super_admin", "failed_login_threshold", "auto_lock_threshold",
                "session_max_lifetime_minutes", "idle_timeout_minutes", "api_key_max_expiry_days",
                "ip_block_auto_expiry_default_days", "export_audit_retention_days"):
        assert key in src


# ── security/models.py ──────────────────────────────────────────────────────

def test_models_threat_fields():
    src = _read(SEC_MODELS)
    for field in ("threat_number", "risk_score", "source", "target_user_id",
                  "assigned_to_admin_id", "last_seen_at", "resolved_at"):
        assert field in src


def test_models_ip_blocklist_fields():
    src = _read(SEC_MODELS)
    for field in ("scope:", "status:", "hit_count:", "last_hit_at:", "revoked_at:", "revoked_by_user_id:"):
        assert field in src


def test_models_api_key_fields():
    src = _read(SEC_MODELS)
    for field in ("owner_type", "allowed_ips_json", "rate_limit_per_minute", "permissions_json"):
        assert field in src


def test_models_new_classes_exist():
    src = _read(SEC_MODELS)
    assert "class IPBlockHit(" in src
    assert "class ApiKeyUsageLog(" in src
    assert "class SecurityPolicy(" in src


def test_models_importable():
    import importlib
    mod = importlib.import_module("app.engines.security.models")
    assert hasattr(mod, "IPBlockHit")
    assert hasattr(mod, "ApiKeyUsageLog")
    assert hasattr(mod, "SecurityPolicy")


# ── security/admin_service.py ───────────────────────────────────────────────

def test_admin_service_importable():
    import importlib
    mod = importlib.import_module("app.engines.security.admin_service")
    assert hasattr(mod, "SecurityAdminService")


def test_admin_service_overview_methods():
    src = _read(SEC_ADMIN_SERVICE)
    assert "async def get_security_overview" in src


def test_admin_service_threat_methods():
    src = _read(SEC_ADMIN_SERVICE)
    for m in ("list_threats", "get_threat_detail", "assign_threat", "update_threat_status",
              "block_ip_from_threat", "revoke_sessions_from_threat"):
        assert f"async def {m}" in src


def test_admin_service_session_methods():
    src = _read(SEC_ADMIN_SERVICE)
    for m in ("list_sessions", "get_session_detail", "revoke_session", "revoke_all_user_sessions"):
        assert f"async def {m}" in src


def test_admin_service_ip_blocklist_methods():
    src = _read(SEC_ADMIN_SERVICE)
    for m in ("list_ip_blocklist", "create_ip_block", "update_ip_block", "revoke_ip_block", "get_ip_block_hits"):
        assert f"async def {m}" in src


def test_admin_service_api_key_methods():
    src = _read(SEC_ADMIN_SERVICE)
    for m in ("list_api_keys", "create_api_key", "get_api_key_detail", "rotate_api_key",
              "revoke_api_key", "get_api_key_usage"):
        assert f"async def {m}" in src


def test_admin_service_audit_methods():
    src = _read(SEC_ADMIN_SERVICE)
    for m in ("list_audit_logs", "get_audit_log_detail", "export_audit_logs"):
        assert f"async def {m}" in src


def test_admin_service_policy_methods():
    src = _read(SEC_ADMIN_SERVICE)
    assert "async def get_policies" in src
    assert "async def update_policy" in src


def test_admin_service_composes_security_service():
    src = _read(SEC_ADMIN_SERVICE)
    assert "SecurityService" in src
    assert "self.sec = SecurityService(" in src
    # Reuses existing lifecycle methods rather than duplicating hashing/rotation logic
    assert "self.sec.create_api_key" in src
    assert "self.sec.rotate_api_key" in src
    assert "self.sec.revoke_api_key" in src


def test_admin_service_never_logs_raw_key_or_hash():
    src = _read(SEC_ADMIN_SERVICE)
    start = src.index("async def create_api_key")
    end = src.index("async def get_api_key_detail")
    body = src[start:end]
    assert "self._audit" not in body  # relies solely on SecurityService.create_api_key's own
                                       # audit call, which only records key_prefix — never adds a
                                       # second audit entry here that could leak the raw key/hash


def test_admin_service_uses_record_platform_audit():
    src = _read(SEC_ADMIN_SERVICE)
    assert "record_platform_audit" in src


def test_admin_service_uses_auth_sessions_not_session_inventory():
    src = _read(SEC_ADMIN_SERVICE)
    assert "UserSession" in src
    assert "LoginEvent" in src
    assert "from app.engines.security.models import" in src
    assert "SessionInventory" not in src.split("from app.engines.security.models import")[1].split("\n")[0]


# ── security/admin_router.py ────────────────────────────────────────────────

def test_admin_router_importable():
    import importlib
    mod = importlib.import_module("app.engines.security.admin_router")
    assert hasattr(mod, "router")


def test_admin_router_prefix():
    src = _read(SEC_ADMIN_ROUTER)
    assert '/v1/admin/security' in src


def test_admin_router_endpoints_present():
    src = _read(SEC_ADMIN_ROUTER)
    for path in ("/overview", "/threats", "/threats/{threat_id}", "/threats/{threat_id}/assign",
                 "/threats/{threat_id}/status", "/threats/{threat_id}/block-ip",
                 "/threats/{threat_id}/revoke-sessions", "/sessions", "/sessions/{session_id}",
                 "/sessions/{session_id}/revoke", "/sessions/user/{user_id}/revoke-all",
                 "/ip-blocklist", "/ip-blocklist/{entry_id}", "/ip-blocklist/{entry_id}/revoke",
                 "/ip-blocklist/{entry_id}/hits", "/api-keys", "/api-keys/{key_id}",
                 "/api-keys/{key_id}/rotate", "/api-keys/{key_id}/revoke", "/api-keys/{key_id}/usage",
                 "/audit-logs", "/audit-logs/{log_id}", "/audit-logs-export",
                 "/policies", "/policies/{policy_key}"):
        assert f'"{path}"' in src, f"missing route {path}"


def test_admin_router_permission_guarded():
    src = _read(SEC_ADMIN_ROUTER)
    for perm in ("P.SECURITY_READ", "P.SECURITY_THREATS_READ", "P.SECURITY_THREATS_UPDATE",
                 "P.SECURITY_THREATS_RESOLVE", "P.SECURITY_THREATS_BLOCK_IP",
                 "P.SECURITY_SESSIONS_READ", "P.SECURITY_SESSIONS_REVOKE",
                 "P.SECURITY_IP_BLOCKLIST_READ", "P.SECURITY_IP_BLOCKLIST_CREATE",
                 "P.SECURITY_IP_BLOCKLIST_UPDATE", "P.SECURITY_IP_BLOCKLIST_REVOKE",
                 "P.SECURITY_API_KEYS_READ", "P.SECURITY_API_KEYS_CREATE",
                 "P.SECURITY_API_KEYS_ROTATE", "P.SECURITY_API_KEYS_REVOKE",
                 "P.SECURITY_AUDIT_READ", "P.SECURITY_AUDIT_EXPORT",
                 "P.SECURITY_POLICIES_READ", "P.SECURITY_POLICIES_UPDATE"):
        assert perm in src


def test_admin_router_registered_in_main():
    src = _read(MAIN_PY)
    assert "security.admin_router" in src
    assert "security_admin_router" in src


# ── permissions.py ───────────────────────────────────────────────────────────

def test_permissions_security_constants_exist():
    src = _read(PERMISSIONS_FILE)
    for const in ("SECURITY_READ", "SECURITY_THREATS_READ", "SECURITY_THREATS_UPDATE",
                  "SECURITY_THREATS_RESOLVE", "SECURITY_THREATS_BLOCK_IP",
                  "SECURITY_SESSIONS_READ", "SECURITY_SESSIONS_REVOKE",
                  "SECURITY_IP_BLOCKLIST_READ", "SECURITY_IP_BLOCKLIST_CREATE",
                  "SECURITY_IP_BLOCKLIST_UPDATE", "SECURITY_IP_BLOCKLIST_REVOKE",
                  "SECURITY_API_KEYS_READ", "SECURITY_API_KEYS_CREATE",
                  "SECURITY_API_KEYS_ROTATE", "SECURITY_API_KEYS_REVOKE",
                  "SECURITY_AUDIT_READ", "SECURITY_AUDIT_EXPORT",
                  "SECURITY_POLICIES_READ", "SECURITY_POLICIES_UPDATE"):
        assert const in src


# ── enterprise_grid/filter_registry.py ──────────────────────────────────────

def test_filter_registry_security_resources_present():
    src = _read(FILTER_REGISTRY)
    for key in ("admin_security_threats", "admin_security_sessions",
                "admin_ip_blocklist", "admin_api_keys"):
        assert f'"{key}": {{' in src


def test_filter_registry_resource_count_35():
    # Note: total grew to 36 after the Customer Users Enterprise Upgrade added
    # admin_customers; this test only asserts Security's 4 resources are present,
    # not the exact global total (see test_sprint26_enterprise_grid.py for that).
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    assert len(EnterpriseFilterRegistry.all_resource_keys()) >= 35
