"""
MediaStorageService — pluggable storage backend.

Drivers: local | cloudinary | s3_compatible | cloudflare_r2
Selected by FILE_STORAGE_DRIVER. When it is unset, configured Cloudinary
credentials take precedence and local disk is only the development fallback.

Local driver stores files in ./uploads/ and serves them via FastAPI StaticFiles.
"""
from __future__ import annotations

import mimetypes
import pathlib
import secrets
import time
import hashlib
import structlog
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

logger = structlog.get_logger("media.storage")

StorageDriver = Literal["local", "cloudinary", "s3_compatible", "cloudflare_r2"]

UPLOADS_DIR = pathlib.Path("uploads")  # relative to working dir; create if missing


@dataclass
class StoredFile:
    storage_driver: str
    storage_key: str
    storage_bucket: str | None
    public_url: str | None
    file_name_stored: str
    checksum: str | None


class MediaStorageService:
    """
    Single entry point for all file storage operations.
    The driver is chosen from FILE_STORAGE_DRIVER (or 'cloudinary' if Cloudinary is configured
    and no explicit FILE_STORAGE_DRIVER is set).
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        """`db` lets store_file() prefer the admin-configured, encrypted
        Cloudinary channel (super admin -> Notification & Provider Settings,
        same pattern as Razorpay/WhatsApp) over the static CLOUDINARY_* env
        vars -- see _resolve_cloudinary_credentials. Pass the request's
        session so a live admin-console rotation takes effect immediately,
        with no restart. Callers with no request session (e.g. a background
        job reading a local path) can omit it and fall back to env-only."""
        self._db = db
        self._settings = get_settings()
        self._driver, self._driver_pinned = self._resolve_driver()
        self._document_driver, self._document_driver_pinned = self._resolve_document_driver()

    def _resolve_driver(self) -> tuple[StorageDriver, bool]:
        """Returns (driver, pinned). pinned=True means an operator explicitly
        chose this via FILE_STORAGE_DRIVER -- store_file() must never
        silently override an explicit choice (e.g. a deliberate "local"),
        only the auto-selected default."""
        explicit = getattr(self._settings, "FILE_STORAGE_DRIVER", "").strip().lower()
        if explicit in ("local", "s3_compatible", "cloudflare_r2", "cloudinary"):
            return explicit, True  # type: ignore[return-value]
        # Auto-select: prefer Cloudinary if configured via env. The
        # admin-configured channel is checked again, per-upload, in
        # store_file() -- this sync path only covers the env-var case so
        # __init__ doesn't need to be async.
        from app.cloudinary_client import is_configured as cloudinary_ok
        if cloudinary_ok():
            return "cloudinary", False
        return "local", False

    def _resolve_document_driver(self) -> tuple[StorageDriver, bool]:
        explicit = getattr(self._settings, "FILE_STORAGE_DOCUMENT_DRIVER", "").strip().lower()
        if explicit in ("local", "s3_compatible", "cloudflare_r2", "cloudinary"):
            return explicit, True  # type: ignore[return-value]
        return self._driver, self._driver_pinned

    async def _resolve_cloudinary_credentials(self) -> tuple[str, str, str] | None:
        """Return (cloud_name, api_key, api_secret), preferring the admin-
        configured channel (only when saved, tested and enabled) over the
        CLOUDINARY_* env vars. Returns None if neither source is complete."""
        s = self._settings
        cloud_name, api_key, api_secret = s.CLOUDINARY_CLOUD_NAME, s.CLOUDINARY_API_KEY, s.CLOUDINARY_API_SECRET
        if self._db is not None:
            try:
                from app.engines.platform_notifications.channel_config_service import channel_config_service
                active = await channel_config_service.get_active(self._db, "cloudinary")
            except Exception:
                logger.warning("media.storage.cloudinary_admin_config_lookup_failed", exc_info=True)
                active = None
            if active:
                config, credentials = active
                cloud_name = config.get("cloud_name") or cloud_name
                api_key = config.get("api_key") or api_key
                api_secret = credentials.get("api_secret") or api_secret
        if cloud_name and api_key and api_secret:
            return cloud_name, api_key, api_secret
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    async def store_file(
        self,
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        media_context: str,
        owner_id: str,
    ) -> StoredFile:
        """Upload bytes to the configured storage driver. Returns StoredFile."""
        ext = self._extract_extension(original_filename, mime_type)
        stored_name = f"{secrets.token_hex(12)}{ext}"
        checksum = hashlib.sha256(file_bytes).hexdigest()

        is_image_or_video = mime_type.startswith(("image/", "video/"))
        driver = self._driver if is_image_or_video else self._document_driver
        pinned = self._driver_pinned if is_image_or_video else self._document_driver_pinned
        cloudinary_creds = await self._resolve_cloudinary_credentials()
        # The admin-configured Cloudinary channel overrides an auto-selected
        # "local" default the moment it's saved, tested and enabled -- no
        # restart, no env vars needed. An operator's EXPLICIT FILE_STORAGE_
        # DRIVER / FILE_STORAGE_DOCUMENT_DRIVER=local (or any other driver)
        # is a deliberate pin and is never silently overridden.
        if driver == "local" and not pinned and cloudinary_creds:
            driver = "cloudinary"
        if driver == "cloudinary":
            if not cloudinary_creds:
                from app.exceptions import ServiceOSException
                raise ServiceOSException(
                    "MEDIA_STORAGE_NOT_CONFIGURED",
                    "Cloudinary storage is selected but not configured. Set it up in Notification & Provider Settings, or the CLOUDINARY_* env vars.",
                )
            return await self._store_cloudinary(file_bytes, stored_name, media_context, owner_id, checksum, cloudinary_creds)
        if driver in ("s3_compatible", "cloudflare_r2"):
            return await self._store_s3(
                file_bytes, stored_name, media_context, owner_id, checksum, mime_type, driver
            )
        # default: local
        return self._store_local(file_bytes, stored_name, media_context, owner_id, checksum)

    async def delete_file(self, storage_driver: str, storage_key: str) -> bool:
        """Delete a file from storage. Returns True if deleted."""
        try:
            if storage_driver == "local":
                path = UPLOADS_DIR / storage_key
                if path.exists():
                    path.unlink()
                return True
            if storage_driver == "cloudinary":
                return await self._delete_cloudinary(storage_key)
            if storage_driver in ("s3_compatible", "cloudflare_r2"):
                return await self._delete_s3(storage_key)
        except Exception as exc:
            logger.warning("media.storage.delete_failed", driver=storage_driver,
                           storage_key=storage_key, error=str(exc))
        return False

    def get_view_url(self, storage_driver: str, storage_key: str,
                     public_url: str | None, is_public: bool) -> str:
        """Return the URL to serve/view a file. For private files, use the serve endpoint."""
        if is_public and public_url:
            return public_url
        # Private: route through our serve endpoint (access-checked)
        return f"/v1/media/assets/{storage_key.replace('/', '%2F')}/serve"

    def get_local_path(self, storage_key: str) -> pathlib.Path | None:
        """Resolve local file path. Returns None if not a local file or missing."""
        path = UPLOADS_DIR / storage_key
        return path if path.exists() else None

    def validate_storage_config(self) -> None:
        """Raise ValueError if the configured driver is missing required settings."""
        drivers = {self._driver, self._document_driver}
        if "cloudinary" in drivers:
            s = self._settings
            missing = [k for k in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
                       if not getattr(s, k, "")]
            if missing:
                raise ValueError(f"Cloudinary storage configured but missing: {', '.join(missing)}")
        if drivers.intersection({"s3_compatible", "cloudflare_r2"}):
            s = self._settings
            missing = [k for k in ("FILE_STORAGE_BUCKET", "FILE_STORAGE_ACCESS_KEY", "FILE_STORAGE_SECRET_KEY")
                       if not getattr(s, k, "")]
            if missing:
                raise ValueError(f"S3 storage configured but missing: {', '.join(missing)}")

    @property
    def driver(self) -> StorageDriver:
        return self._driver

    # ── Local ─────────────────────────────────────────────────────────────────

    def _store_local(
        self, file_bytes: bytes, stored_name: str, media_context: str,
        owner_id: str, checksum: str
    ) -> StoredFile:
        rel_dir = pathlib.Path(media_context)
        abs_dir = UPLOADS_DIR / rel_dir
        abs_dir.mkdir(parents=True, exist_ok=True)
        # `str(PurePath)` uses the OS separator, so on Windows this produced
        # storage_key "category_icon\<name>.png" and therefore a public_url
        # of "/uploads/category_icon\<name>.png" -- a backslash is not a path
        # separator in a URL, so that value is only usable by accident on a
        # local dev server and breaks on any real client/CDN (and is stored
        # in the DB, so it outlives the request). storage_key is a URL/object
        # key, not a filesystem path: always join it with "/", and keep the
        # filesystem path a separate, properly-constructed Path.
        storage_key = f"{media_context}/{stored_name}"
        abs_path = abs_dir / stored_name
        abs_path.write_bytes(file_bytes)
        # A bare "/uploads/..." path only resolves for a caller sharing this
        # server's own origin. It happened to work for nothing so far
        # because every icon_url in this DB was NULL until this session --
        # the first real upload immediately exposed it: super-admin's
        # IconPicker preview (a different origin, the Next.js dev server)
        # and the mobile app (a different host entirely) would both request
        # it against THEIR OWN origin and get a 404, not this API's
        # /uploads route. Cloudinary/S3 never had this problem since they
        # always return an absolute CDN URL. Same
        # FILE_STORAGE_PUBLIC_BASE_URL prefix already used by the S3 driver
        # below, applied here too; falls back to the relative path only if
        # that setting is genuinely unset.
        base_url = getattr(self._settings, "FILE_STORAGE_PUBLIC_BASE_URL", "").rstrip("/")
        public_url = f"{base_url}/uploads/{storage_key}" if base_url else f"/uploads/{storage_key}"
        return StoredFile(
            storage_driver="local",
            storage_key=storage_key,
            storage_bucket=None,
            public_url=public_url,
            file_name_stored=stored_name,
            checksum=checksum,
        )

    # ── Cloudinary ────────────────────────────────────────────────────────────

    async def _store_cloudinary(
        self, file_bytes: bytes, stored_name: str, media_context: str,
        owner_id: str, checksum: str, credentials: tuple[str, str, str]
    ) -> StoredFile:
        """Upload directly to Cloudinary via server-side upload (not client-side).
        `credentials` is (cloud_name, api_key, api_secret) resolved by the
        caller -- see _resolve_cloudinary_credentials."""
        import httpx
        from app.cloudinary_client import build_upload_params

        cloud_name, api_key, api_secret = credentials
        public_id = f"serviceos/{media_context}/{stored_name}"
        params = build_upload_params(public_id=public_id, cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
        params.pop("upload_url", None)

        upload_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload"

        form_data: dict = {k: str(v) for k, v in params.items()}
        files = {"file": (stored_name, file_bytes)}

        timeout = httpx.Timeout(connect=8.0, read=45.0, write=45.0, pool=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(upload_url, data=form_data, files=files)
                resp.raise_for_status()
                result = resp.json()
        except httpx.TimeoutException:
            from app.exceptions import ServiceOSException
            raise ServiceOSException(
                "MEDIA_STORAGE_TIMEOUT",
                "File upload timed out. Please try again with a smaller file or check your connection.",
            )
        except httpx.HTTPStatusError as exc:
            from app.exceptions import ServiceOSException
            raise ServiceOSException(
                "MEDIA_STORAGE_ERROR",
                f"Storage service returned an error ({exc.response.status_code}). Please try again.",
            )
        except httpx.RequestError as exc:
            from app.exceptions import ServiceOSException
            raise ServiceOSException(
                "MEDIA_STORAGE_UNAVAILABLE",
                "Could not reach the storage service. Please try again shortly.",
            )

        public_url = result.get("secure_url") or result.get("url")
        storage_key = result.get("public_id", public_id)

        return StoredFile(
            storage_driver="cloudinary",
            storage_key=storage_key,
            storage_bucket=cloud_name,
            public_url=public_url,
            file_name_stored=stored_name,
            checksum=checksum,
        )

    async def _delete_cloudinary(self, storage_key: str) -> bool:
        import httpx
        import hashlib
        credentials = await self._resolve_cloudinary_credentials()
        if not credentials:
            return False
        cloud_name, api_key, api_secret = credentials
        timestamp = int(time.time())
        sign_str = f"public_id={storage_key}&timestamp={timestamp}{api_secret}"
        signature = hashlib.sha1(sign_str.encode()).hexdigest()
        url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/destroy"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, data={
                "public_id": storage_key, "timestamp": timestamp,
                "api_key": api_key, "signature": signature,
            })
        return resp.status_code == 200

    # ── S3-compatible ─────────────────────────────────────────────────────────

    async def _store_s3(
        self, file_bytes: bytes, stored_name: str, media_context: str,
        owner_id: str, checksum: str, mime_type: str, driver: StorageDriver
    ) -> StoredFile:
        """Upload to any S3-compatible endpoint (including Cloudflare R2)."""
        import httpx
        from datetime import datetime

        settings = self._settings
        bucket = getattr(settings, "FILE_STORAGE_BUCKET", "")
        endpoint = getattr(settings, "FILE_STORAGE_ENDPOINT", "").rstrip("/")
        region = getattr(settings, "FILE_STORAGE_REGION", "auto")
        access_key = getattr(settings, "FILE_STORAGE_ACCESS_KEY", "")
        secret_key = getattr(settings, "FILE_STORAGE_SECRET_KEY", "")

        storage_key = f"{media_context}/{stored_name}"
        url = f"{endpoint}/{bucket}/{storage_key}"

        # Simple AWS SigV4 signing is complex; for brevity use presigned URL approach
        # or boto3. For now, POST directly with basic auth if configured.
        # Production deployments should use boto3 / real SigV4.
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(len(file_bytes)),
        }

        async with httpx.AsyncClient(timeout=60, auth=(access_key, secret_key)) as client:
            resp = await client.put(url, content=file_bytes, headers=headers)
            resp.raise_for_status()

        base_url = getattr(settings, "FILE_STORAGE_PUBLIC_BASE_URL", "").rstrip("/")
        public_url = f"{base_url}/{storage_key}" if base_url else None

        return StoredFile(
            storage_driver=driver,
            storage_key=storage_key,
            storage_bucket=bucket,
            public_url=public_url,
            file_name_stored=stored_name,
            checksum=checksum,
        )

    async def _delete_s3(self, storage_key: str) -> bool:
        import httpx
        settings = self._settings
        bucket = getattr(settings, "FILE_STORAGE_BUCKET", "")
        endpoint = getattr(settings, "FILE_STORAGE_ENDPOINT", "").rstrip("/")
        access_key = getattr(settings, "FILE_STORAGE_ACCESS_KEY", "")
        secret_key = getattr(settings, "FILE_STORAGE_SECRET_KEY", "")
        url = f"{endpoint}/{bucket}/{storage_key}"
        async with httpx.AsyncClient(timeout=15, auth=(access_key, secret_key)) as client:
            resp = await client.delete(url)
        return resp.status_code in (200, 204)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_extension(filename: str, mime_type: str) -> str:
        ext = pathlib.Path(filename).suffix.lower()
        if ext:
            return ext
        guessed = mimetypes.guess_extension(mime_type)
        return guessed or ".bin"
