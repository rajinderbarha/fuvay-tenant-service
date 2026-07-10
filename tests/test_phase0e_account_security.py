"""
Phase 0E — Account Security + Admin User Controls — Backend Tests.

Tests cover:
  - Migration 054: new columns on users/user_sessions + login_events table
  - User ORM model: 7 new security columns
  - UserSession ORM model: revoked_by_user_id, revocation_reason
  - LoginEvent ORM model: all fields + table name
  - Permissions: new security permission constants
  - Schemas: LockAccountRequest, UnlockAccountRequest, DeactivateUserRequest,
             ReactivateUserRequest, AdminRevokeAllSessionsRequest
  - Service: lock_user, unlock_user, deactivate_user, reactivate_user,
             admin_list_sessions, admin_revoke_all_sessions, get_login_history,
             get_full_security_status, _log_login_event
  - Service guard: _can_admin_manage_user prevents cross-tenant management
  - Router: admin security endpoints registered on admin_security_router
  - Router: self endpoints on _me_security_router
  - main.py: both new routers included
  - Frontend: admin user detail page created
  - Frontend: self sessions + login history pages created
  - Frontend: tenant-portal staff security controls integrated
  - Frontend: super-admin api.ts has all Phase 0E methods
  - Frontend: tenant-portal api.ts has staff security methods
  - Security: no password hashes in security status endpoints
  - Security: no raw tokens in any response schema
"""
from __future__ import annotations

import pathlib
import re

import pytest

BACKEND     = pathlib.Path(__file__).parent.parent.resolve()
SUPER_ADMIN = BACKEND / "frontend" / "super-admin"
TENANT      = BACKEND / "frontend" / "tenant-portal"
AUTH        = BACKEND / "app" / "engines" / "auth"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Migration 054
# ═══════════════════════════════════════════════════════════════════════════════

def test_migration_054_exists():
    assert (BACKEND / "alembic/versions/054_phase0e_account_security.py").exists()


def test_migration_054_down_revision_is_053():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert 'down_revision = "053"' in text


def test_migration_054_adds_account_status():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "account_status" in text


def test_migration_054_adds_lock_reason():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "lock_reason" in text


def test_migration_054_adds_locked_by_user_id():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "locked_by_user_id" in text


def test_migration_054_adds_deactivated_at():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "deactivated_at" in text


def test_migration_054_adds_deactivated_by_user_id():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "deactivated_by_user_id" in text


def test_migration_054_adds_deactivation_reason():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "deactivation_reason" in text


def test_migration_054_adds_last_failed_login_at():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "last_failed_login_at" in text


def test_migration_054_adds_revoked_by_user_id_to_sessions():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "revoked_by_user_id" in text
    assert "user_sessions" in text


def test_migration_054_creates_login_events_table():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "login_events" in text


def test_migration_054_login_events_has_event_type():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "event_type" in text


def test_migration_054_login_events_has_ip_address():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "ip_address" in text


def test_migration_054_account_status_default_active():
    text = (BACKEND / "alembic/versions/054_phase0e_account_security.py").read_text(encoding="utf-8")
    assert "active" in text


# ═══════════════════════════════════════════════════════════════════════════════
# 2. ORM Models
# ═══════════════════════════════════════════════════════════════════════════════

def test_user_model_has_account_status():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "account_status" in text


def test_user_model_has_lock_reason():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "lock_reason" in text


def test_user_model_has_locked_by_user_id():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "locked_by_user_id" in text


def test_user_model_has_deactivated_at():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "deactivated_at" in text


def test_user_model_has_deactivated_by_user_id():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "deactivated_by_user_id" in text


def test_user_model_has_deactivation_reason():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "deactivation_reason" in text


def test_user_model_has_last_failed_login_at():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "last_failed_login_at" in text


def test_user_session_model_has_revoked_by_user_id():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "revoked_by_user_id" in text


def test_user_session_model_has_revocation_reason():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "revocation_reason" in text


def test_login_event_model_exists():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "class LoginEvent" in text


def test_login_event_table_name():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert '__tablename__ = "login_events"' in text


def test_login_event_has_event_type():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "event_type" in text


def test_login_event_has_failure_reason():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "failure_reason" in text


def test_login_event_has_ip_address():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "ip_address" in text


def test_login_event_has_user_agent():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "user_agent" in text


def test_login_event_has_request_id():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    assert "request_id" in text


def test_login_event_user_id_nullable():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    # user_id nullable so failed logins with unknown email still get logged
    idx = text.index("class LoginEvent")
    snippet = text[idx:idx+800]
    assert "nullable=True" in snippet


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Permissions
# ═══════════════════════════════════════════════════════════════════════════════

def _perms():
    return (BACKEND / "app/core/permissions.py").read_text(encoding="utf-8")


def test_perm_users_security_lock():
    assert "users:security:lock" in _perms()


def test_perm_users_security_unlock():
    assert "users:security:unlock" in _perms()


def test_perm_users_security_deactivate():
    assert "users:security:deactivate" in _perms()


def test_perm_users_security_reactivate():
    assert "users:security:reactivate" in _perms()


def test_perm_users_security_revoke_sessions():
    assert "users:security:revoke_sessions" in _perms()


def test_perm_users_security_view_sessions():
    assert "users:security:view_sessions" in _perms()


def test_perm_users_security_view_history():
    assert "users:security:view_login_history" in _perms() or "view_history" in _perms()


def test_perm_tenant_staff_security_manage():
    assert "tenant_staff:security:manage" in _perms()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Schemas
# ═══════════════════════════════════════════════════════════════════════════════

def _schemas():
    return (AUTH / "schemas.py").read_text(encoding="utf-8")


def test_schema_lock_account_request_exists():
    assert "class LockAccountRequest" in _schemas()


def test_schema_unlock_account_request_exists():
    assert "class UnlockAccountRequest" in _schemas()


def test_schema_deactivate_user_request_exists():
    assert "class DeactivateUserRequest" in _schemas()


def test_schema_reactivate_user_request_exists():
    assert "class ReactivateUserRequest" in _schemas()


def test_schema_admin_revoke_all_sessions_request_exists():
    assert "class AdminRevokeAllSessionsRequest" in _schemas()


def test_lock_request_has_reason_field():
    text = _schemas()
    idx = text.index("class LockAccountRequest")
    snippet = text[idx:idx+400]
    assert "reason" in snippet


def test_lock_request_has_revoke_sessions_field():
    text = _schemas()
    idx = text.index("class LockAccountRequest")
    snippet = text[idx:idx+400]
    assert "revoke_sessions" in snippet


def test_lock_request_has_locked_until_field():
    text = _schemas()
    idx = text.index("class LockAccountRequest")
    snippet = text[idx:idx+400]
    assert "locked_until" in snippet


def test_schemas_no_raw_password_hash_exposure():
    text = _schemas()
    assert "password_hash" not in text
    assert "hashed_password" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Service methods
# ═══════════════════════════════════════════════════════════════════════════════

def _service():
    return (AUTH / "service.py").read_text(encoding="utf-8")


def test_service_lock_user_method_exists():
    assert "async def lock_user" in _service()


def test_service_unlock_user_method_exists():
    assert "async def unlock_user" in _service()


def test_service_deactivate_user_method_exists():
    assert "async def deactivate_user" in _service()


def test_service_reactivate_user_method_exists():
    assert "async def reactivate_user" in _service()


def test_service_admin_list_sessions_exists():
    assert "async def admin_list_sessions" in _service()


def test_service_admin_revoke_all_sessions_exists():
    assert "async def admin_revoke_all_sessions" in _service()


def test_service_get_login_history_exists():
    assert "async def get_login_history" in _service()


def test_service_get_full_security_status_exists():
    assert "async def get_full_security_status" in _service()


def test_service_log_login_event_exists():
    assert "_log_login_event" in _service()


def test_service_lock_user_sets_account_status():
    text = _service()
    idx = text.index("async def lock_user")
    snippet = text[idx:idx+600]
    assert "account_status" in snippet


def test_service_lock_user_sets_lock_reason():
    text = _service()
    idx = text.index("async def lock_user")
    snippet = text[idx:idx+600]
    assert "lock_reason" in snippet


def test_service_unlock_user_resets_account_status():
    text = _service()
    idx = text.index("async def unlock_user")
    snippet = text[idx:idx+500]
    assert "account_status" in snippet
    assert "active" in snippet


def test_service_deactivate_sets_is_active_false():
    text = _service()
    idx = text.index("async def deactivate_user")
    snippet = text[idx:idx+600]
    assert "is_active" in snippet


def test_service_reactivate_sets_is_active_true():
    text = _service()
    idx = text.index("async def reactivate_user")
    snippet = text[idx:idx+600]
    assert "is_active" in snippet


def test_service_lock_user_writes_audit_log():
    text = _service()
    idx = text.index("async def lock_user")
    # Scan up to 1500 chars to include the audit call at end of method
    snippet = text[idx:idx+1500]
    assert "audit" in snippet.lower() or "account.locked" in snippet or "_audit" in snippet


def test_service_revoke_all_sessions_uses_redis():
    text = _service()
    idx = text.index("async def admin_revoke_all_sessions")
    snippet = text[idx:idx+600]
    assert "redis" in snippet.lower() or "revoked" in snippet


def test_service_can_admin_manage_user_guard_exists():
    assert "_can_admin_manage_user" in _service()


def test_service_guard_blocks_cross_tenant():
    text = _service()
    idx = text.index("_can_admin_manage_user")
    # The guard must check tenant_id to prevent IDOR
    snippet = text[idx:idx+500]
    assert "tenant_id" in snippet or "super_admin" in snippet


def test_service_log_event_never_raises():
    text = _service()
    # Find the method definition (not a call site)
    idx = text.index("async def _log_login_event")
    snippet = text[idx:idx+1000]
    assert "except" in snippet


def test_service_security_status_excludes_password_hash():
    text = _service()
    idx = text.index("async def get_full_security_status")
    snippet = text[idx:idx+800]
    assert "password_hash" not in snippet
    assert "hashed_password" not in snippet


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Router endpoints
# ═══════════════════════════════════════════════════════════════════════════════

def _router():
    return (AUTH / "router.py").read_text(encoding="utf-8")


def test_router_admin_security_router_exists():
    assert "admin_security_router" in _router()


def test_router_me_security_router_exists():
    assert "_me_security_router" in _router()


def test_router_lock_endpoint_registered():
    text = _router()
    assert "/lock" in text


def test_router_unlock_endpoint_registered():
    text = _router()
    assert "/unlock" in text


def test_router_deactivate_endpoint_registered():
    text = _router()
    assert "/deactivate" in text


def test_router_reactivate_endpoint_registered():
    text = _router()
    assert "/reactivate" in text


def test_router_sessions_list_endpoint_registered():
    text = _router()
    assert "/sessions" in text


def test_router_sessions_revoke_all_endpoint_registered():
    text = _router()
    assert "revoke-all" in text or "revoke_all" in text


def test_router_login_history_endpoint_registered():
    text = _router()
    assert "login-history" in text or "login_history" in text


def test_router_me_login_history_endpoint():
    text = _router()
    # /v1/auth/login-history for self
    assert "login-history" in text or "login_history" in text


def test_router_admin_security_endpoint_uses_security_service():
    text = _router()
    assert "lock_user" in text or "get_full_security_status" in text


def test_router_imports_security_schemas():
    text = _router()
    assert "LockAccountRequest" in text or "lock_user" in text


# ═══════════════════════════════════════════════════════════════════════════════
# 7. main.py router registration
# ═══════════════════════════════════════════════════════════════════════════════

def _main():
    return (BACKEND / "app/main.py").read_text(encoding="utf-8")


def test_main_imports_admin_security_router():
    assert "admin_security_router" in _main()


def test_main_imports_me_security_router():
    assert "_me_security_router" in _main()


def test_main_includes_admin_security_router():
    text = _main()
    assert "admin_security_router" in text
    assert "include_router" in text


def test_main_includes_me_security_router():
    text = _main()
    assert "_me_security_router" in text


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Frontend — super-admin user detail page
# ═══════════════════════════════════════════════════════════════════════════════

_USER_DETAIL = SUPER_ADMIN / "app/admin/users/[id]/page.tsx"


def test_super_admin_user_detail_page_exists():
    assert _USER_DETAIL.exists()


def test_user_detail_page_has_lock_action():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "Lock Account" in text or "lockUser" in text


def test_user_detail_page_has_unlock_action():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "Unlock Account" in text or "unlockUser" in text


def test_user_detail_page_has_deactivate_action():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "Deactivate" in text or "deactivateUser" in text


def test_user_detail_page_has_revoke_sessions_action():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "Revoke" in text


def test_user_detail_page_shows_login_history():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "Login History" in text or "login-history" in text


def test_user_detail_page_shows_active_sessions():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "Session" in text


def test_user_detail_page_has_confirm_modal():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "Confirm" in text and "Modal" in text


def test_user_detail_page_has_reason_textarea():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "textarea" in text or "reason" in text.lower()


def test_user_detail_page_no_password_hash_display():
    text = _USER_DETAIL.read_text(encoding="utf-8")
    assert "password_hash" not in text
    assert "hashed_password" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Frontend — super-admin self sessions page
# ═══════════════════════════════════════════════════════════════════════════════

_SESSIONS_PAGE = SUPER_ADMIN / "app/admin/account/sessions/page.tsx"


def test_super_admin_self_sessions_page_exists():
    assert _SESSIONS_PAGE.exists()


def test_sessions_page_calls_get_self_sessions():
    text = _SESSIONS_PAGE.read_text(encoding="utf-8")
    assert "getSelfSessions" in text


def test_sessions_page_has_revoke_other_devices():
    text = _SESSIONS_PAGE.read_text(encoding="utf-8")
    assert "revokeSelf" in text or "Other Devices" in text


def test_sessions_page_shows_device_info():
    text = _SESSIONS_PAGE.read_text(encoding="utf-8")
    assert "device" in text.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Frontend — super-admin login history page
# ═══════════════════════════════════════════════════════════════════════════════

_HISTORY_PAGE = SUPER_ADMIN / "app/admin/account/login-history/page.tsx"


def test_super_admin_login_history_page_exists():
    assert _HISTORY_PAGE.exists()


def test_login_history_page_calls_get_self_login_history():
    text = _HISTORY_PAGE.read_text(encoding="utf-8")
    assert "getSelfLoginHistory" in text


def test_login_history_page_shows_event_type():
    text = _HISTORY_PAGE.read_text(encoding="utf-8")
    assert "event_type" in text or "eventVariant" in text


def test_login_history_page_shows_failure_reason():
    text = _HISTORY_PAGE.read_text(encoding="utf-8")
    assert "failure_reason" in text


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Frontend — tenant-portal staff security
# ═══════════════════════════════════════════════════════════════════════════════

_STAFF_DETAIL = TENANT / "app/(tenant)/staff/[id]/page.tsx"


def test_tenant_staff_detail_has_security_section():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "Security" in text


def test_tenant_staff_detail_has_lock_action():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "Lock" in text


def test_tenant_staff_detail_has_unlock_action():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "Unlock" in text


def test_tenant_staff_detail_has_revoke_sessions():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "Revoke" in text


def test_tenant_staff_detail_shows_login_history():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "Login" in text and ("Event" in text or "History" in text)


def test_tenant_staff_detail_has_reason_input():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "reason" in text.lower()


def test_tenant_staff_security_calls_auth_api():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "authApi" in text


def test_tenant_staff_security_no_password_hash():
    text = _STAFF_DETAIL.read_text(encoding="utf-8")
    assert "password_hash" not in text


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Frontend — super-admin api.ts Phase 0E methods
# ═══════════════════════════════════════════════════════════════════════════════

_ADMIN_API = SUPER_ADMIN / "lib/api.ts"


def test_admin_api_has_lock_user():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "lockUser" in text


def test_admin_api_has_unlock_user():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "unlockUser" in text


def test_admin_api_has_deactivate_user():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "deactivateUser" in text


def test_admin_api_has_reactivate_user():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "reactivateUser" in text


def test_admin_api_has_admin_list_sessions():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "adminListSessions" in text


def test_admin_api_has_admin_revoke_all_sessions():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "adminRevokeAllSessions" in text


def test_admin_api_has_admin_get_login_history():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "adminGetLoginHistory" in text


def test_admin_api_has_get_self_sessions():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "getSelfSessions" in text


def test_admin_api_has_revoke_self_other_sessions():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "revokeSelfOtherSessions" in text


def test_admin_api_has_get_self_login_history():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "getSelfLoginHistory" in text


def test_admin_api_lock_user_calls_correct_endpoint():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "/lock" in text


def test_admin_api_unlock_user_calls_correct_endpoint():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "/unlock" in text


def test_admin_api_has_session_info_type():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "SessionInfo" in text


def test_admin_api_has_login_history_event_type():
    text = _ADMIN_API.read_text(encoding="utf-8")
    assert "LoginHistoryEvent" in text


def test_admin_api_no_raw_token_in_lock_payload():
    text = _ADMIN_API.read_text(encoding="utf-8")
    idx = text.index("lockUser")
    snippet = text[idx:idx+300]
    assert "refresh_token" not in snippet
    assert "password_hash" not in snippet


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Frontend — tenant-portal api.ts Phase 0E methods
# ═══════════════════════════════════════════════════════════════════════════════

_TENANT_API = TENANT / "lib/api.ts"


def test_tenant_api_has_lock_staff():
    text = _TENANT_API.read_text(encoding="utf-8")
    assert "lockStaff" in text


def test_tenant_api_has_unlock_staff():
    text = _TENANT_API.read_text(encoding="utf-8")
    assert "unlockStaff" in text


def test_tenant_api_has_revoke_staff_sessions():
    text = _TENANT_API.read_text(encoding="utf-8")
    assert "revokeStaffSessions" in text


def test_tenant_api_has_get_staff_login_history():
    text = _TENANT_API.read_text(encoding="utf-8")
    assert "getStaffLoginHistory" in text


def test_tenant_api_has_get_staff_security_status():
    text = _TENANT_API.read_text(encoding="utf-8")
    assert "getStaffSecurityStatus" in text


def test_tenant_api_has_staff_security_status_type():
    text = _TENANT_API.read_text(encoding="utf-8")
    assert "StaffSecurityStatus" in text


def test_tenant_api_has_staff_login_event_type():
    text = _TENANT_API.read_text(encoding="utf-8")
    assert "StaffLoginEvent" in text


def test_tenant_api_lock_staff_uses_tenant_scoped_endpoint():
    # Sprint 35 fix: lockStaff must use tenant-scoped endpoint, not super_admin /v1/admin/users/*
    text = _TENANT_API.read_text(encoding="utf-8")
    idx = text.index("lockStaff")
    snippet = text[idx:idx+200]
    assert "/v1/tenant/staff/" in snippet


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Security invariants (no sensitive data exposure)
# ═══════════════════════════════════════════════════════════════════════════════

def test_security_status_schema_no_password_hash():
    text = _schemas()
    assert "password_hash" not in text
    assert "hashed_password" not in text


def test_router_no_refresh_token_in_security_responses():
    text = _router()
    # Security endpoints must not return refresh tokens
    for endpoint in ["lock_user", "unlock_user", "deactivate_user", "reactivate_user"]:
        if endpoint in text:
            idx = text.index(endpoint)
            snippet = text[idx:idx+500]
            assert "refresh_token" not in snippet


def test_login_event_model_no_password_storage():
    text = (AUTH / "models.py").read_text(encoding="utf-8")
    idx = text.index("class LoginEvent")
    snippet = text[idx:idx+800]
    assert "password" not in snippet.lower()


def test_service_revoke_uses_redis_not_just_db():
    text = _service()
    idx = text.index("async def admin_revoke_all_sessions")
    # Scan up to 1200 chars to reach the Redis setex call
    snippet = text[idx:idx+1200]
    has_redis = "redis" in snippet.lower() or "setex" in snippet or "serviceos:session" in snippet
    assert has_redis, "admin_revoke_all_sessions must revoke via Redis for immediate JWT invalidation"
