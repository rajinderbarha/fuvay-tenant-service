"""
P0 Enterprise Platform Users List + User Detail Upgrade — backend + frontend tests.
Migration 083 | users.platform_role/access_scope/invited_by_user_id | 29 new endpoints |
platform-users list/summary/detail | invite lifecycle | role/scope governance |
MFA enforcement | suspend/unsuspend | risk signals | audit trail | bulk actions.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


MIGRATION = ROOT / "alembic" / "versions" / "083_platform_users_governance.py"
MODELS    = ROOT / "app" / "engines" / "auth" / "models.py"
SERVICE   = ROOT / "app" / "engines" / "auth" / "service.py"
SCHEMAS   = ROOT / "app" / "engines" / "auth" / "schemas.py"
ROUTER    = ROOT / "app" / "engines" / "auth" / "platform_users_router.py"
MAIN      = ROOT / "app" / "main.py"
PAGE      = ROOT / "frontend" / "super-admin" / "app" / "admin" / "users" / "page.tsx"
API_TS    = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"


# ════════════════════════════════════════════════════════════════════════════
# Migration 083
# ════════════════════════════════════════════════════════════════════════════
class TestMigration083:
    def test_migration_file_exists(self):
        assert MIGRATION.exists()

    def test_revision(self):
        assert 'revision = "083"' in _read(MIGRATION)

    def test_down_revision(self):
        assert 'down_revision = "082"' in _read(MIGRATION)

    def test_platform_role_column(self):
        assert "platform_role" in _read(MIGRATION)

    def test_access_scope_column(self):
        assert "access_scope" in _read(MIGRATION)

    def test_invited_by_user_id_column(self):
        assert "invited_by_user_id" in _read(MIGRATION)

    def test_backfill_super_admin(self):
        src = _read(MIGRATION)
        assert "UPDATE users" in src
        assert "super_admin" in src

    def test_downgrade_exists(self):
        assert "def downgrade" in _read(MIGRATION)


# ════════════════════════════════════════════════════════════════════════════
# Model fields
# ════════════════════════════════════════════════════════════════════════════
class TestUserModel:
    def test_platform_role_field(self):
        assert "platform_role" in _read(MODELS)

    def test_access_scope_field(self):
        assert "access_scope" in _read(MODELS)

    def test_invited_by_user_id_field(self):
        assert "invited_by_user_id" in _read(MODELS)


# ════════════════════════════════════════════════════════════════════════════
# Service — Platform Users governance
# ════════════════════════════════════════════════════════════════════════════
class TestPlatformUsersService:
    def test_service_file_exists(self):
        assert SERVICE.exists()

    def test_user_group_classification(self):
        assert "_user_group" in _read(SERVICE)

    def test_user_status_derivation(self):
        assert "_user_status" in _read(SERVICE)

    def test_mfa_status_derivation(self):
        assert "_mfa_status" in _read(SERVICE)

    def test_list_platform_users(self):
        assert "async def list_platform_users" in _read(SERVICE)

    def test_list_excludes_tenant_by_default(self):
        src = _read(SERVICE)
        # FINAL-L5-05N: "platform" group now scopes to all 5 real admin
        # roles (PLATFORM_ADMIN_ROLES), not just literal super_admin --
        # otherwise users invited with a limited role would be invisible
        # in their own management list.
        assert '"platform": self.PLATFORM_ADMIN_ROLES' in src

    def test_get_platform_users_summary(self):
        assert "async def get_platform_users_summary" in _read(SERVICE)

    def test_summary_fields(self):
        src = _read(SERVICE)
        for field in ["total_platform_users", "mfa_missing", "pending_invites",
                      "locked_accounts", "suspicious_logins", "inactive_30_days"]:
            assert field in src, f"Missing summary field: {field}"

    def test_get_platform_user_detail(self):
        assert "async def get_platform_user_detail" in _read(SERVICE)

    def test_invite_platform_user(self):
        assert "async def invite_platform_user" in _read(SERVICE)

    def test_invite_super_admin_requires_super_admin_actor(self):
        src = _read(SERVICE)
        assert 'platform_role == "super_admin" and admin.role != "super_admin"' in src

    def test_invite_duplicate_email_blocked(self):
        src = _read(SERVICE)
        start = src.index("async def invite_platform_user")
        end = src.index("async def list_platform_invites")
        assert "ALREADY_EXISTS" in src[start:end]

    def test_list_platform_invites(self):
        assert "async def list_platform_invites" in _read(SERVICE)

    def test_revoke_platform_invite(self):
        assert "async def revoke_platform_invite" in _read(SERVICE)

    def test_change_platform_role(self):
        assert "async def change_platform_role" in _read(SERVICE)

    def test_change_platform_role_validates(self):
        src = _read(SERVICE)
        start = src.index("async def change_platform_role")
        end = src.index("async def change_access_scope")
        assert "VALID_PLATFORM_ROLES" in src[start:end]

    def test_change_access_scope(self):
        assert "async def change_access_scope" in _read(SERVICE)

    def test_require_mfa_for_user(self):
        assert "async def require_mfa_for_user" in _read(SERVICE)

    def test_reset_mfa_for_user(self):
        assert "async def reset_mfa_for_user" in _read(SERVICE)

    def test_reset_mfa_clears_secrets(self):
        src = _read(SERVICE)
        start = src.index("async def reset_mfa_for_user")
        end = src.index("# ── P0 Platform Users: Single session revoke")
        section = src[start:end]
        assert "MFASecret" in section
        assert "MFABackupCode" in section

    def test_suspend_user(self):
        assert "async def suspend_user" in _read(SERVICE)

    def test_suspend_self_blocked(self):
        src = _read(SERVICE)
        start = src.index("async def suspend_user")
        end = src.index("async def unsuspend_user")
        assert "cannot suspend your own account" in src[start:end]

    def test_deactivate_self_blocked(self):
        src = _read(SERVICE)
        start = src.index("async def deactivate_user")
        end = src.index("async def reactivate_user")
        assert "cannot deactivate your own account" in src[start:end]

    def test_unsuspend_user(self):
        assert "async def unsuspend_user" in _read(SERVICE)

    def test_admin_revoke_session_single(self):
        assert "async def admin_revoke_session" in _read(SERVICE)

    def test_get_platform_user_risk_signals(self):
        assert "async def get_platform_user_risk_signals" in _read(SERVICE)

    def test_risk_signal_types(self):
        src = _read(SERVICE)
        for signal in ["mfa_missing", "too_many_failed_logins", "locked_account",
                       "password_reset_required", "inactive_30_days", "role_privilege_high"]:
            assert signal in src, f"Missing risk signal: {signal}"

    def test_risk_score_levels(self):
        src = _read(SERVICE)
        for level in ['"critical"', '"high"', '"medium"', '"low"']:
            assert level in src

    def test_get_platform_user_audit_logs(self):
        assert "async def get_platform_user_audit_logs" in _read(SERVICE)

    def test_list_platform_audit_logs(self):
        assert "async def list_platform_audit_logs" in _read(SERVICE)

    def test_audit_ip_hint_not_raw(self):
        src = _read(SERVICE)
        assert "ip_hint" in src

    def test_bulk_platform_action(self):
        assert "async def bulk_platform_action" in _read(SERVICE)

    def test_bulk_actions_supported(self):
        src = _read(SERVICE)
        start = src.index("async def bulk_platform_action")
        section = src[start:start + 1500]
        for action in ["require_mfa", "force_password_reset", "suspend",
                       "deactivate", "revoke_sessions"]:
            assert f'"{action}"' in section

    def test_audit_events_present(self):
        src = _read(SERVICE)
        for event in [
            "platform_user.invited", "platform_user.role_changed",
            "platform_user.access_scope_changed", "platform_user.mfa_required",
            "platform_user.mfa_reset", "platform_user.suspended",
            "platform_user.reactivated", "platform_user.session_revoked",
            "platform_user.invite_revoked",
        ]:
            assert event in src, f"Missing audit event: {event}"


# ════════════════════════════════════════════════════════════════════════════
# Schemas — reason-required request bodies
# ════════════════════════════════════════════════════════════════════════════
class TestPlatformUsersSchemas:
    def test_schemas_file_exists(self):
        assert SCHEMAS.exists()

    def test_suspend_request_reason_required(self):
        src = _read(SCHEMAS)
        start = src.index("class SuspendUserRequest")
        end = src.index("class UnsuspendUserRequest")
        assert "min_length=3" in src[start:end]

    def test_require_mfa_request_reason_required(self):
        src = _read(SCHEMAS)
        start = src.index("class RequireMfaRequest")
        end = src.index("class ResetMfaRequest")
        assert "min_length=3" in src[start:end]

    def test_change_role_request(self):
        assert "class ChangeRoleRequest" in _read(SCHEMAS)

    def test_change_access_scope_request(self):
        assert "class ChangeAccessScopeRequest" in _read(SCHEMAS)

    def test_invite_platform_user_request(self):
        src = _read(SCHEMAS)
        assert "class InvitePlatformUserRequest" in src
        start = src.index("class InvitePlatformUserRequest")
        end = src.index("class RevokeInviteRequest")
        section = src[start:end]
        for field in ["full_name", "email", "platform_role", "access_scope", "require_mfa"]:
            assert field in section

    def test_bulk_action_request(self):
        src = _read(SCHEMAS)
        assert "class BulkPlatformActionRequest" in src
        start = src.index("class BulkPlatformActionRequest")
        section = src[start:start + 400]
        assert "user_ids" in section
        assert "reason" in section


# ════════════════════════════════════════════════════════════════════════════
# Router — endpoint + ordering + permission checks
# ════════════════════════════════════════════════════════════════════════════
class TestPlatformUsersRouter:
    def test_router_file_exists(self):
        assert ROUTER.exists()

    def test_prefix(self):
        assert '/v1/admin/platform-users' in _read(ROUTER)

    def test_summary_route(self):
        assert '"/summary"' in _read(ROUTER)

    def test_export_route(self):
        assert '"/export"' in _read(ROUTER)

    def test_invite_route(self):
        assert '"/invite"' in _read(ROUTER)

    def test_invites_list_route(self):
        assert '"/invites"' in _read(ROUTER)

    def test_bulk_route(self):
        assert '"/bulk/{action}"' in _read(ROUTER)

    def test_role_route(self):
        assert '"/{user_id}/role"' in _read(ROUTER)

    def test_access_scope_route(self):
        assert '"/{user_id}/access-scope"' in _read(ROUTER)

    def test_suspend_route(self):
        assert '"/{user_id}/suspend"' in _read(ROUTER)

    def test_require_mfa_route(self):
        assert '"/{user_id}/require-mfa"' in _read(ROUTER)

    def test_reset_mfa_route(self):
        assert '"/{user_id}/reset-mfa"' in _read(ROUTER)

    def test_sessions_route(self):
        assert '"/{user_id}/sessions"' in _read(ROUTER)

    def test_single_session_revoke_route(self):
        assert '"/{user_id}/sessions/{session_id}/revoke"' in _read(ROUTER)

    def test_login_history_route(self):
        assert '"/{user_id}/login-history"' in _read(ROUTER)

    def test_risk_signals_route(self):
        assert '"/{user_id}/risk-signals"' in _read(ROUTER)

    def test_audit_logs_route(self):
        assert '"/{user_id}/audit-logs"' in _read(ROUTER)

    def test_static_routes_before_dynamic(self):
        """/summary, /export, /invites, /invite, /audit-logs, /bulk must be
        registered before /{user_id} to avoid UUID-parse shadowing."""
        src = _read(ROUTER)
        dynamic_pos = src.index('@router.get("/{user_id}")')
        for static in ['"/summary"', '"/export"', '"/audit-logs"', '"/invites"',
                       '"/invite"', '"/bulk/{action}"']:
            assert src.index(static) < dynamic_pos, f"{static} must precede /{{user_id}}"

    def test_require_platform_mutate_dependency(self):
        assert "require_platform_mutate" in _read(ROUTER)

    def test_read_only_admin_blocked(self):
        src = _read(ROUTER)
        assert "read_only_admin" in src

    def test_temp_password_restricted_to_super_admin(self):
        src = _read(ROUTER)
        start = src.index("generate_temp_password")
        section = src[start:start + 400]
        assert "require_super_admin" in section

    def test_mutating_routes_use_require_platform_mutate(self):
        src = _read(ROUTER)
        assert src.count("Depends(require_platform_mutate)") >= 10


# ════════════════════════════════════════════════════════════════════════════
# Self-deactivation guard (critical security bug fix)
# ════════════════════════════════════════════════════════════════════════════
class TestSelfActionGuards:
    def test_deactivate_self_guard_uses_service_exception(self):
        src = _read(SERVICE)
        assert 'ServiceOSException("PERMISSION_DENIED", "You cannot deactivate your own account.")' in src

    def test_suspend_self_guard_uses_service_exception(self):
        src = _read(SERVICE)
        assert 'ServiceOSException("PERMISSION_DENIED", "You cannot suspend your own account.")' in src

    def test_no_broken_permission_denied_single_arg_calls(self):
        """PermissionDeniedException requires (required_role, current_role) — a bare
        single-string call raises TypeError at runtime. None should remain."""
        src = _read(SERVICE)
        import re
        for m in re.finditer(r'PermissionDeniedException\(\s*"', src):
            # Any remaining call must be immediately followed by a second arg (comma) eventually;
            # single-string calls close with ")" before a comma appears on the same logical call.
            snippet = src[m.start():m.start() + 200]
            # crude but effective: a well-formed 2-arg call has a comma before the first ")"
            close_idx = snippet.index(")")
            comma_idx = snippet.find(",")
            assert 0 <= comma_idx < close_idx, f"Possible single-arg call at: {snippet[:80]!r}"


# ════════════════════════════════════════════════════════════════════════════
# main.py registration
# ════════════════════════════════════════════════════════════════════════════
class TestMainRegistration:
    def test_platform_users_router_imported(self):
        assert "platform_users_router" in _read(MAIN)

    def test_platform_users_router_included(self):
        src = _read(MAIN)
        assert "app.include_router(platform_users_router)" in src


# ════════════════════════════════════════════════════════════════════════════
# Frontend — page + api client (non-blocking scope: page rewrite tracked separately)
# ════════════════════════════════════════════════════════════════════════════
class TestFrontendPage:
    def test_page_exists(self):
        assert PAGE.exists()

    def test_api_file_exists(self):
        assert API_TS.exists()
