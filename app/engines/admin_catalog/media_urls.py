"""Validation for durable, public catalog artwork URLs."""
from __future__ import annotations

from urllib.parse import urlparse

from app.exceptions import ServiceOSException


def cloudinary_catalog_url(value: object, field_name: str) -> str | None:
    """Return a normalized Cloudinary delivery URL or reject the write.

    Catalog forms upload through the Media engine. This guard closes the API
    bypass where a client could save a local path or an unrelated remote URL
    directly into an icon/image field.
    """
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    parsed = urlparse(normalized)
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() != "res.cloudinary.com"
        or "/upload/" not in parsed.path
    ):
        raise ServiceOSException(
            "CATALOG_MEDIA_CLOUDINARY_REQUIRED",
            f"{field_name} must be uploaded to Cloudinary through the catalog media picker.",
            status_code=422,
        )
    return normalized
