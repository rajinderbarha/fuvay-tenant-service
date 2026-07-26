"""Vertical Catalog — ORM models (migration 089)."""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class Vertical(ServiceOSBase):
    __tablename__ = "verticals"
    __table_args__ = (
        Index("ix_verticals_key",        "key"),
        Index("ix_verticals_is_enabled", "is_enabled"),
    )

    key:           Mapped[str]           = mapped_column(String(80),  nullable=False, unique=True)
    slug:          Mapped[str | None]    = mapped_column(String(80),  nullable=True, unique=True)
    label:         Mapped[str]           = mapped_column(String(120), nullable=False)
    description:   Mapped[str | None]    = mapped_column(Text,        nullable=True)
    icon:          Mapped[str | None]    = mapped_column(String(60),  nullable=True)
    color:         Mapped[str | None]    = mapped_column(String(20),  nullable=True)
    is_enabled:    Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=True)
    is_beta:       Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=False)
    sort_order:    Mapped[int]           = mapped_column(Integer,     nullable=False, default=0)
    finance_model: Mapped[str | None]    = mapped_column(String(40),  nullable=True)
    meta:          Mapped[dict | None]   = mapped_column(JSONB,       nullable=True)

    # Phase 1 — canonical registry additions (migration 148).
    lifecycle_status:  Mapped[str]        = mapped_column(String(20), nullable=False, default="active")
    registration_allowed: Mapped[bool]    = mapped_column(Boolean, nullable=False, default=True)
    capabilities:       Mapped[list | None] = mapped_column(JSONB, nullable=True)
    onboarding_requirements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    enabled_by:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    disabled_by:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    enabled_at:    Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at:   Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    disable_reason: Mapped[str | None]      = mapped_column(String(500), nullable=True)


class CatalogModuleDefinition(ServiceOSBase):
    __tablename__ = "catalog_module_definitions"
    __table_args__ = (
        Index("ix_cmd_key",          "key"),
        Index("ix_cmd_is_universal", "is_universal"),
    )

    key:          Mapped[str]        = mapped_column(String(80),  nullable=False, unique=True)
    label:        Mapped[str]        = mapped_column(String(120), nullable=False)
    description:  Mapped[str | None] = mapped_column(Text,        nullable=True)
    icon:         Mapped[str | None] = mapped_column(String(60),  nullable=True)
    admin_path:   Mapped[str | None] = mapped_column(String(200), nullable=True)
    module_group: Mapped[str | None] = mapped_column(String(60),  nullable=True)
    is_universal: Mapped[bool]       = mapped_column(Boolean,     nullable=False, default=False)
    sort_order:   Mapped[int]        = mapped_column(Integer,     nullable=False, default=0)


class VerticalCatalogModule(ServiceOSBase):
    __tablename__ = "vertical_catalog_modules"
    __table_args__ = (
        UniqueConstraint("vertical_id", "module_id", name="uq_vcm_vertical_module"),
        Index("ix_vcm_vertical_id", "vertical_id"),
        Index("ix_vcm_module_id",   "module_id"),
    )

    vertical_id:  Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    module_id:    Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    is_enabled:   Mapped[bool]       = mapped_column(Boolean, nullable=False, default=True)
    is_required:  Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    sort_order:   Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    custom_label: Mapped[str | None] = mapped_column(String(120), nullable=True)


class VerticalMenuConfig(ServiceOSBase):
    __tablename__ = "vertical_menu_config"
    __table_args__ = (
        Index("ix_vmc_vertical_id", "vertical_id"),
    )

    vertical_id: Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    menu_items:  Mapped[list | None]   = mapped_column(JSONB, nullable=True)


class TenantVerticalEnrollment(ServiceOSBase):
    """A tenant's independent lifecycle status within ONE vertical (migration 148).

    A tenant operating in multiple verticals holds one row per vertical here,
    each with its own status — approving/suspending one enrollment must never
    touch another vertical's enrollment for the same tenant.
    """
    __tablename__ = "tenant_vertical_enrollments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "vertical_id", name="uq_tve_tenant_vertical"),
        Index("ix_tve_tenant_id",  "tenant_id"),
        Index("ix_tve_vertical_id", "vertical_id"),
        Index("ix_tve_status", "status"),
    )

    tenant_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vertical_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # draft -> submitted -> under_review -> (changes_requested) -> approved -> active
    #   -> suspended / rejected (suspended/active are mutually reversible)
    status:       Mapped[str]       = mapped_column(String(20), nullable=False, default="draft")
    requested_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at:  Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    suspend_reason:   Mapped[str | None] = mapped_column(String(500), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changes_requested_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    admin_notes:  Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class VerticalAuditLog(ServiceOSBase):
    """Platform-level audit trail for vertical enable/disable/capability changes
    and tenant-vertical-enrollment lifecycle transitions (migration 148).
    Separate from `tenant_audit_logs` since vertical-level events (e.g.
    disabling a vertical platform-wide) are not tied to a single tenant."""
    __tablename__ = "vertical_audit_logs"
    __table_args__ = (
        Index("ix_val_vertical_id", "vertical_id"),
        Index("ix_val_tenant_id",   "tenant_id"),
    )

    vertical_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_type: Mapped[str]              = mapped_column(String(60), nullable=False)
    before_state: Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    after_state:  Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    notes:        Mapped[str | None]      = mapped_column(String(500), nullable=True)


class VerticalEngineMapping(ServiceOSBase):
    """Which backend engines a vertical depends on (migration 090)."""
    __tablename__ = "vertical_engine_mappings"
    __table_args__ = (
        UniqueConstraint("vertical_id", "engine_key", name="uq_vem_vertical_engine"),
        Index("ix_vem_vertical_id", "vertical_id"),
    )

    vertical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    engine_key:  Mapped[str]       = mapped_column(String(80), nullable=False)
    is_required: Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    sort_order:  Mapped[int]       = mapped_column(Integer, nullable=False, default=0)
