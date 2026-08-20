"""Regression guards for the enterprise Security command center."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_security_workspace_has_enabled_operational_tabs_and_cursor_paging():
    page = source("frontend/super-admin/app/admin/security/page.tsx")
    for tab in ("overview", "threats", "sessions", "ip_blocklist", "audit_logs", "policies"):
        assert f'"{tab}"' in page
    assert '{ key: "api_keys", label: "API Keys"' not in page
    assert "next_cursor" in page
    assert "CursorPager" in page
    assert "limit: pageSize" in page
    assert "cursor: cursor || undefined" in page


def test_security_filters_are_dependencies_not_one_time_fetches():
    page = source("frontend/super-admin/app/admin/security/page.tsx")
    assert "[status, level, search, pageSize, cursor, refreshKey]" in page
    assert "[search, role, activeOnly, pageSize, cursor, refreshKey]" in page
    assert "[search, status, scope, pageSize, cursor, refreshKey]" in page


def test_session_revocation_and_network_blocks_are_runtime_enforced():
    admin = source("app/engines/security/admin_service.py")
    middleware = source("app/middleware.py")
    errors = source("app/schemas/base.py")
    assert 'serviceos:session:revoked:{session_id}' in admin
    assert "class IPBlocklistMiddleware" in middleware
    assert "IPBlockHit" in middleware
    assert '"SESSION_REVOKED":' in errors
    assert '"status": 401' in errors


def test_network_controls_work_and_dormant_api_key_code_stays_hardened():
    service = source("app/engines/security/service.py")
    admin = source("app/engines/security/admin_service.py")
    frontend_api = source("frontend/super-admin/lib/api.ts")
    assert "_api_key_runtime_denial" in service
    assert "rate_limit_per_minute" in service
    assert "allowed_ips_json" in service
    assert 'str(network.network_address) if entry_type == "ip"' in admin
    assert "permanent: data.permanent" in frontend_api


def test_security_migrations_seed_only_enforced_policies_and_scale_indexes():
    migration = source("alembic/versions/288_security_command_center_runtime.py")
    followup = source("alembic/versions/289_security_concurrent_session_policy.py")
    assert "ix_user_sessions_active_last_id" in migration
    assert "ix_pal_high_risk_created_id" in migration
    assert "max_concurrent_sessions" in followup
    assert "fresh_mfa_for_sensitive_actions" in followup and "DELETE FROM security_policies" in followup


def test_threat_detail_requires_reasons_and_permission_gates():
    page = source("frontend/super-admin/app/admin/security/threats/[threat_id]/page.tsx")
    assert "Decision reason" in page
    assert 'permissions.has("security:threats:update")' in page
    assert 'permissions.has("security:threats:block_ip")' in page
    assert 'permissions.has("security:sessions:revoke")' in page
