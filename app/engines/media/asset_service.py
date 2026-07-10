"""
MediaAssetService — core business logic for the Phase 0A Media Engine.

Uses the new `media_assets` table (migration 049).
Storage via MediaStorageService.
Validation via MediaValidationService.
Access control via MediaAccessService.
"""
from __future__ import annotations

import pathlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog
from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.dependencies.auth import UserContext
from app.engines.media.access import MediaAccessService
from app.engines.media.models import MediaAsset
from app.engines.media.storage import MediaStorageService
from app.engines.media.validation import MediaValidationService
from app.exceptions import NotFoundException, ServiceOSException

logger = structlog.get_logger("media.asset_service")
utcnow = lambda: datetime.now(timezone.utc)

MAX_PAGE_SIZE = 100


@dataclass
class MediaAssetRecord:
    """Lightweight DTO for access checks (avoids passing full ORM objects around)."""
    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    tenant_id: uuid.UUID | None
    customer_id: uuid.UUID | None
    uploaded_by_user_id: uuid.UUID
    media_context: str
    storage_driver: str
    storage_key: str
    public_url: str | None
    is_public: bool
    access_level: str
    status: str

    @classmethod
    def from_orm(cls, a: MediaAsset) -> "MediaAssetRecord":
        return cls(
            id=a.id, owner_type=a.owner_type, owner_id=a.owner_id,
            tenant_id=a.tenant_id, customer_id=a.customer_id,
            uploaded_by_user_id=a.uploaded_by_user_id,
            media_context=a.media_context,
            storage_driver=a.storage_driver, storage_key=a.storage_key,
            public_url=a.public_url, is_public=a.is_public,
            access_level=a.access_level, status=a.status,
        )


class MediaAssetService:

    def __init__(self, db: AsyncSession, actor: UserContext) -> None:
        self.db = db
        self.actor = actor
        self._storage = MediaStorageService()
        self._validation = MediaValidationService()
        self._access = MediaAccessService()

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload(
        self,
        file: UploadFile,
        media_context: str,
        owner_type: str,
        owner_id: str,
        is_public: bool = False,
        extra_metadata: dict | None = None,
    ) -> dict:
        """
        Accept an UploadFile, validate, store, and create a MediaAsset record.
        Returns the asset dict with preview_url.
        """
        file_bytes = await file.read()
        original_name = file.filename or "upload"
        mime_type = file.content_type or "application/octet-stream"

        # 1. Validate
        self._validation.validate_upload(file_bytes, original_name, mime_type, media_context)

        # 2. Access check
        self._access.assert_can_upload(self.actor, media_context, owner_type, owner_id)

        # 3. Store
        stored = await self._storage.store_file(
            file_bytes=file_bytes,
            original_filename=original_name,
            mime_type=mime_type,
            media_context=media_context,
            owner_id=owner_id,
        )

        # 4. Resolve tenant_id / customer_id from actor (never from request body)
        tenant_id: uuid.UUID | None = None
        customer_id: uuid.UUID | None = None
        if self.actor.tenant_id:
            tenant_id = uuid.UUID(self.actor.tenant_id)
        if self.actor.role == "customer":
            customer_id = uuid.UUID(self.actor.user_id)

        ext = pathlib.Path(original_name).suffix.lower()

        asset = MediaAsset(
            owner_type=owner_type,
            owner_id=uuid.UUID(owner_id) if isinstance(owner_id, str) else owner_id,
            tenant_id=tenant_id,
            customer_id=customer_id,
            uploaded_by_user_id=uuid.UUID(self.actor.user_id),
            media_context=media_context,
            file_name_original=original_name,
            file_name_stored=stored.file_name_stored,
            mime_type=mime_type,
            file_extension=ext or ".bin",
            file_size_bytes=len(file_bytes),
            storage_driver=stored.storage_driver,
            storage_bucket=stored.storage_bucket,
            storage_key=stored.storage_key,
            public_url=stored.public_url if is_public else None,
            is_public=is_public,
            access_level="public" if is_public else self._default_access_level(media_context),
            status="active",
            checksum=stored.checksum,
            metadata_json=extra_metadata or {},
        )
        self.db.add(asset)
        await self.db.flush()

        logger.info("media.uploaded", asset_id=str(asset.id), context=media_context,
                    driver=stored.storage_driver, size=len(file_bytes))

        await record_platform_audit(
            self.db,
            operation="media.uploaded",
            engine_id="media",
            entity_id=str(asset.id),
            entity_type="media_asset",
            actor_id=uuid.UUID(self.actor.user_id),
            actor_role=self.actor.role,
            tenant_id=tenant_id,
            after={"media_context": media_context, "owner_type": owner_type, "file_size_bytes": len(file_bytes)},
        )

        return asset.to_dict(view_url=self._view_url(asset))

    # ── Get / View ────────────────────────────────────────────────────────────

    async def get_asset(self, media_id: uuid.UUID) -> dict:
        asset = await self._load(media_id)
        rec = MediaAssetRecord.from_orm(asset)
        try:
            self._access.assert_can_view(self.actor, rec)
        except ServiceOSException as exc:
            if exc.error_code in ("MEDIA_ACCESS_DENIED", "MEDIA_CUSTOMER_SCOPE_VIOLATION", "MEDIA_TENANT_SCOPE_VIOLATION"):
                await record_platform_audit(
                    self.db,
                    operation="media.access_denied",
                    engine_id="media",
                    entity_id=str(media_id),
                    entity_type="media_asset",
                    actor_id=uuid.UUID(self.actor.user_id),
                    actor_role=self.actor.role,
                    after={"error_code": exc.error_code, "media_context": asset.media_context},
                )
            raise
        return asset.to_dict(view_url=self._view_url(asset))

    async def get_local_file_for_serve(self, media_id: uuid.UUID) -> tuple[pathlib.Path, str]:
        """Return (path, mime_type) for serving local files through the API."""
        asset = await self._load(media_id)
        rec = MediaAssetRecord.from_orm(asset)
        try:
            self._access.assert_can_view(self.actor, rec)
        except ServiceOSException as exc:
            if exc.error_code in ("MEDIA_ACCESS_DENIED", "MEDIA_CUSTOMER_SCOPE_VIOLATION", "MEDIA_TENANT_SCOPE_VIOLATION"):
                await record_platform_audit(
                    self.db,
                    operation="media.access_denied",
                    engine_id="media",
                    entity_id=str(media_id),
                    entity_type="media_asset",
                    actor_id=uuid.UUID(self.actor.user_id),
                    actor_role=self.actor.role,
                    after={"error_code": exc.error_code, "media_context": asset.media_context},
                )
            raise
        if asset.storage_driver != "local":
            raise ServiceOSException(
                "MEDIA_NOT_FOUND",
                "This asset is not stored locally. Use the public_url or redirect."
            )
        path = self._storage.get_local_path(asset.storage_key)
        if not path:
            raise ServiceOSException("MEDIA_NOT_FOUND", "File not found in local storage.")
        return path, asset.mime_type

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_assets(
        self,
        media_context: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size

        q = select(MediaAsset).where(MediaAsset.status != "deleted")

        # Scope to actor
        if self.actor.role == "customer":
            q = q.where(MediaAsset.customer_id == uuid.UUID(self.actor.user_id))
        elif self.actor.role in ("tenant_owner", "staff", "technician"):
            if self.actor.tenant_id:
                q = q.where(MediaAsset.tenant_id == uuid.UUID(self.actor.tenant_id))
        # super_admin sees all

        if media_context:
            q = q.where(MediaAsset.media_context == media_context)
        if owner_type:
            q = q.where(MediaAsset.owner_type == owner_type)
        if owner_id:
            q = q.where(MediaAsset.owner_id == uuid.UUID(owner_id))

        total_r = await self.db.execute(select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one()

        q = q.order_by(MediaAsset.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(q)
        assets = result.scalars().all()

        return {
            "items": [a.to_dict(view_url=self._view_url(a)) for a in assets],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Replace ───────────────────────────────────────────────────────────────

    async def replace_asset(
        self,
        media_id: uuid.UUID,
        file: UploadFile,
        is_public: bool | None = None,
    ) -> dict:
        old_asset = await self._load(media_id)
        rec = MediaAssetRecord.from_orm(old_asset)
        self._access.assert_can_replace(self.actor, rec)

        file_bytes = await file.read()
        original_name = file.filename or "upload"
        mime_type = file.content_type or "application/octet-stream"

        self._validation.validate_upload(file_bytes, original_name, mime_type, old_asset.media_context)

        stored = await self._storage.store_file(
            file_bytes=file_bytes,
            original_filename=original_name,
            mime_type=mime_type,
            media_context=old_asset.media_context,
            owner_id=str(old_asset.owner_id),
        )

        # Mark old as replaced
        old_asset.status = "replaced"
        old_asset.updated_at = utcnow()

        ext = pathlib.Path(original_name).suffix.lower()
        new_is_public = is_public if is_public is not None else old_asset.is_public

        new_asset = MediaAsset(
            owner_type=old_asset.owner_type,
            owner_id=old_asset.owner_id,
            tenant_id=old_asset.tenant_id,
            customer_id=old_asset.customer_id,
            uploaded_by_user_id=uuid.UUID(self.actor.user_id),
            media_context=old_asset.media_context,
            file_name_original=original_name,
            file_name_stored=stored.file_name_stored,
            mime_type=mime_type,
            file_extension=ext or ".bin",
            file_size_bytes=len(file_bytes),
            storage_driver=stored.storage_driver,
            storage_bucket=stored.storage_bucket,
            storage_key=stored.storage_key,
            public_url=stored.public_url if new_is_public else None,
            is_public=new_is_public,
            access_level=old_asset.access_level,
            status="active",
            checksum=stored.checksum,
            metadata_json=old_asset.metadata_json or {},
        )
        self.db.add(new_asset)
        await self.db.flush()

        logger.info("media.replaced", old_id=str(media_id), new_id=str(new_asset.id))
        await record_platform_audit(
            self.db,
            operation="media.replaced",
            engine_id="media",
            entity_id=str(new_asset.id),
            entity_type="media_asset",
            actor_id=uuid.UUID(self.actor.user_id),
            actor_role=self.actor.role,
            tenant_id=new_asset.tenant_id,
            before={"replaced_id": str(media_id)},
            after={"new_id": str(new_asset.id), "media_context": new_asset.media_context},
        )
        return {
            "replaced_id": str(old_asset.id),
            "new_asset": new_asset.to_dict(view_url=self._view_url(new_asset)),
        }

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_asset(self, media_id: uuid.UUID) -> dict:
        asset = await self._load(media_id)
        rec = MediaAssetRecord.from_orm(asset)
        self._access.assert_can_delete(self.actor, rec)

        asset.status = "deleted"
        asset.deleted_at = utcnow()
        asset.updated_at = utcnow()

        # Physical delete for local storage (safe — no shared references for new assets)
        if asset.storage_driver == "local":
            await self._storage.delete_file(asset.storage_driver, asset.storage_key)

        logger.info("media.deleted", asset_id=str(media_id), context=asset.media_context)
        await record_platform_audit(
            self.db,
            operation="media.deleted",
            engine_id="media",
            entity_id=str(media_id),
            entity_type="media_asset",
            actor_id=uuid.UUID(self.actor.user_id),
            actor_role=self.actor.role,
            tenant_id=asset.tenant_id,
            before={"media_context": asset.media_context, "file_name": asset.file_name_original},
        )
        return {"id": str(media_id), "deleted": True}

    # ── Profile photo helper ──────────────────────────────────────────────────

    async def set_user_profile_photo(self, file: UploadFile) -> dict:
        """Upload profile photo for the current user and update avatar_url."""
        from app.engines.auth.models import User
        user_id = uuid.UUID(self.actor.user_id)

        # Determine media context by role
        context_map = {
            "super_admin":   "admin_profile_photo",
            "tenant_owner":  "tenant_owner_profile_photo",
            "staff":         "staff_profile_photo",
            "technician":    "staff_profile_photo",
            "customer":      "customer_profile_photo",
        }
        media_context = context_map.get(self.actor.role, "tenant_owner_profile_photo")

        result = await self.upload(
            file=file,
            media_context=media_context,
            owner_type="user",
            owner_id=str(user_id),
            is_public=True,
        )

        # Update user record
        user_r = await self.db.execute(select(User).where(User.id == user_id))
        user = user_r.scalar_one_or_none()
        if user:
            user.avatar_url = result.get("preview_url") or result.get("public_url")
            user.profile_photo_media_id = uuid.UUID(result["id"])

        return result

    async def remove_user_profile_photo(self) -> dict:
        """Remove profile photo for the current user."""
        from app.engines.auth.models import User
        user_id = uuid.UUID(self.actor.user_id)
        user_r = await self.db.execute(select(User).where(User.id == user_id))
        user = user_r.scalar_one_or_none()
        if not user or not user.profile_photo_media_id:
            raise ServiceOSException("MEDIA_NOT_FOUND", "No profile photo to remove.")

        await self.delete_asset(user.profile_photo_media_id)
        user.avatar_url = None
        user.profile_photo_media_id = None
        return {"removed": True}

    # ── Business logo / shop photo (tenant-scoped) ────────────────────────────

    async def set_tenant_business_logo(self, file: UploadFile) -> dict:
        """Upload business logo for the actor's tenant and update logo_url + business_logo_media_id."""
        from app.engines.tenant_engine.models import Tenant
        if not self.actor.tenant_id:
            raise ServiceOSException("MEDIA_ACCESS_DENIED", "No tenant context.")
        tenant_id = uuid.UUID(self.actor.tenant_id)

        result = await self.upload(
            file=file,
            media_context="provider_business_logo",
            owner_type="tenant",
            owner_id=str(tenant_id),
            is_public=True,
        )

        t_r = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = t_r.scalar_one_or_none()
        if tenant:
            tenant.logo_url = result.get("preview_url") or result.get("public_url")
            tenant.business_logo_media_id = uuid.UUID(result["id"])

        return result

    async def remove_tenant_business_logo(self, media_id: uuid.UUID) -> dict:
        """Soft-delete the specified business logo and clear tenant logo references."""
        from app.engines.tenant_engine.models import Tenant
        if not self.actor.tenant_id:
            raise ServiceOSException("MEDIA_ACCESS_DENIED", "No tenant context.")
        tenant_id = uuid.UUID(self.actor.tenant_id)

        result = await self.delete_asset(media_id)

        t_r = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = t_r.scalar_one_or_none()
        if tenant and tenant.business_logo_media_id == media_id:
            tenant.logo_url = None
            tenant.business_logo_media_id = None

        return result

    async def set_tenant_shop_photo(self, file: UploadFile) -> dict:
        """Upload shop/storefront photo for the actor's tenant."""
        from app.engines.tenant_engine.models import Tenant
        if not self.actor.tenant_id:
            raise ServiceOSException("MEDIA_ACCESS_DENIED", "No tenant context.")
        tenant_id = uuid.UUID(self.actor.tenant_id)

        result = await self.upload(
            file=file,
            media_context="provider_shop_photo",
            owner_type="tenant",
            owner_id=str(tenant_id),
            is_public=True,
        )

        t_r = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = t_r.scalar_one_or_none()
        if tenant:
            tenant.shop_photo_media_id = uuid.UUID(result["id"])

        return result

    async def remove_tenant_shop_photo(self, media_id: uuid.UUID) -> dict:
        """Soft-delete the specified shop photo and clear tenant reference."""
        from app.engines.tenant_engine.models import Tenant
        if not self.actor.tenant_id:
            raise ServiceOSException("MEDIA_ACCESS_DENIED", "No tenant context.")
        tenant_id = uuid.UUID(self.actor.tenant_id)

        result = await self.delete_asset(media_id)

        t_r = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = t_r.scalar_one_or_none()
        if tenant and tenant.shop_photo_media_id == media_id:
            tenant.shop_photo_media_id = None

        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _load(self, media_id: uuid.UUID) -> MediaAsset:
        r = await self.db.execute(
            select(MediaAsset).where(
                MediaAsset.id == media_id,
                MediaAsset.status != "deleted",
            )
        )
        asset = r.scalar_one_or_none()
        if not asset:
            raise NotFoundException("MediaAsset", str(media_id))
        return asset

    def _view_url(self, asset: MediaAsset) -> str:
        if asset.is_public and asset.public_url:
            return asset.public_url
        if asset.storage_driver == "local":
            return f"/v1/media/{asset.id}/view"
        return f"/v1/media/{asset.id}/view"

    @staticmethod
    def _default_access_level(media_context: str) -> str:
        from app.engines.media.access import CUSTOMER_CONTEXTS
        if media_context in CUSTOMER_CONTEXTS:
            return "customer"
        if media_context in ("admin_profile_photo", "brand_logo", "category_icon", "service_icon"):
            return "public"
        return "tenant"
