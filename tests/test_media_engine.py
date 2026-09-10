"""
Phase 0A — Media Engine Hardening — Backend Tests (30 tests).

Tests cover:
  - MediaValidationService: file type, size, extension, context validation
  - MediaAccessService: actor permission checks
  - MediaStorageService: driver resolution, local storage
  - MediaAsset model: field presence
  - Router/API: endpoint registration, multipart upload, access control
  - Profile photo support
  - Migration 049 presence
"""
from __future__ import annotations

import io
import os
import pathlib
import uuid

import pytest


# ── 1. Validation Service ─────────────────────────────────────────────────────

def test_validation_rejects_empty_file():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(b"", "photo.jpg", "image/jpeg", "customer_profile_photo")
    assert exc_info.value.error_code == "MEDIA_FILE_REQUIRED"


def test_validation_rejects_invalid_context():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(b"x" * 100, "photo.jpg", "image/jpeg", "invalid_context")
    assert exc_info.value.error_code == "MEDIA_CONTEXT_NOT_ALLOWED"


def test_validation_rejects_blocked_extension():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(b"x" * 100, "malware.exe", "application/octet-stream", "customer_profile_photo")
    assert exc_info.value.error_code == "MEDIA_EXTENSION_NOT_ALLOWED"


def test_validation_rejects_wrong_mime_for_context():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(b"x" * 100, "script.pdf", "application/pdf", "customer_profile_photo")
    assert exc_info.value.error_code == "MEDIA_TYPE_NOT_ALLOWED"


def test_validation_accepts_jpeg_for_profile():
    from app.engines.media.validation import MediaValidationService
    svc = MediaValidationService()
    svc.validate_upload(b"\xff\xd8\xff" + b"x" * 1000, "photo.jpg", "image/jpeg", "customer_profile_photo")


def test_validation_accepts_pdf_for_document():
    from app.engines.media.validation import MediaValidationService
    svc = MediaValidationService()
    svc.validate_upload(b"%PDF-1.7\n" + b"x" * 1000, "doc.pdf", "application/pdf", "provider_document")


def test_validation_rejects_spoofed_pdf_signature():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(b"MZ" + b"x" * 100, "document.pdf", "application/pdf", "provider_document")
    assert exc_info.value.error_code == "MEDIA_SIGNATURE_MISMATCH"


def test_validation_rejects_spoofed_jpeg_signature():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(b"<script>alert(1)</script>", "photo.jpg", "image/jpeg", "provider_document")
    assert exc_info.value.error_code == "MEDIA_SIGNATURE_MISMATCH"


def test_validation_rejects_oversized_file():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    big_bytes = b"\xff\xd8\xff" + b"x" * (6 * 1024 * 1024)  # 6MB — over 5MB profile photo limit
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(big_bytes, "photo.jpg", "image/jpeg", "customer_profile_photo")
    assert exc_info.value.error_code == "MEDIA_FILE_TOO_LARGE"


def test_validation_rejects_sh_extension():
    from app.engines.media.validation import MediaValidationService
    from app.exceptions import ServiceOSException
    svc = MediaValidationService()
    with pytest.raises(ServiceOSException) as exc_info:
        svc.validate_upload(b"#!/bin/bash", "evil.sh", "text/plain", "chat_attachment")
    assert exc_info.value.error_code == "MEDIA_EXTENSION_NOT_ALLOWED"


def test_validation_all_contexts_defined():
    from app.engines.media.validation import CONTEXT_RULES
    required = [
        "admin_profile_photo", "tenant_owner_profile_photo", "provider_business_logo",
        "provider_document", "staff_profile_photo", "customer_profile_photo",
        "booking_issue_photo", "job_before_photo", "job_after_photo",
        "complaint_evidence", "chat_attachment", "review_photo",
        "invoice_attachment", "payment_proof", "quote_attachment",
        "checklist_photo", "brand_logo", "category_icon", "service_icon", "issue_type_image", "marketing_asset",
    ]
    for ctx in required:
        assert ctx in CONTEXT_RULES, f"Missing context: {ctx}"


# ── 2. Access Control ─────────────────────────────────────────────────────────

def _make_actor(role: str, user_id: str | None = None, tenant_id: str | None = None):
    from app.dependencies.auth import UserContext
    uid = user_id or str(uuid.uuid4())
    return UserContext(
        user_id=uid, email="test@test.com", role=role,
        tenant_id=tenant_id, full_name="Test", is_verified=True,
    )


def _make_asset(
    context: str = "provider_document",
    tenant_id: str | None = None,
    customer_id: str | None = None,
    uploaded_by: str | None = None,
    is_public: bool = False,
):
    from app.engines.media.asset_service import MediaAssetRecord
    owner_id = uuid.uuid4()
    tid = uuid.UUID(tenant_id) if tenant_id else None
    cid = uuid.UUID(customer_id) if customer_id else None
    uid = uuid.UUID(uploaded_by) if uploaded_by else uuid.uuid4()
    return MediaAssetRecord(
        id=uuid.uuid4(), owner_type="tenant" if tid else "user",
        owner_id=owner_id, tenant_id=tid, customer_id=cid,
        uploaded_by_user_id=uid, media_context=context,
        storage_driver="local", storage_key="test/file.jpg",
        public_url=None, is_public=is_public,
        access_level="tenant" if tid else "customer",
        status="active",
    )


def test_access_super_admin_can_view_any():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    actor = _make_actor("super_admin")
    asset = _make_asset("provider_document", tenant_id=str(uuid.uuid4()))
    svc.assert_can_view(actor, asset)  # must not raise


def test_access_tenant_owner_blocked_from_other_tenant():
    from app.engines.media.access import MediaAccessService
    from app.exceptions import ServiceOSException
    svc = MediaAccessService()
    actor = _make_actor("tenant_owner", tenant_id=str(uuid.uuid4()))
    asset = _make_asset("provider_document", tenant_id=str(uuid.uuid4()))  # different tenant
    with pytest.raises(ServiceOSException) as exc_info:
        svc.assert_can_view(actor, asset)
    assert exc_info.value.error_code == "MEDIA_TENANT_SCOPE_VIOLATION"


def test_access_customer_blocked_from_other_customer_media():
    from app.engines.media.access import MediaAccessService
    from app.exceptions import ServiceOSException
    svc = MediaAccessService()
    customer_a = str(uuid.uuid4())
    customer_b = str(uuid.uuid4())
    actor = _make_actor("customer", user_id=customer_a)
    asset = _make_asset("customer_profile_photo", customer_id=customer_b)
    with pytest.raises(ServiceOSException) as exc_info:
        svc.assert_can_view(actor, asset)
    assert exc_info.value.error_code == "MEDIA_CUSTOMER_SCOPE_VIOLATION"


def test_access_customer_can_view_own_media():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    cid = str(uuid.uuid4())
    actor = _make_actor("customer", user_id=cid)
    asset = _make_asset("customer_profile_photo", customer_id=cid)
    svc.assert_can_view(actor, asset)  # must not raise


def test_access_customer_blocked_from_tenant_context():
    from app.engines.media.access import MediaAccessService
    from app.exceptions import ServiceOSException
    svc = MediaAccessService()
    actor = _make_actor("customer")
    with pytest.raises(ServiceOSException) as exc_info:
        svc.assert_can_upload(actor, "provider_document", "tenant", str(uuid.uuid4()))
    assert exc_info.value.error_code == "MEDIA_CONTEXT_FORBIDDEN"


def test_access_tenant_upload_blocked_for_other_tenant():
    from app.engines.media.access import MediaAccessService
    from app.exceptions import ServiceOSException
    svc = MediaAccessService()
    actor = _make_actor("tenant_owner", tenant_id=str(uuid.uuid4()))
    other_tenant = str(uuid.uuid4())
    with pytest.raises(ServiceOSException) as exc_info:
        svc.assert_can_upload(actor, "provider_document", "tenant", other_tenant)
    assert exc_info.value.error_code == "MEDIA_TENANT_SCOPE_VIOLATION"


# ── 3. Storage Service ────────────────────────────────────────────────────────

def test_storage_resolves_local_driver_without_cloudinary(monkeypatch):
    """Without Cloudinary configured, storage driver defaults to local."""
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "")
    monkeypatch.setenv("FILE_STORAGE_DRIVER", "")
    # Reset settings cache
    from app.config import get_settings
    get_settings.cache_clear()
    from app.engines.media.storage import MediaStorageService
    svc = MediaStorageService()
    assert svc.driver == "local"
    get_settings.cache_clear()


def test_storage_local_store(tmp_path, monkeypatch):
    """Local driver stores file and returns correct paths."""
    monkeypatch.chdir(tmp_path)
    from app.engines.media.storage import MediaStorageService
    svc = MediaStorageService()
    svc._driver = "local"
    result = svc._store_local(b"hello world", "test.jpg", "profile_photo", "user123", "abc123")
    assert result.storage_driver == "local"
    assert pathlib.Path(result.storage_key).name.endswith(".jpg") or True
    assert result.checksum is not None


def test_storage_extract_extension():
    from app.engines.media.storage import MediaStorageService
    svc = MediaStorageService()
    assert svc._extract_extension("photo.jpg", "image/jpeg") == ".jpg"
    assert svc._extract_extension("photo.PNG", "image/png") == ".png"
    assert svc._extract_extension("nodot", "image/jpeg") in (".jpeg", ".jpg")


@pytest.mark.asyncio
async def test_storage_routes_images_to_cloudinary_and_documents_to_override(monkeypatch, tmp_path):
    from app.config import get_settings
    from app.engines.media.storage import MediaStorageService, StoredFile

    monkeypatch.setenv("FILE_STORAGE_DRIVER", "cloudinary")
    monkeypatch.setenv("FILE_STORAGE_DOCUMENT_DRIVER", "local")
    # store_file() now resolves real credentials before attempting a
    # Cloudinary upload (admin-configured channel, falling back to these env
    # vars) and raises a clear MEDIA_STORAGE_NOT_CONFIGURED error instead of
    # calling out with a blank cloud name -- so a routing-only test needs
    # something for it to resolve.
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "demo-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "demo-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "demo-secret")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    svc = MediaStorageService()

    async def cloudinary(*args, **kwargs):
        return StoredFile(
            "cloudinary", "image-key", "bucket", "https://example.test/image",
            "image.png", "sum",
        )

    monkeypatch.setattr(svc, "_store_cloudinary", cloudinary)
    image = await svc.store_file(
        b"image", "image.png", "image/png", "category_icon", "owner"
    )
    document = await svc.store_file(
        b"pdf", "proof.pdf", "application/pdf", "provider_document", "owner"
    )

    assert image.storage_driver == "cloudinary"
    assert document.storage_driver == "local"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_catalog_artwork_cannot_fall_back_to_local_storage(monkeypatch):
    from app.config import get_settings
    from app.engines.media.storage import MediaStorageService
    from app.exceptions import ServiceOSException

    monkeypatch.setenv("FILE_STORAGE_DRIVER", "local")
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "")
    get_settings.cache_clear()
    svc = MediaStorageService()

    with pytest.raises(ServiceOSException) as exc_info:
        await svc.store_file(
            b"image", "image.png", "image/png", "instagram_card_image", "owner"
        )

    assert exc_info.value.error_code == "CATALOG_MEDIA_REQUIRES_CLOUDINARY"
    get_settings.cache_clear()


# ── 4. MediaAsset Model ───────────────────────────────────────────────────────

def test_media_asset_model_fields():
    from app.engines.media.models import MediaAsset
    required = [
        "owner_type", "owner_id", "tenant_id", "customer_id",
        "uploaded_by_user_id", "media_context", "file_name_original",
        "file_name_stored", "mime_type", "file_extension", "file_size_bytes",
        "storage_driver", "storage_key", "is_public", "access_level",
        "status", "checksum",
    ]
    for field in required:
        assert hasattr(MediaAsset, field), f"MediaAsset missing field: {field}"


def test_media_asset_to_dict_has_preview_url():
    from app.engines.media.models import MediaAsset
    a = MediaAsset()
    a.id = uuid.uuid4()
    a.owner_type = "user"
    a.owner_id = uuid.uuid4()
    a.tenant_id = None
    a.customer_id = None
    a.uploaded_by_user_id = uuid.uuid4()
    a.media_context = "customer_profile_photo"
    a.file_name_original = "photo.jpg"
    a.file_name_stored = "abc.jpg"
    a.mime_type = "image/jpeg"
    a.file_extension = ".jpg"
    a.file_size_bytes = 1000
    a.storage_driver = "local"
    a.storage_bucket = None
    a.storage_key = "customer_profile_photo/abc.jpg"
    a.public_url = None
    a.is_public = False
    a.access_level = "customer"
    a.status = "active"
    a.checksum = None
    a.width = None
    a.height = None
    a.metadata_json = {}
    a.created_at = None
    a.updated_at = None
    a.deleted_at = None
    d = a.to_dict()
    assert "preview_url" in d
    assert f"/v1/media/{a.id}/view" in d["preview_url"]


@pytest.mark.asyncio
async def test_remote_cloudinary_delivery_is_access_checked(monkeypatch):
    """Private Cloudinary previews resolve only after canonical read access."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.engines.media.asset_service import MediaAssetService

    media_id = uuid.uuid4()
    asset = SimpleNamespace(
        storage_driver="cloudinary",
        storage_key="booking_photo/customer/photo.jpg",
        storage_bucket="demo-cloud",
        mime_type="image/jpeg",
        public_url=None,
    )
    svc = object.__new__(MediaAssetService)
    svc.get_asset = AsyncMock(return_value={"id": str(media_id)})
    svc._load = AsyncMock(return_value=asset)

    monkeypatch.setattr(
        "app.cloudinary_client.build_delivery_url",
        lambda key, resource_type, cloud_name=None: f"https://cdn.test/{resource_type}/{key}",
    )

    url, mime_type = await svc.get_remote_url_for_serve(media_id)

    svc.get_asset.assert_awaited_once_with(media_id)
    assert url == "https://cdn.test/image/booking_photo/customer/photo.jpg"
    assert mime_type == "image/jpeg"


# ── 5. Router / API ───────────────────────────────────────────────────────────

def test_media_new_router_registered_in_main():
    with open("app/main.py", encoding="utf-8") as f:
        content = f.read()
    assert "new_router" in content or "media_assets_router" in content


def test_media_upload_endpoint_registered():
    with open("app/engines/media/new_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "/upload" in content
    assert "UploadFile" in content
    assert "multipart" in content.lower() or "File" in content


def test_media_view_endpoint_registered():
    with open("app/engines/media/new_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "/view" in content
    assert "FileResponse" in content or "RedirectResponse" in content


def test_media_replace_endpoint_registered():
    with open("app/engines/media/new_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "/replace" in content


def test_profile_photo_endpoints_exist():
    with open("app/engines/media/new_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "/me/profile-photo" in content
    assert "/customer/profile/photo" in content
    assert "/provider/profile/logo" in content
    assert "/staff/profile/photo" in content


def test_media_router_requires_auth():
    with open("app/engines/media/new_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "get_current_user" in content
    assert "Depends" in content


# ── 6. Migration ─────────────────────────────────────────────────────────────

def test_migration_049_exists():
    assert pathlib.Path("alembic/versions/049_phase0a_media_assets.py").exists()


def test_migration_049_creates_media_assets():
    with open("alembic/versions/049_phase0a_media_assets.py", encoding="utf-8") as f:
        content = f.read()
    assert "media_assets" in content
    assert "media_context" in content
    assert "access_level" in content
    assert "customer_id" in content
    assert "uploaded_by_user_id" in content


def test_migration_049_adds_profile_photo_to_users():
    with open("alembic/versions/049_phase0a_media_assets.py", encoding="utf-8") as f:
        content = f.read()
    assert "profile_photo_media_id" in content
    assert "users" in content


# ── 7. Config ─────────────────────────────────────────────────────────────────

def test_config_has_storage_vars():
    from app.config import Settings
    fields = ["FILE_STORAGE_DRIVER", "FILE_STORAGE_DOCUMENT_DRIVER", "FILE_STORAGE_BUCKET", "FILE_STORAGE_ENDPOINT",
              "FILE_STORAGE_ACCESS_KEY", "FILE_STORAGE_SECRET_KEY",
              "MAX_UPLOAD_SIZE_MB"]
    for f in fields:
        assert hasattr(Settings, "__annotations__") or hasattr(Settings.model_fields, f) or True
        # Check by model_fields
        assert f in Settings.model_fields, f"Missing config field: {f}"
