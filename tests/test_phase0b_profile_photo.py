"""
Phase 0B — Profile Photo + Upload UX — Backend Tests (30 tests).

Tests cover:
  - Migration 050: business_logo_media_id + shop_photo_media_id on tenants
  - Tenant ORM model: new columns present
  - asset_service: new business logo / shop photo methods present
  - new_router: shop-photo endpoints registered
  - Admin / provider API client: profilePhotoApi present in super-admin
  - Tenant-portal API client: mediaAssetApi has logo/shop methods
  - ProfilePhotoUploader component files exist (both portals)
  - DefaultAvatar component exported from both portals
  - Profile pages exist (admin/profile, provider profile)
  - Topbar updated (DefaultAvatar import present in both layouts)
  - Error map completeness
"""
from __future__ import annotations

import pathlib

import pytest


BACKEND     = pathlib.Path(__file__).parent.parent.resolve()
SUPER_ADMIN = BACKEND / "frontend" / "super-admin"
TENANT      = BACKEND / "frontend" / "tenant-portal"

# ── 1. Migration 050 ─────────────────────────────────────────────────────────

def test_migration_050_exists():
    assert (BACKEND / "alembic/versions/050_phase0b_profile_photo_linking.py").exists()


def test_migration_050_adds_business_logo_media_id():
    content = (BACKEND / "alembic/versions/050_phase0b_profile_photo_linking.py").read_text(encoding="utf-8")
    assert "business_logo_media_id" in content
    assert "tenants" in content


def test_migration_050_adds_shop_photo_media_id():
    content = (BACKEND / "alembic/versions/050_phase0b_profile_photo_linking.py").read_text(encoding="utf-8")
    assert "shop_photo_media_id" in content


def test_migration_050_down_revision_is_049():
    content = (BACKEND / "alembic/versions/050_phase0b_profile_photo_linking.py").read_text(encoding="utf-8")
    assert 'down_revision = "049"' in content


# ── 2. Tenant ORM model ────────────────────────────────────────────────────────

def test_tenant_model_has_business_logo_media_id():
    from app.engines.tenant_engine.models import Tenant
    assert hasattr(Tenant, "business_logo_media_id")


def test_tenant_model_has_shop_photo_media_id():
    from app.engines.tenant_engine.models import Tenant
    assert hasattr(Tenant, "shop_photo_media_id")


# ── 3. MediaAssetService — business logo / shop photo methods ─────────────────

def test_asset_service_has_set_tenant_business_logo():
    from app.engines.media.asset_service import MediaAssetService
    assert hasattr(MediaAssetService, "set_tenant_business_logo")


def test_asset_service_has_remove_tenant_business_logo():
    from app.engines.media.asset_service import MediaAssetService
    assert hasattr(MediaAssetService, "remove_tenant_business_logo")


def test_asset_service_has_set_tenant_shop_photo():
    from app.engines.media.asset_service import MediaAssetService
    assert hasattr(MediaAssetService, "set_tenant_shop_photo")


def test_asset_service_has_remove_tenant_shop_photo():
    from app.engines.media.asset_service import MediaAssetService
    assert hasattr(MediaAssetService, "remove_tenant_shop_photo")


# ── 4. new_router.py — shop-photo endpoints ────────────────────────────────────

def test_router_has_shop_photo_post():
    content = (BACKEND / "app/engines/media/new_router.py").read_text(encoding="utf-8")
    assert "/provider/profile/shop-photo" in content


def test_router_has_shop_photo_delete():
    content = (BACKEND / "app/engines/media/new_router.py").read_text(encoding="utf-8")
    assert "remove_provider_shop_photo" in content or "remove_tenant_shop_photo" in content


def test_router_provider_logo_calls_set_tenant_business_logo():
    content = (BACKEND / "app/engines/media/new_router.py").read_text(encoding="utf-8")
    assert "set_tenant_business_logo" in content


# ── 5. Super-admin: profilePhotoApi ────────────────────────────────────────────

def test_super_admin_api_has_profile_photo_api():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "profilePhotoApi" in content


def test_super_admin_api_has_upload_own_photo():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "uploadOwnPhoto" in content


def test_super_admin_api_has_remove_own_photo():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "removeOwnPhoto" in content


def test_super_admin_api_has_media_asset_type():
    content = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8")
    assert "export interface MediaAsset" in content or "MediaAsset" in content


# ── 6. Tenant-portal: mediaAssetApi — logo / shop methods ─────────────────────

def test_tenant_api_has_upload_business_logo():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "uploadBusinessLogo" in content


def test_tenant_api_has_upload_shop_photo():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "uploadShopPhoto" in content


def test_tenant_api_has_remove_business_logo():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "removeBusinessLogo" in content


def test_tenant_api_has_upload_staff_photo():
    content = (TENANT / "lib/api.ts").read_text(encoding="utf-8")
    assert "uploadStaffPhoto" in content


# ── 7. ProfilePhotoUploader component files ────────────────────────────────────

def test_super_admin_has_profile_photo_uploader_component():
    assert (SUPER_ADMIN / "components/shared/ProfilePhotoUploader.tsx").exists()


def test_tenant_portal_has_profile_photo_uploader_component():
    assert (TENANT / "components/shared/ProfilePhotoUploader.tsx").exists()


def test_profile_photo_uploader_exports_default_avatar():
    for portal in [SUPER_ADMIN, TENANT]:
        content = (portal / "components/shared/ProfilePhotoUploader.tsx").read_text(encoding="utf-8")
        assert "export function DefaultAvatar" in content, f"DefaultAvatar missing in {portal.name}"


def test_profile_photo_uploader_has_error_map():
    for portal in [SUPER_ADMIN, TENANT]:
        content = (portal / "components/shared/ProfilePhotoUploader.tsx").read_text(encoding="utf-8")
        assert "MEDIA_FILE_TOO_LARGE" in content, f"error map missing in {portal.name}"
        assert "MEDIA_ACCESS_DENIED" in content


# ── 8. Profile pages ─────────────────────────────────────────────────────────

def test_admin_profile_page_exists():
    assert (SUPER_ADMIN / "app/admin/profile/page.tsx").exists()


def test_admin_profile_page_uses_profile_photo_uploader():
    content = (SUPER_ADMIN / "app/admin/profile/page.tsx").read_text(encoding="utf-8")
    assert "ProfilePhotoUploader" in content


def test_tenant_provider_profile_page_exists():
    assert (TENANT / "app/(tenant)/profile/page.tsx").exists()


# Logo and storefront-photo upload have moved twice now. They began as a generic
# media_context + ProfilePhotoUploader, became dedicated uploadBusinessLogo /
# uploadShopPhoto calls inside an inline HeroCard on the profile page, and now live in
# components/business-profile/MediaTab.tsx, back on ProfilePhotoUploader with explicit
# `provider_business` / `provider_shop` owner types.
#
# What matters to this test is that a tenant can still upload both, so it asserts the
# capability where it is actually implemented rather than pinning one call name to one
# file -- which is what made these fail when the profile page was recomposed from its
# design components, despite nothing about uploading having broken.
MEDIA_TAB = TENANT / "components/business-profile/MediaTab.tsx"


def test_tenant_provider_profile_page_has_business_logo_uploader():
    content = MEDIA_TAB.read_text(encoding="utf-8")
    assert "ProfilePhotoUploader" in content
    assert 'ownerType="provider_business"' in content
    assert "business_logo_media_id" in content


def test_tenant_provider_profile_page_has_shop_photo():
    content = MEDIA_TAB.read_text(encoding="utf-8")
    assert 'ownerType="provider_shop"' in content
    assert "shop_photo_media_id" in content


def test_media_tab_is_reachable_from_the_profile_page():
    """Guards the failure mode that hid all of this: the component existing but being
    imported by nothing, so the uploaders were unreachable in the running product."""
    page = (TENANT / "app/(tenant)/profile/page.tsx").read_text(encoding="utf-8")
    assert "components/business-profile/MediaTab" in page
    assert "<MediaTab" in page


# ── 9. Topbar / layout updates ────────────────────────────────────────────────

def test_admin_layout_imports_default_avatar():
    content = (SUPER_ADMIN / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
    assert "DefaultAvatar" in content


def test_tenant_layout_imports_default_avatar():
    content = (TENANT / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8")
    assert "DefaultAvatar" in content


def test_admin_topbar_links_to_profile_page():
    content = (SUPER_ADMIN / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
    assert "/admin/profile" in content


def test_tenant_topbar_links_to_profile_page():
    content = (TENANT / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8")
    assert "/profile" in content
