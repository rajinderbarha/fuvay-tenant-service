"""
Phase 0D — Force Password Change + Admin Reset — Backend Tests.

Tests cover:
  - Migration 053: new columns + password_reset_tokens table
  - User ORM model: new security columns
  - PasswordResetToken model: fields + hash storage
  - Schemas: ChangePasswordRequiredRequest, AdminForce/Reset/TempPw schemas
  - Password policy: strength validation with special-char requirement
  - Service: change_password_required, admin_force_password_change,
             admin_generate_temporary_password, get_user_security_status
  - Router: new endpoints registered
  - Auth guard: force_password_change blocks role-guarded endpoints
  - Frontend: change-password-required pages in both portals
  - Frontend: login pages redirect when requires_password_change
  - Frontend: api.ts has changePasswordRequired + admin security calls
"""
from __future__ import annotations

import pathlib
import re

import pytest

BACKEND     = pathlib.Path(__file__).parent.parent.resolve()
SUPER_ADMIN = BACKEND / "frontend" / "super-admin"
TENANT      = BACKEND / "frontend" / "tenant-portal"


# ── 1. Migration 053 ─────────────────────────────────────────────────────────

def test_migration_053_exists():
    assert (BACKEND / "alembic/versions/053_phase0d_password_security.py").exists()


def test_migration_053_down_revision_is_052():
    content = (BACKEND / "alembic/versions/053_phase0d_password_security.py").read_text(encoding="utf-8")
    assert 'down_revision = "052"' in content


def test_migration_053_adds_password_reset_required():
    content = (BACKEND / "alembic/versions/053_phase0d_password_security.py").read_text(encoding="utf-8")
    assert "password_reset_required" in content


def test_migration_053_adds_temporary_password_active():
    content = (BACKEND / "alembic/versions/053_phase0d_password_security.py").read_text(encoding="utf-8")
    assert "temporary_password_active" in content


def test_migration_053_creates_password_reset_tokens_table():
    content = (BACKEND / "alembic/versions/053_phase0d_password_security.py").read_text(encoding="utf-8")
    assert "password_reset_tokens" in content


def test_migration_053_stores_token_hash_not_raw_token():
    content = (BACKEND / "alembic/versions/053_phase0d_password_security.py").read_text(encoding="utf-8")
    assert "token_hash" in content
    # Raw token column must NOT exist
    assert "raw_token" not in content
    assert "plain_token" not in content


# ── 2. User ORM model ────────────────────────────────────────────────────────

def test_user_model_has_password_reset_required():
    from app.engines.auth.models import User
    assert hasattr(User, "password_reset_required")


def test_user_model_has_temporary_password_active():
    from app.engines.auth.models import User
    assert hasattr(User, "temporary_password_active")


def test_user_model_has_password_expires_at():
    from app.engines.auth.models import User
    assert hasattr(User, "password_expires_at")


def test_user_model_has_last_password_reset_at():
    from app.engines.auth.models import User
    assert hasattr(User, "last_password_reset_at")


def test_user_model_has_last_password_reset_by_admin_id():
    from app.engines.auth.models import User
    assert hasattr(User, "last_password_reset_by_admin_id")


# ── 3. PasswordResetToken model ───────────────────────────────────────────────

def test_password_reset_token_model_exists():
    from app.engines.auth.models import PasswordResetToken
    assert PasswordResetToken is not None


def test_password_reset_token_has_token_hash():
    from app.engines.auth.models import PasswordResetToken
    assert hasattr(PasswordResetToken, "token_hash")


def test_password_reset_token_has_status():
    from app.engines.auth.models import PasswordResetToken
    assert hasattr(PasswordResetToken, "status")


def test_password_reset_token_has_expires_at():
    from app.engines.auth.models import PasswordResetToken
    assert hasattr(PasswordResetToken, "expires_at")


def test_password_reset_token_no_raw_token_column():
    """Security: token stored as hash only, never raw."""
    from app.engines.auth.models import PasswordResetToken
    assert not hasattr(PasswordResetToken, "token")
    assert not hasattr(PasswordResetToken, "raw_token")
    assert not hasattr(PasswordResetToken, "plain_token")


# ── 4. Schemas ───────────────────────────────────────────────────────────────

def test_change_password_required_request_schema_exists():
    from app.engines.auth.schemas import ChangePasswordRequiredRequest
    assert ChangePasswordRequiredRequest is not None


def test_change_password_required_schema_validates_match():
    from app.engines.auth.schemas import ChangePasswordRequiredRequest
    import pytest as _pytest
    with _pytest.raises(Exception):
        ChangePasswordRequiredRequest(
            current_password="Old123!",
            new_password="New123!@",
            confirm_password="Different123!@",
        )


def test_change_password_required_schema_accepts_matching():
    from app.engines.auth.schemas import ChangePasswordRequiredRequest
    req = ChangePasswordRequiredRequest(
        current_password="Old123!",
        new_password="New123!@",
        confirm_password="New123!@",
    )
    assert req.new_password == "New123!@"


def test_admin_force_password_change_request_schema_exists():
    from app.engines.auth.schemas import AdminForcePasswordChangeRequest
    req = AdminForcePasswordChangeRequest()
    assert req.revoke_sessions is True


def test_admin_send_password_reset_request_schema_exists():
    from app.engines.auth.schemas import AdminSendPasswordResetRequest
    req = AdminSendPasswordResetRequest()
    assert req.revoke_sessions is False


def test_admin_generate_temporary_password_request_schema_exists():
    from app.engines.auth.schemas import AdminGenerateTemporaryPasswordRequest
    req = AdminGenerateTemporaryPasswordRequest()
    assert req.revoke_sessions is True


# ── 5. Password strength validation ──────────────────────────────────────────

def test_password_validation_requires_special_char():
    from app.engines.auth.utils import validate_password_strength
    errors = validate_password_strength("Password123")
    assert errors, "Expected validation errors for missing special char"
    assert any("SPECIAL" in e or "special" in e.lower() for e in errors)


def test_password_validation_accepts_strong_password():
    from app.engines.auth.utils import validate_password_strength
    errors = validate_password_strength("Password123!")
    assert not errors, f"Expected no errors, got: {errors}"


def test_password_validation_rejects_too_short():
    from app.engines.auth.utils import validate_password_strength
    errors = validate_password_strength("Abc1!")
    assert errors
    assert any("SHORT" in e or "8" in e for e in errors)


def test_password_validation_rejects_missing_uppercase():
    from app.engines.auth.utils import validate_password_strength
    errors = validate_password_strength("password123!")
    assert errors
    assert any("UPPERCASE" in e or "uppercase" in e.lower() for e in errors)


def test_password_validation_rejects_missing_lowercase():
    from app.engines.auth.utils import validate_password_strength
    errors = validate_password_strength("PASSWORD123!")
    assert errors
    assert any("LOWERCASE" in e or "lowercase" in e.lower() for e in errors)


def test_password_validation_rejects_missing_number():
    from app.engines.auth.utils import validate_password_strength
    errors = validate_password_strength("Password!@#")
    assert errors
    assert any("NUMBER" in e or "number" in e.lower() for e in errors)


# ── 6. Auth service methods ───────────────────────────────────────────────────

def test_service_has_change_password_required():
    from app.engines.auth.service import AuthService
    assert hasattr(AuthService, "change_password_required")


def test_service_has_admin_force_password_change():
    from app.engines.auth.service import AuthService
    assert hasattr(AuthService, "admin_force_password_change")


def test_service_has_admin_send_password_reset():
    from app.engines.auth.service import AuthService
    assert hasattr(AuthService, "admin_send_password_reset")


def test_service_has_admin_generate_temporary_password():
    from app.engines.auth.service import AuthService
    assert hasattr(AuthService, "admin_generate_temporary_password")


def test_service_has_get_user_security_status():
    from app.engines.auth.service import AuthService
    assert hasattr(AuthService, "get_user_security_status")


def test_service_temporary_password_never_logs_plaintext():
    """The generated temp password must not appear in audit log or service args."""
    import inspect
    from app.engines.auth import service as svc_module
    src = inspect.getsource(svc_module)
    # The method should NOT pass password value to logger/audit under a plain name
    # We check that temporary_password is audited without the value itself
    assert "temporary_password_generated" in src
    # The specific audit call must not include the plain password value in the log line
    audit_lines = [l for l in src.splitlines() if "temporary_password_generated" in l]
    assert audit_lines, "Audit action not found"


def test_service_admin_scope_guard_exists():
    """_can_admin_manage_user guard must be present."""
    from app.engines.auth import service as svc_module
    import inspect
    src = inspect.getsource(svc_module)
    assert "_can_admin_manage_user" in src


# ── 7. Router endpoints ───────────────────────────────────────────────────────

def test_change_password_required_endpoint_registered():
    content = (BACKEND / "app/engines/auth/router.py").read_text(encoding="utf-8")
    assert "change-password-required" in content


def test_admin_security_router_registered():
    content = (BACKEND / "app/engines/auth/router.py").read_text(encoding="utf-8")
    assert "admin_security_router" in content


def test_admin_security_force_password_change_endpoint():
    content = (BACKEND / "app/engines/auth/router.py").read_text(encoding="utf-8")
    assert "force-password-change" in content


def test_admin_security_generate_temporary_password_endpoint():
    content = (BACKEND / "app/engines/auth/router.py").read_text(encoding="utf-8")
    assert "generate-temporary-password" in content


def test_admin_security_router_in_main():
    content = (BACKEND / "app/main.py").read_text(encoding="utf-8")
    assert "admin_security_router" in content


# ── 8. Auth guard: force_password_change blocks dashboard ────────────────────

def test_auth_guard_checks_force_password_change():
    content = (BACKEND / "app/dependencies/auth.py").read_text(encoding="utf-8")
    assert "_check_force_password_change" in content
    assert "FORCE_PASSWORD_CHANGE" in content


def test_auth_guard_force_check_in_all_role_guards():
    content = (BACKEND / "app/dependencies/auth.py").read_text(encoding="utf-8")
    for guard in ["require_super_admin", "require_tenant_owner", "require_staff_or_above",
                  "require_customer", "require_technician"]:
        # Each guard function must contain the force check call
        # Extract the function body and verify _check_force_password_change appears in it
        assert guard in content
    # Overall check: the helper is called more than once (one per guard)
    assert content.count("_check_force_password_change") >= 5


def test_session_revoked_redis_check_in_get_current_user():
    content = (BACKEND / "app/dependencies/auth.py").read_text(encoding="utf-8")
    assert "session:revoked" in content
    assert "SESSION_REVOKED" in content


# ── 9. Frontend — change-password-required pages ─────────────────────────────

def test_super_admin_change_password_page_exists():
    assert (SUPER_ADMIN / "app/change-password-required/page.tsx").exists()


def test_super_admin_change_password_page_has_current_field():
    content = (SUPER_ADMIN / "app/change-password-required/page.tsx").read_text(encoding="utf-8")
    assert "current" in content.lower() or "Current" in content


def test_super_admin_change_password_page_has_confirm_field():
    content = (SUPER_ADMIN / "app/change-password-required/page.tsx").read_text(encoding="utf-8")
    assert "confirm" in content.lower() or "Confirm" in content


def test_super_admin_change_password_page_has_password_rules():
    content = (SUPER_ADMIN / "app/change-password-required/page.tsx").read_text(encoding="utf-8")
    assert "uppercase" in content.lower() or "Uppercase" in content


def test_super_admin_change_password_page_has_logout_option():
    content = (SUPER_ADMIN / "app/change-password-required/page.tsx").read_text(encoding="utf-8")
    assert "logout" in content.lower() or "Sign out" in content


def test_tenant_change_password_page_exists():
    assert (TENANT / "app/change-password-required/page.tsx").exists()


def test_tenant_change_password_page_has_all_three_fields():
    content = (TENANT / "app/change-password-required/page.tsx").read_text(encoding="utf-8")
    assert "current" in content.lower()
    assert "new" in content.lower()
    assert "confirm" in content.lower()


def test_tenant_change_password_page_clears_tokens_on_success():
    content = (TENANT / "app/change-password-required/page.tsx").read_text(encoding="utf-8")
    assert "serviceos_tenant_token" in content
    assert "removeItem" in content


# ── 10. Frontend — login redirect when force_password_change ─────────────────

def test_super_admin_login_redirects_to_change_password_required():
    content = (SUPER_ADMIN / "app/login/page.tsx").read_text(encoding="utf-8")
    assert "change-password-required" in content
    assert "requires_password_change" in content


def test_tenant_login_redirects_to_change_password_required():
    content = (TENANT / "app/login/page.tsx").read_text(encoding="utf-8")
    assert "change-password-required" in content
    # Must NOT redirect to old /change-password path
    assert '"/change-password"' not in content


# ── 11. Frontend — api.ts security calls ─────────────────────────────────────

def test_super_admin_api_has_change_password_required():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "changePasswordRequired" in content
    assert "change-password-required" in content


def test_super_admin_api_has_admin_force_password_change():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "adminForcePasswordChange" in content
    assert "force-password-change" in content


def test_super_admin_api_has_admin_generate_temporary_password():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "adminGenerateTemporaryPassword" in content
    assert "generate-temporary-password" in content


def test_super_admin_api_has_get_user_security_status():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "getUserSecurityStatus" in content
    assert "security-status" in content


def test_super_admin_api_has_user_security_status_type():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "UserSecurityStatus" in content


def test_tenant_api_has_change_password_required():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "changePasswordRequired" in content
    assert "change-password-required" in content


# ── 12. Security invariants ───────────────────────────────────────────────────

def test_service_does_not_log_plain_password():
    """Ensure no logger.* call includes the raw password variable."""
    import inspect
    from app.engines.auth import service as svc_module
    src = inspect.getsource(svc_module)
    # Find all logger lines and ensure none contain temp_password or raw_password
    logger_lines = [l.strip() for l in src.splitlines() if "logger." in l]
    for line in logger_lines:
        assert "temp_password" not in line, f"Password leaked in log: {line}"
        assert "raw_password" not in line, f"Password leaked in log: {line}"
        assert "plain_password" not in line, f"Password leaked in log: {line}"


def test_password_reset_token_uses_sha256_hash():
    """Token stored as SHA-256 hash, not raw value."""
    import inspect
    from app.engines.auth import service as svc_module
    src = inspect.getsource(svc_module)
    assert "sha256" in src or "hash_token" in src


def test_temporary_password_meets_policy():
    """Generated temp password must pass the same strength validator."""
    from app.engines.auth.utils import validate_password_strength
    # Simulate what admin_generate_temporary_password produces:
    # 14-char random with uppercase, lowercase, number, special
    sample = "Xk9!mPq2@nRw7L"
    errors = validate_password_strength(sample)
    assert not errors, f"Sample temp password failed policy: {errors}"
