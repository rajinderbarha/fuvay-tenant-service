"""Cloudinary client — signed direct-upload params + delivery URL builder.
No cloudinary SDK dependency; signs upload params per Cloudinary's documented
SHA-1 signing scheme so the client can POST directly to Cloudinary's API.
"""
import hashlib
import time
import structlog
from app.config import get_settings

logger = structlog.get_logger("cloudinary_client")


def is_configured() -> bool:
    s = get_settings()
    return bool(s.CLOUDINARY_CLOUD_NAME and s.CLOUDINARY_API_KEY and s.CLOUDINARY_API_SECRET)


def build_upload_params(public_id: str, folder: str | None = None) -> dict:
    """Build signed params for a client-side direct upload to Cloudinary."""
    settings = get_settings()
    timestamp = int(time.time())

    sign_params = {"public_id": public_id, "timestamp": timestamp}
    if folder:
        sign_params["folder"] = folder

    param_string = "&".join(f"{k}={v}" for k, v in sorted(sign_params.items()))
    signature = hashlib.sha1((param_string + settings.CLOUDINARY_API_SECRET).encode("utf-8")).hexdigest()

    return {
        "upload_url": f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/auto/upload",
        "api_key": settings.CLOUDINARY_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
        "public_id": public_id,
        **({"folder": folder} if folder else {}),
    }


def build_delivery_url(public_id: str, resource_type: str = "image") -> str:
    settings = get_settings()
    return f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/{resource_type}/upload/{public_id}"
