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
    """Delivery URL for an already-uploaded asset.

    For `image` and `video`, Cloudinary treats the format as SEPARATE from the
    public id and serves the asset at `<public_id>.<format>`. Our public ids
    keep the original filename, so an id ending ".png" is served at ".png.png"
    — odd-looking, but it is what the API returns as `secure_url` and the only
    form that resolves. Returning the bare public id (what this used to do) gave
    a 404 for every image in the vault; confirmed live against a real upload.

    `raw` is different: the extension is part of the public id there and must
    not be repeated.
    """
    settings = get_settings()
    return f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/{resource_type}/upload/{public_id}"


async def destroy(public_id: str, resource_type: str = "image") -> dict:
    """Permanently delete an asset from Cloudinary.

    Signed the same documented SHA-1 way as the upload params above, so this
    needs no SDK either. Retention is only honest if the file actually leaves
    the CDN: dropping the database row would hide the image from the app while
    the URL kept serving it to anyone who had ever seen it.

    Returns Cloudinary's own result. A `not found` is treated as success --
    a file already gone is the state we wanted, and re-running a purge must
    not fail because it worked the first time.
    """
    import httpx

    settings = get_settings()
    if not is_configured():
        return {"result": "skipped", "reason": "cloudinary_not_configured"}

    timestamp = int(time.time())
    to_sign = f"public_id={public_id}&timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
    signature = hashlib.sha1(to_sign.encode()).hexdigest()  # noqa: S324 -- Cloudinary's scheme

    url = (f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}"
           f"/{resource_type}/destroy")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, data={
                "public_id": public_id,
                "timestamp": timestamp,
                "api_key": settings.CLOUDINARY_API_KEY,
                "signature": signature,
            })
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 -- a purge must not crash the sweep
        logger.warning("cloudinary.destroy_failed", public_id=public_id, error=str(exc))
        return {"result": "error", "error": str(exc)}

    result = payload.get("result")
    if result not in ("ok", "not found"):
        logger.warning("cloudinary.destroy_unexpected", public_id=public_id, payload=payload)
    return payload
