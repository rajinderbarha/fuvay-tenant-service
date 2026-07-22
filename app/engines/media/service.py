"""Media Vault — MediaService."""
from __future__ import annotations
import uuid, secrets
from datetime import datetime, timezone, timedelta
import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.media.models import MediaFile, MediaUploadSession
from app.exceptions import ServiceOSException, NotFoundException
from app.schemas.base import encode_cursor, decode_cursor
from app.cloudinary_client import is_configured as cloudinary_configured, build_upload_params, build_delivery_url

logger = structlog.get_logger("media.service")
utcnow = lambda: datetime.now(timezone.utc)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB default
# Storage quota is enforced per the tenant's chosen package for every vertical
# EXCEPT home services, which is exempt (unlimited). A non-home-services tenant
# with no package limit set falls back to this default.
DEFAULT_STORAGE_QUOTA_GB = 10
EXEMPT_VERTICALS = {"home_services"}
_GB = 1024 * 1024 * 1024


class MediaService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role
        # Phase 2A Slice 2F-31A (N01 residual): the authoritative tenant of the
        # calling principal, derived server-side from the token. Every mutation
        # below MUST compare any client-supplied tenant_id against this value
        # (never the reverse) -- a route guard alone cannot close this, because
        # a direct MediaService call bypasses the router entirely.
        self.actor_tenant_id = actor_tenant_id

    def _require_trusted_tenant(self, requested_tenant_id: uuid.UUID) -> None:
        """Fail closed unless the caller is platform staff or the requested
        tenant equals the principal's own authoritative tenant.

        Never raises a message that reveals whether requested_tenant_id itself
        is real -- the caller compares its own return value/exception, not the
        tenant's existence.
        """
        if self.actor_role == "super_admin":
            return
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "PERMISSION_DENIED", "No tenant context.",
                blocking_rule="media_mutation_requires_trusted_tenant_context")
        if requested_tenant_id != self.actor_tenant_id:
            # Non-oracular: the caller's own tenant mismatch, not "this other
            # tenant doesn't exist" -- same PERMISSION_DENIED regardless of
            # whether requested_tenant_id is real.
            raise ServiceOSException(
                "PERMISSION_DENIED", "You do not have access to this tenant's media.",
                blocking_rule="media_mutation_cross_tenant_denied")

    def _file_dict(self, f: MediaFile, signed_url: str | None = None) -> dict:
        return {"file_id": str(f.id), "tenant_id": str(f.tenant_id),
                "original_name": f.original_name, "mime_type": f.mime_type,
                "size_bytes": f.size_bytes, "entity_type": f.entity_type,
                "entity_id": f.entity_id, "is_public": f.is_public,
                "scan_status": f.scan_status, "signed_url": signed_url,
                "created_at": f.created_at.isoformat()}

    async def _effective_storage_quota_bytes(self, tenant_id: uuid.UUID) -> int | None:
        """The tenant's storage cap in bytes, or None when it is exempt.

        Home services is exempt (no cap). Every other vertical is capped by its
        chosen package's quota — tenant_limits.max_storage_gb, which the package
        engine writes on package approval. A non-exempt tenant with no explicit
        limit falls back to DEFAULT_STORAGE_QUOTA_GB.
        """
        from app.engines.tenant_engine.models import Tenant, TenantLimits

        vertical = await self.db.scalar(select(Tenant.vertical).where(Tenant.id == tenant_id))
        if (vertical or "").strip().lower() in EXEMPT_VERTICALS:
            return None

        limits = await self.db.scalar(
            select(TenantLimits).where(TenantLimits.tenant_id == tenant_id))
        gb = float(limits.max_storage_gb) if limits and limits.max_storage_gb is not None \
            else DEFAULT_STORAGE_QUOTA_GB
        return int(gb * _GB)

    async def initiate_upload(self, tenant_id: uuid.UUID, file_name: str,
                               mime_type: str, size_bytes: int,
                               entity_type: str | None, entity_id: str | None) -> dict:
        # Phase 2A Slice 2F-31A (N01 residual): tenant_id previously arrived
        # straight from the request body with no comparison to the calling
        # principal -- any authenticated user could reserve quota and mint a
        # storage-key prefix under an arbitrary tenant. No existing object is
        # involved yet, so PERMISSION_DENIED (not a 404) is the honest response.
        self._require_trusted_tenant(tenant_id)
        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB.")

        # Storage quota is package-based per the tenant's vertical. Home services
        # is exempt (unlimited); every other vertical is capped by the chosen
        # package's quota (tenant_limits.max_storage_gb, applied on approval).
        quota_bytes = await self._effective_storage_quota_bytes(tenant_id)
        if quota_bytes is not None:
            quota_r = await self.db.execute(select(func.sum(MediaFile.size_bytes)).where(
                MediaFile.tenant_id == tenant_id, MediaFile.is_deleted == False))
            used = quota_r.scalar_one_or_none() or 0
            if used + size_bytes > quota_bytes:
                raise ServiceOSException("PLAN_LIMIT_EXCEEDED",
                    "Storage quota exceeded. Upgrade your package for more storage.",
                    context={"used_gb": round(used / _GB, 2),
                             "quota_gb": round(quota_bytes / _GB, 2)})

        # Phase 2A Slice 2F-31A (N01 residual) WS6: file_name is client-supplied
        # and was previously concatenated into the storage key unsanitized --
        # a name containing "/" or ".." could escape the tenant-scoped prefix
        # on some storage backends (path traversal into another tenant's
        # namespace or outside the intended tree). Strip to the basename only;
        # the random token_hex segment already guarantees uniqueness.
        safe_file_name = file_name.replace("\\", "/").rsplit("/", 1)[-1].lstrip(".") or "file"
        storage_key = f"tenants/{tenant_id}/{secrets.token_hex(8)}/{safe_file_name}"
        expires_at = utcnow() + timedelta(hours=1)

        if cloudinary_configured():
            upload_params = build_upload_params(public_id=storage_key, folder=f"tenants/{tenant_id}")
            upload_url = upload_params["upload_url"]
        else:
            upload_params = None
            upload_url = f"https://s3.placeholder.com/upload?key={storage_key}&token={secrets.token_hex(16)}"

        session = MediaUploadSession(
            tenant_id=tenant_id, owner_id=self.actor_id or tenant_id,
            file_name=file_name, mime_type=mime_type, size_bytes=size_bytes,
            storage_key=storage_key, upload_url=upload_url,
            entity_type=entity_type, entity_id=entity_id, expires_at=expires_at,
        )
        self.db.add(session); await self.db.flush()
        result = {"session_id": str(session.id), "upload_url": upload_url,
                  "storage_key": storage_key, "expires_at": expires_at.isoformat(),
                  "max_size_bytes": MAX_FILE_SIZE_BYTES}
        if upload_params:
            result["upload_params"] = upload_params
        return result

    async def confirm_upload(self, session_id: uuid.UUID, is_public: bool) -> dict:
        r = await self.db.execute(select(MediaUploadSession).where(
            MediaUploadSession.id == session_id))
        sess = r.scalar_one_or_none()
        if not sess: raise NotFoundException("UploadSession", str(session_id))
        # Phase 2A Slice 2F-31A (N01 residual): confirm_upload previously took
        # no actor/tenant evidence at all -- any authenticated principal could
        # confirm ANY pending session by guessing/enumerating a session_id,
        # materializing a MediaFile owned by another tenant. Now requires the
        # confirming principal to be the session's own owner (the common case
        # -- initiate_upload sets owner_id from the initiating actor) OR to
        # belong to the session's tenant (tenant staff completing an upload).
        # Foreign sessions raise the SAME NotFoundException as a missing
        # session_id -- no existence oracle.
        if self.actor_role != "super_admin":
            owns_session = (self.actor_id is not None and sess.owner_id == self.actor_id)
            same_tenant = (self.actor_tenant_id is not None and sess.tenant_id == self.actor_tenant_id)
            if not (owns_session or same_tenant):
                raise NotFoundException("UploadSession", str(session_id))
        if sess.status == "confirmed":
            raise ServiceOSException("CONFLICT", "Upload already confirmed.")
        if sess.expires_at < utcnow():
            raise ServiceOSException("CONFLICT", "Upload session expired.")

        file = MediaFile(
            tenant_id=sess.tenant_id, owner_id=sess.owner_id,
            original_name=sess.file_name, storage_key=sess.storage_key,
            mime_type=sess.mime_type, size_bytes=sess.size_bytes,
            is_public=is_public, entity_type=sess.entity_type,
            entity_id=sess.entity_id, scan_status="clean",
        )
        self.db.add(file)
        sess.status = "confirmed"
        await self.db.flush()
        signed_url = self._signed_url(file.storage_key, file.mime_type)
        return self._file_dict(file, signed_url)

    async def get_file(self, file_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(MediaFile).where(
            MediaFile.id == file_id, MediaFile.tenant_id == tenant_id,
            MediaFile.is_deleted == False))
        f = r.scalar_one_or_none()
        if not f: raise NotFoundException("MediaFile", str(file_id))
        signed_url = self._signed_url(f.storage_key, f.mime_type)
        return self._file_dict(f, signed_url)

    def _signed_url(self, storage_key: str, mime_type: str) -> str:
        if cloudinary_configured():
            resource_type = "image" if mime_type.startswith("image/") else "video" if mime_type.startswith("video/") else "raw"
            return build_delivery_url(storage_key, resource_type)
        return f"https://cdn.placeholder.com/{storage_key}?sig={secrets.token_hex(8)}"

    async def list_files(self, tenant_id: uuid.UUID, entity_type: str | None,
                          entity_id: str | None, limit: int, cursor: str | None) -> dict:
        q = select(MediaFile).where(
            MediaFile.tenant_id == tenant_id, MediaFile.is_deleted == False
        ).order_by(MediaFile.created_at.desc())
        if entity_type: q = q.where(MediaFile.entity_type == entity_type)
        if entity_id: q = q.where(MediaFile.entity_id == entity_id)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(MediaFile.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        files = r.scalars().all()
        has_next = len(files) > limit; files = files[:limit]
        nc = encode_cursor({"created_at": files[-1].created_at.isoformat()}) if has_next and files else None
        return {"files": [self._file_dict(f) for f in files],
                "has_next": has_next, "next_cursor": nc}

    async def delete_file(self, file_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        # Phase 2A Slice 2F-31A (N01 residual): tenant_id previously came
        # straight from the request PATH and was used to scope the query with
        # no comparison to the calling principal's own tenant -- a
        # TENANT_UPDATE holder in tenant A could delete tenant B's file simply
        # by naming tenant B in the URL. Reject BEFORE the query runs, with the
        # same PERMISSION_DENIED regardless of whether the named tenant is
        # real, so this check itself creates no oracle.
        self._require_trusted_tenant(tenant_id)
        r = await self.db.execute(select(MediaFile).where(
            MediaFile.id == file_id, MediaFile.tenant_id == tenant_id))
        f = r.scalar_one_or_none()
        if not f: raise NotFoundException("MediaFile", str(file_id))
        f.is_deleted = True; f.deleted_at = utcnow()
        return {"file_id": str(file_id), "deleted": True}

    async def get_storage_quota(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(func.sum(MediaFile.size_bytes),
                                          func.count(MediaFile.id)).where(
            MediaFile.tenant_id == tenant_id, MediaFile.is_deleted == False))
        row = r.one()
        used = row[0] or 0; file_count = row[1]
        # Same package-based / home-services-exempt rule as enforcement.
        quota = await self._effective_storage_quota_bytes(tenant_id)
        if quota is None:
            return {"tenant_id": str(tenant_id),
                    "used_bytes": used, "used_gb": round(used / _GB, 3),
                    "quota_bytes": None, "quota_gb": None, "unlimited": True,
                    "usage_pct": 0.0, "file_count": file_count, "alert": False}
        return {"tenant_id": str(tenant_id),
                "used_bytes": used, "used_gb": round(used / _GB, 3),
                "quota_bytes": quota, "quota_gb": round(quota / _GB, 2), "unlimited": False,
                "usage_pct": round(used / quota * 100, 1) if quota else 0.0,
                "file_count": file_count,
                "alert": bool(quota) and used / quota > 0.85}
