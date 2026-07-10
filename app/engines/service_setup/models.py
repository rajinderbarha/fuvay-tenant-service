"""Service Setup Templates — ORM models (migration 091)."""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class ServiceSetupTemplate(ServiceOSBase):
    __tablename__ = "service_setup_templates"

    name:               Mapped[str]           = mapped_column(Text,         nullable=False)
    code:               Mapped[str]           = mapped_column(Text,         nullable=False, unique=True)
    description:        Mapped[str | None]    = mapped_column(Text,         nullable=True)
    vertical_key:       Mapped[str | None]    = mapped_column(Text,         nullable=True,  default="universal")
    template_type:      Mapped[str | None]    = mapped_column(Text,         nullable=True,  default="starter_pack")
    is_system:          Mapped[bool]          = mapped_column(Boolean,      nullable=False, default=False)
    status:             Mapped[str | None]    = mapped_column(Text,         nullable=True,  default="draft")
    version:            Mapped[int]           = mapped_column(Integer,      nullable=False, default=1)
    display_order:      Mapped[int]           = mapped_column(Integer,      nullable=False, default=0)
    config_json:        Mapped[dict | None]   = mapped_column(JSONB,        nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    archived_at:        Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "name": self.name, "code": self.code,
            "description": self.description, "vertical_key": self.vertical_key,
            "template_type": self.template_type, "is_system": self.is_system,
            "status": self.status, "version": self.version,
            "display_order": self.display_order, "config_json": self.config_json,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }


class ServiceSetupTemplateModule(ServiceOSBase):
    __tablename__ = "service_setup_template_modules"

    template_id:   Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    module_key:    Mapped[str]          = mapped_column(Text,    nullable=False)
    module_name:   Mapped[str | None]   = mapped_column(Text,    nullable=True)
    is_enabled:    Mapped[bool]         = mapped_column(Boolean, nullable=False, default=True)
    config_json:   Mapped[dict | None]  = mapped_column(JSONB,   nullable=True)
    display_order: Mapped[int]          = mapped_column(Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "template_id": str(self.template_id),
            "module_key": self.module_key, "module_name": self.module_name,
            "is_enabled": self.is_enabled, "config_json": self.config_json,
            "display_order": self.display_order,
        }


class ServiceSetupTemplateItem(ServiceOSBase):
    __tablename__ = "service_setup_template_items"

    template_id:     Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    module_key:      Mapped[str | None]   = mapped_column(Text, nullable=True)
    item_type:       Mapped[str | None]   = mapped_column(Text, nullable=True)
    item_key:        Mapped[str | None]   = mapped_column(Text, nullable=True)
    item_name:       Mapped[str | None]   = mapped_column(Text, nullable=True)
    parent_item_key: Mapped[str | None]   = mapped_column(Text, nullable=True)
    payload_json:    Mapped[dict | None]  = mapped_column(JSONB, nullable=True)
    display_order:   Mapped[int]          = mapped_column(Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "template_id": str(self.template_id),
            "module_key": self.module_key, "item_type": self.item_type,
            "item_key": self.item_key, "item_name": self.item_name,
            "parent_item_key": self.parent_item_key, "payload_json": self.payload_json,
            "display_order": self.display_order,
        }


class ServiceSetupTemplateVersion(ServiceOSBase):
    __tablename__ = "service_setup_template_versions"

    template_id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    version:             Mapped[int]          = mapped_column(Integer, nullable=False)
    snapshot_json:       Mapped[dict | None]  = mapped_column(JSONB,   nullable=True)
    changed_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_reason:       Mapped[str | None]   = mapped_column(Text,    nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "template_id": str(self.template_id),
            "version": self.version, "snapshot_json": self.snapshot_json,
            "changed_by_user_id": str(self.changed_by_user_id) if self.changed_by_user_id else None,
            "change_reason": self.change_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ServiceSetupTemplateUsage(ServiceOSBase):
    __tablename__ = "service_setup_template_usage"

    template_id:     Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    used_in:         Mapped[str | None]      = mapped_column(Text, nullable=True)
    used_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    bulk_run_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:          Mapped[str | None]      = mapped_column(Text, nullable=True, default="pending")


# ── Bulk Wizard Models (migration 098) ────────────────────────────────────────

class BulkDraft(ServiceOSBase):
    __tablename__ = "service_setup_bulk_drafts"

    draft_code:          Mapped[str]              = mapped_column(Text, unique=True, nullable=False)
    name:                Mapped[str]              = mapped_column(Text, nullable=False)
    description:         Mapped[str | None]       = mapped_column(Text, nullable=True)
    vertical_key:        Mapped[str]              = mapped_column(Text, nullable=False)
    setup_mode:          Mapped[str | None]       = mapped_column(Text, nullable=True, default="manual")
    template_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:              Mapped[str | None]       = mapped_column(Text, nullable=True, default="draft")
    current_step:        Mapped[int]              = mapped_column(Integer, nullable=True, default=1)
    config_json:         Mapped[dict | None]      = mapped_column(JSONB, nullable=True, default=dict)
    created_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    archived_at:         Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)


class BulkPreviewItem(ServiceOSBase):
    __tablename__ = "service_setup_bulk_preview_items"

    draft_id:    Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), nullable=False)
    module_key:  Mapped[str | None]  = mapped_column(Text, nullable=True)
    record_type: Mapped[str | None]  = mapped_column(Text, nullable=True)
    record_name: Mapped[str | None]  = mapped_column(Text, nullable=True)
    record_code: Mapped[str | None]  = mapped_column(Text, nullable=True)
    action:      Mapped[str | None]  = mapped_column(Text, nullable=True, default="create")
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    reason:      Mapped[str | None]  = mapped_column(Text, nullable=True)


class BulkValidationResult(ServiceOSBase):
    __tablename__ = "service_setup_bulk_validation_results"

    draft_id:    Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    severity:    Mapped[str | None] = mapped_column(Text, nullable=True, default="info")
    module_key:  Mapped[str | None] = mapped_column(Text, nullable=True)
    record_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    message:     Mapped[str]        = mapped_column(Text, nullable=False)
    blocking:    Mapped[bool]       = mapped_column(Boolean, nullable=True, default=False)


class BulkRun(ServiceOSBase):
    __tablename__ = "service_setup_bulk_runs"

    run_code:            Mapped[str]              = mapped_column(Text, unique=True, nullable=False)
    draft_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    vertical_key:        Mapped[str | None]       = mapped_column(Text, nullable=True)
    template_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:              Mapped[str | None]       = mapped_column(Text, nullable=True, default="queued")
    is_dry_run:          Mapped[bool]             = mapped_column(Boolean, nullable=True, default=False)
    total_items:         Mapped[int]              = mapped_column(Integer, nullable=True, default=0)
    created_count:       Mapped[int]              = mapped_column(Integer, nullable=True, default=0)
    updated_count:       Mapped[int]              = mapped_column(Integer, nullable=True, default=0)
    skipped_count:       Mapped[int]              = mapped_column(Integer, nullable=True, default=0)
    failed_count:        Mapped[int]              = mapped_column(Integer, nullable=True, default=0)
    rollback_available:  Mapped[bool]             = mapped_column(Boolean, nullable=True, default=False)
    execution_reason:    Mapped[str | None]       = mapped_column(Text, nullable=True)
    started_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at:          Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:        Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)


class BulkRunItem(ServiceOSBase):
    __tablename__ = "service_setup_bulk_run_items"

    run_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    module_key:       Mapped[str | None]       = mapped_column(Text, nullable=True)
    record_type:      Mapped[str | None]       = mapped_column(Text, nullable=True)
    record_name:      Mapped[str | None]       = mapped_column(Text, nullable=True)
    record_code:      Mapped[str | None]       = mapped_column(Text, nullable=True)
    action:           Mapped[str | None]       = mapped_column(Text, nullable=True)
    status:           Mapped[str | None]       = mapped_column(Text, nullable=True, default="pending")
    target_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    error_message:    Mapped[str | None]       = mapped_column(Text, nullable=True)
