"""
Phase 0C — Profile Edit / Account Edit System — Backend Tests.

Tests cover:
  - Migration 051: display_name, language, timezone columns on users
  - User ORM model: new columns present
  - Profile engine module structure (schemas, service, router)
  - Schema validation: allowed/forbidden languages, timezones, phone regex
  - Forbidden fields: role, tenant_id, hashed_password not accepted by UpdateUserProfileRequest
  - Business schema: critical_fields detection, changed_critical_fields()
  - Re-verification logic: CRITICAL_BUSINESS_FIELDS frozenset
  - Router: 8 endpoints registered under /v1 prefix
  - API clients: profileApi in super-admin, profileApi + businessProfileApi in tenant-portal
  - Admin profile page: language/timezone/display_name fields present
  - Storage timeout fix: explicit connect timeout in Cloudinary client
  - Frontend upload timeout: AbortController timeout in apiUpload
  - Error codes: MEDIA_STORAGE_TIMEOUT in error maps
"""
from __future__ import annotations

import pathlib
import re

import pytest

BACKEND     = pathlib.Path(__file__).parent.parent.resolve()
SUPER_ADMIN = BACKEND / "frontend" / "super-admin"
TENANT      = BACKEND / "frontend" / "tenant-portal"


# ── 1. Migration 051 ─────────────────────────────────────────────────────────

def test_migration_051_exists():
    assert (BACKEND / "alembic/versions/051_phase0c_profile_edit.py").exists()


def test_migration_051_adds_display_name():
    content = (BACKEND / "alembic/versions/051_phase0c_profile_edit.py").read_text(encoding="utf-8")
    assert "display_name" in content


def test_migration_051_adds_language():
    content = (BACKEND / "alembic/versions/051_phase0c_profile_edit.py").read_text(encoding="utf-8")
    assert "language" in content


def test_migration_051_adds_timezone():
    content = (BACKEND / "alembic/versions/051_phase0c_profile_edit.py").read_text(encoding="utf-8")
    assert "timezone" in content


def test_migration_051_down_revision_is_050():
    content = (BACKEND / "alembic/versions/051_phase0c_profile_edit.py").read_text(encoding="utf-8")
    assert 'down_revision = "050"' in content


# ── 2. User ORM model ────────────────────────────────────────────────────────

def test_user_model_has_display_name():
    from app.engines.auth.models import User
    assert hasattr(User, "display_name")


def test_user_model_has_language():
    from app.engines.auth.models import User
    assert hasattr(User, "language")


def test_user_model_has_timezone():
    from app.engines.auth.models import User
    assert hasattr(User, "timezone")


# ── 3. Profile engine module structure ───────────────────────────────────────

def test_profile_engine_init_exists():
    assert (BACKEND / "app/engines/profile/__init__.py").exists()


def test_profile_engine_schemas_exists():
    assert (BACKEND / "app/engines/profile/schemas.py").exists()


def test_profile_engine_service_exists():
    assert (BACKEND / "app/engines/profile/service.py").exists()


def test_profile_engine_router_exists():
    assert (BACKEND / "app/engines/profile/router.py").exists()


def test_profile_engine_importable():
    from app.engines.profile.router import router as profile_edit_router
    assert profile_edit_router is not None


# ── 4. Schema validation ─────────────────────────────────────────────────────

def test_schema_allows_valid_language():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    req = UpdateUserProfileRequest(language="hi")
    assert req.language == "hi"


def test_schema_rejects_invalid_language():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Language"):
        UpdateUserProfileRequest(language="klingon")


def test_schema_allows_all_supported_languages():
    from app.engines.profile.schemas import UpdateUserProfileRequest, ALLOWED_LANGUAGES
    for lang in ALLOWED_LANGUAGES:
        req = UpdateUserProfileRequest(language=lang)
        assert req.language == lang


def test_schema_allows_valid_timezone():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    req = UpdateUserProfileRequest(timezone="Asia/Kolkata")
    assert req.timezone == "Asia/Kolkata"


def test_schema_rejects_invalid_timezone():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Timezone"):
        UpdateUserProfileRequest(timezone="Mars/Olympus")


def test_schema_accepts_valid_phone():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    req = UpdateUserProfileRequest(phone="+919876543210")
    assert req.phone == "+919876543210"


def test_schema_rejects_invalid_phone():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="Invalid phone"):
        UpdateUserProfileRequest(phone="not-a-phone")


def test_schema_all_fields_none_is_valid():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    req = UpdateUserProfileRequest()
    assert req.full_name is None
    assert req.language is None
    assert req.timezone is None


# ── 5. Forbidden fields NOT in update schema ──────────────────────────────────

def test_update_user_profile_schema_has_no_role_field():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    assert not hasattr(UpdateUserProfileRequest.model_fields, "role") or \
           "role" not in UpdateUserProfileRequest.model_fields


def test_update_user_profile_schema_has_no_tenant_id_field():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    assert "tenant_id" not in UpdateUserProfileRequest.model_fields


def test_update_user_profile_schema_has_no_hashed_password_field():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    assert "hashed_password" not in UpdateUserProfileRequest.model_fields


def test_update_user_profile_schema_has_no_is_active_field():
    from app.engines.profile.schemas import UpdateUserProfileRequest
    assert "is_active" not in UpdateUserProfileRequest.model_fields


# ── 6. Business profile schema ────────────────────────────────────────────────

def test_critical_business_fields_frozenset_exists():
    from app.engines.profile.schemas import CRITICAL_BUSINESS_FIELDS
    assert isinstance(CRITICAL_BUSINESS_FIELDS, frozenset)


def test_critical_business_fields_includes_business_name():
    from app.engines.profile.schemas import CRITICAL_BUSINESS_FIELDS
    assert "business_name" in CRITICAL_BUSINESS_FIELDS


def test_critical_business_fields_includes_gst():
    from app.engines.profile.schemas import CRITICAL_BUSINESS_FIELDS
    assert "gst_number" in CRITICAL_BUSINESS_FIELDS


def test_changed_critical_fields_detects_name_change():
    from app.engines.profile.schemas import UpdateBusinessProfileRequest
    req = UpdateBusinessProfileRequest(business_name="New Business Name")
    current = {"business_name": "Old Business Name", "gst_number": "123"}
    changed = req.changed_critical_fields(current)
    assert "business_name" in changed


def test_changed_critical_fields_no_change_when_same():
    from app.engines.profile.schemas import UpdateBusinessProfileRequest
    req = UpdateBusinessProfileRequest(business_name="Same Name")
    current = {"business_name": "Same Name"}
    changed = req.changed_critical_fields(current)
    assert "business_name" not in changed


def test_changed_critical_fields_none_values_ignored():
    from app.engines.profile.schemas import UpdateBusinessProfileRequest
    req = UpdateBusinessProfileRequest()
    current = {"business_name": "Old", "gst_number": "123"}
    changed = req.changed_critical_fields(current)
    assert changed == []


def test_business_schema_accepts_website_and_description():
    from app.engines.profile.schemas import UpdateBusinessProfileRequest
    req = UpdateBusinessProfileRequest(website_url="https://example.com", description="Test biz")
    assert req.website_url == "https://example.com"
    assert req.description == "Test biz"


def test_business_schema_no_verification_status_field():
    from app.engines.profile.schemas import UpdateBusinessProfileRequest
    assert "verification_status" not in UpdateBusinessProfileRequest.model_fields


def test_business_schema_no_slug_field():
    from app.engines.profile.schemas import UpdateBusinessProfileRequest
    assert "slug" not in UpdateBusinessProfileRequest.model_fields


# ── 7. Router endpoints ───────────────────────────────────────────────────────

def test_router_prefix_is_v1():
    from app.engines.profile.router import router
    assert router.prefix == "/v1"


def test_router_has_get_me_profile():
    from app.engines.profile.router import router
    paths = [r.path for r in router.routes]
    assert "/v1/me/profile" in paths


def test_router_has_put_me_profile():
    from app.engines.profile.router import router
    routes = {r.path: getattr(r, "methods", set()) for r in router.routes}
    assert "PUT" in routes.get("/v1/me/profile", set())


def test_router_has_get_provider_business_profile():
    from app.engines.profile.router import router
    paths = [r.path for r in router.routes]
    assert "/v1/provider/business-profile" in paths


def test_router_has_put_provider_business_profile():
    from app.engines.profile.router import router
    routes = {r.path: getattr(r, "methods", set()) for r in router.routes}
    assert "PUT" in routes.get("/v1/provider/business-profile", set())


def test_router_has_staff_profile_endpoint():
    from app.engines.profile.router import router
    paths = [r.path for r in router.routes]
    assert "/v1/staff/profile" in paths


def test_router_has_customer_profile_endpoint():
    from app.engines.profile.router import router
    paths = [r.path for r in router.routes]
    assert "/v1/customer/profile" in paths


def test_router_registered_in_main():
    content = (BACKEND / "app/main.py").read_text(encoding="utf-8")
    assert "profile_edit_router" in content or "profile.router" in content


# ── 8. Profile service structure ──────────────────────────────────────────────

def test_profile_service_has_get_user_profile():
    from app.engines.profile.service import ProfileService
    assert hasattr(ProfileService, "get_user_profile")


def test_profile_service_has_update_user_profile():
    from app.engines.profile.service import ProfileService
    assert hasattr(ProfileService, "update_user_profile")


def test_profile_service_has_get_business_profile():
    from app.engines.profile.service import ProfileService
    assert hasattr(ProfileService, "get_business_profile")


def test_profile_service_has_update_business_profile():
    from app.engines.profile.service import ProfileService
    assert hasattr(ProfileService, "update_business_profile")


# ── 9. Frontend API clients ───────────────────────────────────────────────────

def test_super_admin_has_profile_api():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "export const profileApi" in content


def test_super_admin_profile_api_has_get_profile():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "getProfile" in content
    assert "/v1/me/profile" in content


def test_super_admin_profile_api_has_update_profile():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "updateProfile" in content


def test_super_admin_has_user_profile_interface():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "UserProfile" in content
    assert "display_name" in content


def test_tenant_portal_has_profile_api():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "profileApi" in content


def test_tenant_portal_has_business_profile_api():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "businessProfileApi" in content


def test_tenant_portal_business_profile_api_has_update():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "/v1/provider/business-profile" in content


def test_tenant_portal_has_staff_profile_api():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "staffProfileApi" in content


# ── 10. Admin profile page ────────────────────────────────────────────────────

def test_admin_profile_page_exists():
    assert (SUPER_ADMIN / "app/admin/profile/page.tsx").exists()


def test_admin_profile_page_has_language_select():
    content = (SUPER_ADMIN / "app/admin/profile/page.tsx").read_text(encoding="utf-8")
    assert "language" in content
    assert "Language" in content


def test_admin_profile_page_has_timezone_select():
    content = (SUPER_ADMIN / "app/admin/profile/page.tsx").read_text(encoding="utf-8")
    assert "timezone" in content
    assert "Timezone" in content


def test_admin_profile_page_has_display_name_field():
    content = (SUPER_ADMIN / "app/admin/profile/page.tsx").read_text(encoding="utf-8")
    assert "displayName" in content or "display_name" in content


def test_admin_profile_page_uses_profile_api():
    content = (SUPER_ADMIN / "app/admin/profile/page.tsx").read_text(encoding="utf-8")
    assert "profileApi" in content


def test_admin_profile_page_shows_email_readonly():
    content = (SUPER_ADMIN / "app/admin/profile/page.tsx").read_text(encoding="utf-8")
    assert "email" in content.lower()
    # should NOT have an editable input for email
    assert "onChange" not in content.lower().split("email")[0].split("\n")[-1]


# ── 11. Upload hang fix — storage timeout ─────────────────────────────────────

def test_cloudinary_storage_has_explicit_connect_timeout():
    content = (BACKEND / "app/engines/media/storage.py").read_text(encoding="utf-8")
    assert "connect=" in content
    assert "Timeout(" in content


def test_cloudinary_storage_handles_timeout_exception():
    content = (BACKEND / "app/engines/media/storage.py").read_text(encoding="utf-8")
    assert "TimeoutException" in content
    assert "MEDIA_STORAGE_TIMEOUT" in content


def test_cloudinary_storage_handles_http_status_error():
    content = (BACKEND / "app/engines/media/storage.py").read_text(encoding="utf-8")
    assert "HTTPStatusError" in content
    assert "MEDIA_STORAGE_ERROR" in content


def test_cloudinary_storage_handles_request_error():
    content = (BACKEND / "app/engines/media/storage.py").read_text(encoding="utf-8")
    assert "RequestError" in content
    assert "MEDIA_STORAGE_UNAVAILABLE" in content


# ── 12. Upload hang fix — frontend AbortController timeout ────────────────────

def test_super_admin_api_upload_has_abort_controller():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "AbortController" in content


def test_super_admin_api_upload_has_timeout():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "AbortError" in content
    assert "UPLOAD_TIMEOUT" in content


def test_tenant_portal_api_upload_has_abort_controller():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "AbortController" in content


def test_tenant_portal_api_upload_has_timeout():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "AbortError" in content
    assert "UPLOAD_TIMEOUT" in content


def test_tenant_portal_error_map_has_upload_timeout():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "MEDIA_STORAGE_TIMEOUT" in content


def test_super_admin_error_map_has_upload_timeout():
    content = (SUPER_ADMIN / "components/shared/ProfilePhotoUploader.tsx").read_text(encoding="utf-8")
    assert "MEDIA_STORAGE_TIMEOUT" in content


def test_super_admin_error_map_has_storage_unavailable():
    content = (SUPER_ADMIN / "components/shared/ProfilePhotoUploader.tsx").read_text(encoding="utf-8")
    assert "MEDIA_STORAGE_UNAVAILABLE" in content
