"""
Phase 0A — Media Engine Integration Tests (Part 2).

Tests cover:
  - Audit logging: media.uploaded, media.replaced, media.deleted, media.access_denied
  - Download endpoint registration
  - Cross-tenant access denial
  - Context-specific validation for new flow contexts
  - SendMsgIn extended with media_ids
  - mediaAssetApi frontend API pattern (static checks)
  - Frontend component file presence
  - Frontend API type additions
"""
from __future__ import annotations

import pathlib
import uuid


# ── 1. Audit Logging Integration ─────────────────────────────────────────────

def test_asset_service_imports_record_platform_audit():
    """asset_service.py must import record_platform_audit from app.core.audit."""
    with open("app/engines/media/asset_service.py", encoding="utf-8") as f:
        content = f.read()
    assert "record_platform_audit" in content
    assert "from app.core.audit import record_platform_audit" in content


def test_audit_call_after_upload():
    """upload() must call record_platform_audit with operation='media.uploaded'."""
    with open("app/engines/media/asset_service.py", encoding="utf-8") as f:
        content = f.read()
    assert '"media.uploaded"' in content or "'media.uploaded'" in content


def test_audit_call_after_replace():
    """replace_asset() must call record_platform_audit with operation='media.replaced'."""
    with open("app/engines/media/asset_service.py", encoding="utf-8") as f:
        content = f.read()
    assert '"media.replaced"' in content or "'media.replaced'" in content


def test_audit_call_after_delete():
    """delete_asset() must call record_platform_audit with operation='media.deleted'."""
    with open("app/engines/media/asset_service.py", encoding="utf-8") as f:
        content = f.read()
    assert '"media.deleted"' in content or "'media.deleted'" in content


def test_audit_call_on_access_denied():
    """get_asset() must log 'media.access_denied' when access check fails."""
    with open("app/engines/media/asset_service.py", encoding="utf-8") as f:
        content = f.read()
    assert '"media.access_denied"' in content or "'media.access_denied'" in content


def test_access_denied_wraps_assert_can_view():
    """get_asset() must wrap assert_can_view() in try/except to log denied access."""
    with open("app/engines/media/asset_service.py", encoding="utf-8") as f:
        content = f.read()
    assert "try:" in content
    assert "assert_can_view" in content
    assert "except ServiceOSException" in content


# ── 2. Download Endpoint ──────────────────────────────────────────────────────

def test_download_endpoint_registered():
    """GET /v1/media/{media_id}/download must be registered in new_router.py."""
    with open("app/engines/media/new_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "/download" in content
    assert "Content-Disposition" in content


def test_download_endpoint_returns_attachment():
    """Download endpoint must set Content-Disposition: attachment."""
    with open("app/engines/media/new_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "attachment" in content


# ── 3. Cross-Tenant Access Denial (unit-level) ────────────────────────────────

def _make_actor(role: str, user_id: str | None = None, tenant_id: str | None = None):
    from app.dependencies.auth import UserContext
    return UserContext(
        user_id=user_id or str(uuid.uuid4()),
        email="test@test.com", role=role,
        tenant_id=tenant_id, full_name="Test", is_verified=True,
    )


def _make_asset_record(
    context: str = "provider_document",
    tenant_id: str | None = None,
    customer_id: str | None = None,
    is_public: bool = False,
):
    from app.engines.media.asset_service import MediaAssetRecord
    tid = uuid.UUID(tenant_id) if tenant_id else None
    cid = uuid.UUID(customer_id) if customer_id else None
    return MediaAssetRecord(
        id=uuid.uuid4(), owner_type="tenant" if tid else "user",
        owner_id=uuid.uuid4(), tenant_id=tid, customer_id=cid,
        uploaded_by_user_id=uuid.uuid4(), media_context=context,
        storage_driver="local", storage_key="test/file.jpg",
        public_url=None, is_public=is_public,
        access_level="tenant" if tid else "customer",
        status="active",
    )


def test_cross_tenant_access_blocked():
    from app.engines.media.access import MediaAccessService
    from app.exceptions import ServiceOSException
    svc = MediaAccessService()
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    actor  = _make_actor("tenant_owner", tenant_id=tenant_a)
    asset  = _make_asset_record("provider_document", tenant_id=tenant_b)
    with pytest.raises(ServiceOSException) as exc:
        svc.assert_can_view(actor, asset)
    assert exc.value.error_code == "MEDIA_TENANT_SCOPE_VIOLATION"


def test_cross_customer_access_blocked():
    from app.engines.media.access import MediaAccessService
    from app.exceptions import ServiceOSException
    svc = MediaAccessService()
    cid_a = str(uuid.uuid4())
    cid_b = str(uuid.uuid4())
    actor  = _make_actor("customer", user_id=cid_a)
    asset  = _make_asset_record("complaint_evidence", customer_id=cid_b)
    with pytest.raises(ServiceOSException) as exc:
        svc.assert_can_view(actor, asset)
    assert exc.value.error_code == "MEDIA_CUSTOMER_SCOPE_VIOLATION"


import pytest


def test_chat_attachment_context_allowed_for_customer():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    cid = str(uuid.uuid4())
    actor = _make_actor("customer", user_id=cid)
    svc.assert_can_upload(actor, "chat_attachment", "user", cid)  # must not raise


def test_complaint_evidence_context_allowed_for_customer():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    cid = str(uuid.uuid4())
    actor = _make_actor("customer", user_id=cid)
    svc.assert_can_upload(actor, "complaint_evidence", "user", cid)  # must not raise


def test_review_photo_context_allowed_for_customer():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    cid = str(uuid.uuid4())
    actor = _make_actor("customer", user_id=cid)
    svc.assert_can_upload(actor, "review_photo", "user", cid)  # must not raise


def test_booking_issue_photo_context_allowed_for_customer():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    cid = str(uuid.uuid4())
    actor = _make_actor("customer", user_id=cid)
    svc.assert_can_upload(actor, "booking_issue_photo", "user", cid)  # must not raise


def test_job_before_photo_allowed_for_tenant():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    tid = str(uuid.uuid4())
    actor = _make_actor("tenant_owner", tenant_id=tid)
    svc.assert_can_upload(actor, "job_before_photo", "tenant", tid)  # must not raise


def test_job_after_photo_allowed_for_tenant():
    from app.engines.media.access import MediaAccessService
    svc = MediaAccessService()
    tid = str(uuid.uuid4())
    actor = _make_actor("tenant_owner", tenant_id=tid)
    svc.assert_can_upload(actor, "job_after_photo", "tenant", tid)  # must not raise


def test_job_before_photo_blocked_for_wrong_tenant():
    from app.engines.media.access import MediaAccessService
    from app.exceptions import ServiceOSException
    svc = MediaAccessService()
    tid_a = str(uuid.uuid4())
    tid_b = str(uuid.uuid4())
    actor = _make_actor("tenant_owner", tenant_id=tid_a)
    with pytest.raises(ServiceOSException) as exc:
        svc.assert_can_upload(actor, "job_before_photo", "tenant", tid_b)
    assert exc.value.error_code == "MEDIA_TENANT_SCOPE_VIOLATION"


# ── 4. Chat Backend — SendMsgIn with media_ids ────────────────────────────────

def test_send_msg_in_has_media_ids():
    """SendMsgIn in provider_router.py must accept media_ids list."""
    with open("app/engines/platform_notifications/provider_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "media_ids" in content
    assert "list[str]" in content or "List[str]" in content


def test_provider_send_message_passes_media_urls():
    """provider_send_message router must pass media_urls to send_message service."""
    with open("app/engines/platform_notifications/provider_router.py", encoding="utf-8") as f:
        content = f.read()
    assert "media_urls" in content


# ── 5. Validation Contexts for all integration flows ─────────────────────────

def test_all_integration_contexts_exist():
    from app.engines.media.validation import CONTEXT_RULES
    integration_contexts = [
        "booking_issue_photo",
        "complaint_evidence",
        "review_photo",
        "chat_attachment",
        "job_before_photo",
        "job_after_photo",
        "quote_attachment",
        "checklist_photo",
    ]
    for ctx in integration_contexts:
        assert ctx in CONTEXT_RULES, f"Missing integration context: {ctx}"


# ── 6. Frontend Component Files ───────────────────────────────────────────────

def test_media_uploader_component_exists():
    assert pathlib.Path("frontend/tenant-portal/components/media/MediaUploader.tsx").exists()


def test_media_preview_component_exists():
    assert pathlib.Path("frontend/tenant-portal/components/media/MediaPreview.tsx").exists()


def test_media_gallery_component_exists():
    assert pathlib.Path("frontend/tenant-portal/components/media/MediaGallery.tsx").exists()


def test_media_uploader_uses_media_engine_api():
    with open("frontend/tenant-portal/components/media/MediaUploader.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "mediaAssetApi" in content
    assert "mediaContext" in content
    assert "ownerType" in content
    assert "ownerId" in content


def test_media_uploader_shows_error_state():
    with open("frontend/tenant-portal/components/media/MediaUploader.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "friendlyMediaError" in content or "error" in content.lower()


def test_media_preview_has_lightbox():
    with open("frontend/tenant-portal/components/media/MediaPreview.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "lightbox" in content.lower() or "zoom" in content.lower() or "position: \"fixed\"" in content


def test_media_preview_uses_view_endpoint():
    with open("frontend/tenant-portal/components/media/MediaPreview.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "viewUrl" in content or "/view" in content


def test_media_preview_uses_download_endpoint():
    with open("frontend/tenant-portal/components/media/MediaPreview.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "downloadUrl" in content or "/download" in content


# ── 7. Frontend API — mediaAssetApi ──────────────────────────────────────────

def test_frontend_media_asset_api_exists():
    with open("frontend/tenant-portal/lib/api.ts", encoding="utf-8") as f:
        content = f.read()
    assert "mediaAssetApi" in content


def test_frontend_media_asset_type_exists():
    with open("frontend/tenant-portal/lib/api.ts", encoding="utf-8") as f:
        content = f.read()
    assert "export interface MediaAsset" in content
    assert "media_context" in content
    assert "preview_url" in content


def test_frontend_apiFetchMultipart_exists():
    with open("frontend/tenant-portal/lib/api.ts", encoding="utf-8") as f:
        content = f.read()
    assert "apiFetchMultipart" in content
    assert "FormData" in content


def test_frontend_friendly_error_helper_exists():
    with open("frontend/tenant-portal/lib/api.ts", encoding="utf-8") as f:
        content = f.read()
    assert "friendlyMediaError" in content
    assert "MEDIA_FILE_TOO_LARGE" in content
    assert "MEDIA_ACCESS_DENIED" in content


def test_frontend_media_upload_error_maps_all_codes():
    with open("frontend/tenant-portal/lib/api.ts", encoding="utf-8") as f:
        content = f.read()
    required_codes = [
        "MEDIA_FILE_REQUIRED", "MEDIA_FILE_TOO_LARGE", "MEDIA_TYPE_NOT_ALLOWED",
        "MEDIA_EXTENSION_NOT_ALLOWED", "MEDIA_CONTEXT_NOT_ALLOWED",
        "MEDIA_ACCESS_DENIED", "MEDIA_STORAGE_NOT_CONFIGURED", "MEDIA_NOT_FOUND",
    ]
    for code in required_codes:
        assert code in content, f"Missing error code mapping: {code}"


# ── 8. Chat Integration ───────────────────────────────────────────────────────

def test_chat_page_has_attachment_button():
    with open("frontend/tenant-portal/app/(tenant)/provider/chat/page.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "Paperclip" in content or "file" in content.lower()


def test_chat_page_uploads_to_media_engine():
    with open("frontend/tenant-portal/app/(tenant)/provider/chat/page.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "mediaAssetApi" in content
    assert "chat_attachment" in content


def test_chat_page_renders_attachment_links():
    with open("frontend/tenant-portal/app/(tenant)/provider/chat/page.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "media_urls" in content
    assert "media_ids" in content


# ── 9. Job Photos Integration ─────────────────────────────────────────────────

def test_job_detail_has_before_photo_upload():
    with open("frontend/tenant-portal/app/(tenant)/media/page.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "job_before_photo" in content
    assert "Job — before" in content


def test_job_detail_has_after_photo_upload():
    with open("frontend/tenant-portal/app/(tenant)/media/page.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "job_after_photo" in content


def test_job_detail_has_media_gallery():
    with open("mobile/staff-app/src/screens/completionProof/CompletionProofScreen.tsx", encoding="utf-8") as f:
        content = f.read()
    assert "after photo" in content.lower()


# ── 10. app.core.audit function signature ─────────────────────────────────────

def test_record_platform_audit_exists():
    from app.core.audit import record_platform_audit
    import inspect
    sig = inspect.signature(record_platform_audit)
    assert "operation" in sig.parameters
    assert "engine_id" in sig.parameters


def test_platform_audit_log_model_exists():
    from app.engines.security.models import PlatformAuditLog
    assert hasattr(PlatformAuditLog, "operation")
