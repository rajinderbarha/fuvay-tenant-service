"""
MediaValidationService — file type, size, context, and actor validation.

All validation is server-side. Frontend file type constraints are UX only.
"""
from __future__ import annotations

import pathlib
from typing import Literal

from app.config import get_settings
from app.exceptions import ServiceOSException

# ── Allowed types per context ──────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "image/jpeg", "image/png", "image/webp",
}

ALLOWED_CHAT_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf",
}

ALWAYS_BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".htm", ".php", ".rb", ".py", ".pl", ".ps1",
    ".vbs", ".msi", ".dll", ".so", ".dylib",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".jar", ".war",
}

CONTEXT_RULES: dict[str, dict] = {
    "admin_profile_photo":          {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 5},
    "tenant_owner_profile_photo":   {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 5},
    "provider_business_logo":       {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 5},
    "provider_shop_photo":          {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 10},
    "provider_document":            {"allowed_types": ALLOWED_DOCUMENT_TYPES, "max_mb": 10},
    "staff_profile_photo":          {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 5},
    "customer_profile_photo":       {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 5},
    "customer_address_proof":       {"allowed_types": ALLOWED_DOCUMENT_TYPES, "max_mb": 10},
    "booking_issue_photo":          {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 10},
    "job_before_photo":             {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 10},
    "job_after_photo":              {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 10},
    "quote_attachment":             {"allowed_types": ALLOWED_DOCUMENT_TYPES, "max_mb": 10},
    "checklist_photo":              {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 10},
    "invoice_attachment":           {"allowed_types": ALLOWED_DOCUMENT_TYPES, "max_mb": 10},
    "payment_proof":                {"allowed_types": ALLOWED_DOCUMENT_TYPES, "max_mb": 10},
    "review_photo":                 {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 10},
    "complaint_evidence":           {"allowed_types": ALLOWED_DOCUMENT_TYPES, "max_mb": 10},
    "chat_attachment":              {"allowed_types": ALLOWED_CHAT_TYPES,     "max_mb": 10},
    "brand_logo":                   {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 5},
    "category_icon":                {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 2},
    "service_icon":                 {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 2},
    "issue_icon":                   {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 2},
    "checklist_icon":               {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 2},
    "question_icon":                {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 2},
    "global_service_icon":          {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 2},
    "banner_artwork":               {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 5},
    "marketing_asset":              {"allowed_types": ALLOWED_IMAGE_TYPES,    "max_mb": 20},
}

_SIGNATURES = {
    "application/pdf": lambda data: data.startswith(b"%PDF-"),
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    "image/gif": lambda data: data.startswith((b"GIF87a", b"GIF89a")),
}


class MediaValidationService:

    def validate_upload(
        self,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        media_context: str,
    ) -> None:
        """Run all upload validations. Raises ServiceOSException on failure."""
        self._validate_file_present(file_bytes)
        self._validate_context(media_context)
        self._validate_extension(original_filename)
        rules = CONTEXT_RULES[media_context]
        self._validate_mime_type(mime_type, rules["allowed_types"])
        self._validate_signature(file_bytes, mime_type)
        self._validate_size(len(file_bytes), rules["max_mb"])

    def validate_context(self, media_context: str) -> None:
        self._validate_context(media_context)

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_file_present(file_bytes: bytes) -> None:
        if not file_bytes:
            raise ServiceOSException(
                "MEDIA_FILE_REQUIRED",
                "No file content received."
            )

    @staticmethod
    def _validate_context(media_context: str) -> None:
        if media_context not in CONTEXT_RULES:
            raise ServiceOSException(
                "MEDIA_CONTEXT_NOT_ALLOWED",
                f"Unknown media context: '{media_context}'. "
                f"Allowed: {', '.join(sorted(CONTEXT_RULES))}",
            )

    @staticmethod
    def _validate_extension(filename: str) -> None:
        ext = pathlib.Path(filename).suffix.lower()
        if ext in ALWAYS_BLOCKED_EXTENSIONS:
            raise ServiceOSException(
                "MEDIA_EXTENSION_NOT_ALLOWED",
                f"File extension '{ext}' is not allowed for security reasons.",
            )

    @staticmethod
    def _validate_mime_type(mime_type: str, allowed: set[str]) -> None:
        if mime_type not in allowed:
            raise ServiceOSException(
                "MEDIA_TYPE_NOT_ALLOWED",
                f"MIME type '{mime_type}' is not allowed for this context. "
                f"Allowed: {', '.join(sorted(allowed))}",
            )

    @staticmethod
    def _validate_signature(file_bytes: bytes, mime_type: str) -> None:
        """Reject files whose bytes do not match their declared MIME type.

        Upload headers and filename extensions are client-controlled. These
        signatures cover every type currently accepted by CONTEXT_RULES.
        """
        matcher = _SIGNATURES.get(mime_type)
        if matcher and not matcher(file_bytes):
            raise ServiceOSException(
                "MEDIA_SIGNATURE_MISMATCH",
                "The file content does not match its declared file type.",
            )

    @staticmethod
    def _validate_size(size_bytes: int, max_mb: int) -> None:
        max_bytes = max_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise ServiceOSException(
                "MEDIA_FILE_TOO_LARGE",
                f"File size {size_bytes / (1024*1024):.1f} MB exceeds the "
                f"{max_mb} MB limit for this context.",
            )
        # Also check global max from config
        settings = get_settings()
        global_max_bytes = getattr(settings, "MAX_UPLOAD_SIZE_MB", 50) * 1024 * 1024
        if size_bytes > global_max_bytes:
            raise ServiceOSException(
                "MEDIA_FILE_TOO_LARGE",
                f"File size exceeds the global upload limit of "
                f"{global_max_bytes // (1024*1024)} MB.",
            )
