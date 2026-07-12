"""Sprint 26 — Enterprise Grid ORM models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EnterpriseSavedView(Base):
    __tablename__ = "enterprise_saved_views"

    id:            Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scope:         Mapped[str]             = mapped_column(String(32), nullable=False)
    resource_key:  Mapped[str]             = mapped_column(String(64), nullable=False)
    view_name:     Mapped[str]             = mapped_column(String(128), nullable=False)
    is_default:    Mapped[bool]            = mapped_column(Boolean, default=False, nullable=False)
    filters:       Mapped[dict]            = mapped_column(JSONB, default=dict, nullable=False)
    sort:          Mapped[dict]            = mapped_column(JSONB, default=dict, nullable=False)
    columns:       Mapped[list]            = mapped_column(JSONB, default=list, nullable=False)
    page_size:     Mapped[int]             = mapped_column(Integer, default=25, nullable=False)
    visibility:    Mapped[str]             = mapped_column(String(32), default="private", nullable=False)
    created_at:    Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:    Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "owner_user_id": str(self.owner_user_id),
            "tenant_id":     str(self.tenant_id) if self.tenant_id else None,
            "scope":         self.scope,
            "resource_key":  self.resource_key,
            "view_name":     self.view_name,
            "is_default":    self.is_default,
            "filters":       self.filters,
            "sort":          self.sort,
            "columns":       self.columns,
            "page_size":     self.page_size,
            "visibility":    self.visibility,
            "created_at":    str(self.created_at) if self.created_at else None,
            "updated_at":    str(self.updated_at) if self.updated_at else None,
        }


class EnterpriseColumnPreference(Base):
    __tablename__ = "enterprise_column_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "resource_key", name="uq_colpref_user_resource"),
    )

    id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resource_key: Mapped[str]             = mapped_column(String(64), nullable=False)
    columns:      Mapped[list]            = mapped_column(JSONB, default=list, nullable=False)
    density:      Mapped[str]             = mapped_column(String(16), default="comfortable", nullable=False)
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id":           str(self.id),
            "user_id":      str(self.user_id),
            "tenant_id":    str(self.tenant_id) if self.tenant_id else None,
            "resource_key": self.resource_key,
            "columns":      self.columns,
            "density":      self.density,
            "created_at":   str(self.created_at) if self.created_at else None,
        }


class EnterpriseExportJob(Base):
    __tablename__ = "enterprise_export_jobs"

    id:                   Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by_user_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resource_key:         Mapped[str]             = mapped_column(String(64), nullable=False)
    status:               Mapped[str]             = mapped_column(String(32), default="pending", nullable=False)
    export_format:        Mapped[str]             = mapped_column(String(16), default="csv", nullable=False)
    filters:              Mapped[dict]            = mapped_column(JSONB, default=dict, nullable=False)
    columns:              Mapped[list]            = mapped_column(JSONB, default=list, nullable=False)
    row_count:            Mapped[int | None]      = mapped_column(Integer, nullable=True)
    file_url:             Mapped[str | None]      = mapped_column(Text, nullable=True)
    failure_reason:       Mapped[str | None]      = mapped_column(Text, nullable=True)
    expires_at:           Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:           Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at:           Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # FINAL-L5-05S — real export execution lifecycle (migration 135).
    worker_id:            Mapped[str | None]      = mapped_column(String(64), nullable=True)
    claimed_at:           Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at:           Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:         Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at:         Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count:          Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    storage_key:          Mapped[str | None]      = mapped_column(Text, nullable=True)
    filename:             Mapped[str | None]      = mapped_column(String(255), nullable=True)
    content_type:         Mapped[str | None]      = mapped_column(String(128), nullable=True)
    file_size:            Mapped[int | None]      = mapped_column(Integer, nullable=True)
    checksum:             Mapped[str | None]      = mapped_column(String(128), nullable=True)
    error_code:           Mapped[str | None]      = mapped_column(String(64), nullable=True)
    error_message:        Mapped[str | None]      = mapped_column(Text, nullable=True)
    progress:             Mapped[int]             = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "requested_by_user_id": str(self.requested_by_user_id),
            "tenant_id":            str(self.tenant_id) if self.tenant_id else None,
            "resource_key":         self.resource_key,
            "status":               self.status,
            "export_format":        self.export_format,
            "filters":              self.filters,
            "columns":              self.columns,
            "row_count":            self.row_count,
            # file_url is deliberately NOT populated with a raw storage
            # path -- download is only ever available via the authorized
            # /exports/{id}/download endpoint (rule: storage paths must
            # never be returned directly in an API response).
            "file_url":             None,
            "failure_reason":       self.failure_reason,
            "expires_at":           str(self.expires_at) if self.expires_at else None,
            "created_at":           str(self.created_at) if self.created_at else None,
            "updated_at":           str(self.updated_at) if self.updated_at else None,
            "started_at":           str(self.started_at) if self.started_at else None,
            "completed_at":         str(self.completed_at) if self.completed_at else None,
            "cancelled_at":         str(self.cancelled_at) if self.cancelled_at else None,
            "retry_count":          self.retry_count,
            "filename":             self.filename,
            "content_type":         self.content_type,
            "file_size":            self.file_size,
            "checksum":             self.checksum,
            "error_code":           self.error_code,
            "progress":             self.progress,
            "downloadable":         self.status == "completed" and bool(self.storage_key)
                                     and (self.expires_at is None or self.expires_at > datetime.now(timezone.utc)),
        }
