"""Media Engine — Models.

Tables:
  media_files         — legacy (migration 005); kept for backward compat
  media_upload_sessions — legacy; kept for backward compat
  MediaAsset          — new (migration 049); authoritative table going forward
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class MediaFile(ServiceOSBase):
    """Every uploaded file. Soft-delete only. Access via signed URLs."""
    __tablename__ = "media_files"
    __table_args__ = (Index("ix_mf_tenant_entity","tenant_id","entity_type","entity_id"),
                      Index("ix_mf_owner","owner_id"))

    tenant_id:    Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_id:     Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type:  Mapped[str|None]     = mapped_column(String(60), nullable=True)
    entity_id:    Mapped[str|None]     = mapped_column(String(100), nullable=True)
    original_name:Mapped[str]          = mapped_column(String(255), nullable=False)
    storage_key:  Mapped[str]          = mapped_column(String(500), nullable=False)
    mime_type:    Mapped[str]          = mapped_column(String(100), nullable=False)
    size_bytes:   Mapped[int]          = mapped_column(Integer, nullable=False)
    is_public:    Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    is_deleted:   Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    deleted_at:   Mapped[datetime|None]= mapped_column(DateTime(timezone=True), nullable=True)
    scan_status:  Mapped[str]          = mapped_column(String(20), default="pending", nullable=False)
    meta:         Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)


class MediaUploadSession(ServiceOSBase):
    """Tracks multipart upload state until confirmed."""
    __tablename__ = "media_upload_sessions"
    __table_args__ = (Index("ix_mus_tenant","tenant_id"),)

    tenant_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_name:   Mapped[str]       = mapped_column(String(255), nullable=False)
    mime_type:   Mapped[str]       = mapped_column(String(100), nullable=False)
    size_bytes:  Mapped[int]       = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str]       = mapped_column(String(500), nullable=False)
    upload_url:  Mapped[str]       = mapped_column(String(2000), nullable=False)
    status:      Mapped[str]       = mapped_column(String(20), default="pending", nullable=False)
    entity_type: Mapped[str|None]  = mapped_column(String(60), nullable=True)
    entity_id:   Mapped[str|None]  = mapped_column(String(100), nullable=True)
    expires_at:  Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)


class MediaAsset(ServiceOSBase):
    """Phase 0A — Central media asset record. Every uploaded file has one row."""
    __tablename__ = "media_assets"
    __table_args__ = (
        Index("ix_ma_owner",          "owner_type", "owner_id"),
        Index("ix_ma_tenant",         "tenant_id"),
        Index("ix_ma_customer",       "customer_id"),
        Index("ix_ma_context",        "media_context"),
        Index("ix_ma_status",         "status"),
        Index("ix_ma_tenant_context", "tenant_id", "media_context"),
        Index("ix_ma_uploader",       "uploaded_by_user_id"),
    )

    owner_type:            Mapped[str]           = mapped_column(String(60),   nullable=False)
    owner_id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:             Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    uploaded_by_user_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    media_context:         Mapped[str]            = mapped_column(String(80),   nullable=False)
    file_name_original:    Mapped[str]            = mapped_column(String(255),  nullable=False)
    file_name_stored:      Mapped[str]            = mapped_column(String(500),  nullable=False)
    mime_type:             Mapped[str]            = mapped_column(String(100),  nullable=False)
    file_extension:        Mapped[str]            = mapped_column(String(20),   nullable=False)
    file_size_bytes:       Mapped[int]            = mapped_column(Integer,      nullable=False)
    storage_driver:        Mapped[str]            = mapped_column(String(30),   nullable=False, default="local")
    storage_bucket:        Mapped[str|None]       = mapped_column(String(255),  nullable=True)
    storage_key:           Mapped[str]            = mapped_column(String(1000), nullable=False)
    public_url:            Mapped[str|None]       = mapped_column(String(2000), nullable=True)
    is_public:             Mapped[bool]           = mapped_column(Boolean,      nullable=False, default=False)
    access_level:          Mapped[str]            = mapped_column(String(30),   nullable=False, default="tenant")
    status:                Mapped[str]            = mapped_column(String(30),   nullable=False, default="active")
    checksum:              Mapped[str|None]       = mapped_column(String(64),   nullable=True)
    width:                 Mapped[int|None]       = mapped_column(Integer,      nullable=True)
    height:                Mapped[int|None]       = mapped_column(Integer,      nullable=True)
    metadata_json:         Mapped[dict]           = mapped_column(JSONB,        nullable=False, default=dict)
    deleted_at:            Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    # Found missing during the "make it 100% working" drift audit -- real,
    # migrated moderation/lifecycle columns.
    archived_at:           Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    description:           Mapped[str|None]       = mapped_column(String(500),  nullable=True)
    flag_reason:           Mapped[str|None]       = mapped_column(String(80),   nullable=True)
    flagged_at:            Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    is_flagged:            Mapped[bool]           = mapped_column(Boolean,      nullable=False, default=False)
    linked_module:         Mapped[str|None]       = mapped_column(String(60),   nullable=True)
    linked_record_id:      Mapped[str|None]       = mapped_column(String(100),  nullable=True)
    media_number:          Mapped[str|None]       = mapped_column(String(30),   nullable=True)
    moderation_status:     Mapped[str]            = mapped_column(String(30),   nullable=False, default="clean")
    processing_status:     Mapped[str]            = mapped_column(String(30),   nullable=False, default="ready")
    scan_status:           Mapped[str]            = mapped_column(String(30),   nullable=False, default="not_scanned")
    tags_json:             Mapped[list|None]      = mapped_column(JSONB,        nullable=True)
    thumbnail_key:         Mapped[str|None]       = mapped_column(String(1000), nullable=True)
    uploaded_from_app:     Mapped[str|None]       = mapped_column(String(60),   nullable=True)
    visibility:            Mapped[str]            = mapped_column(String(30),   nullable=False, default="private")

    def to_dict(self, view_url: str | None = None) -> dict:
        return {
            "id":                  str(self.id),
            "owner_type":          self.owner_type,
            "owner_id":            str(self.owner_id),
            "tenant_id":           str(self.tenant_id) if self.tenant_id else None,
            "customer_id":         str(self.customer_id) if self.customer_id else None,
            "uploaded_by_user_id": str(self.uploaded_by_user_id),
            "media_context":       self.media_context,
            "file_name_original":  self.file_name_original,
            "mime_type":           self.mime_type,
            "file_extension":      self.file_extension,
            "file_size_bytes":     self.file_size_bytes,
            "storage_driver":      self.storage_driver,
            "storage_key":         self.storage_key,
            "is_public":           self.is_public,
            "access_level":        self.access_level,
            "status":              self.status,
            "width":               self.width,
            "height":              self.height,
            "preview_url":         view_url or f"/v1/media/{self.id}/view",
            "created_at":          self.created_at.isoformat() if self.created_at else None,
            "updated_at":          self.updated_at.isoformat() if self.updated_at else None,
        }
