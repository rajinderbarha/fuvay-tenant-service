"""FINAL-L5-04B — Tenant Module and Category Entitlement ORM models (migration 132).

Replaces the always-NULL tenant.category_id single-value field with a real
many-to-many entitlement model. See FINAL_L5_04B_ENTITLEMENT_DATA_MODEL_REPORT.md
for the full design rationale.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

ENTITLEMENT_STATUSES = ("ACTIVE", "INACTIVE", "SUSPENDED", "EXPIRED", "PENDING", "ARCHIVED")


class TenantModuleEntitlement(ServiceOSBase):
    """Which platform modules (verticals) a tenant can access."""
    __tablename__ = "tenant_module_entitlements"
    __table_args__ = (
        CheckConstraint(f"status IN {ENTITLEMENT_STATUSES}", name="ck_tme_status_valid"),
        Index("ix_tme_tenant_status", "tenant_id", "status"),
        Index("ix_tme_module_status", "module_id", "status"),
        Index("ix_tme_tenant_module", "tenant_id", "module_id"),
    )

    tenant_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    module_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:          Mapped[str]            = mapped_column(String(20), nullable=False, default="ACTIVE")
    source:          Mapped[str]            = mapped_column(String(40), nullable=False, default="admin_manual")
    configuration:   Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    enabled_at:      Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at:     Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    effective_from:  Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    effective_until: Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    created_by:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    version:         Mapped[int]            = mapped_column(Integer, nullable=False, default=1)


class TenantCategoryEntitlement(ServiceOSBase):
    """Which categories (service_groups) within an entitled module a tenant can access."""
    __tablename__ = "tenant_category_entitlements"
    __table_args__ = (
        CheckConstraint(f"status IN {ENTITLEMENT_STATUSES}", name="ck_tce_status_valid"),
        Index("ix_tce_tenant_status", "tenant_id", "status"),
        Index("ix_tce_category_status", "category_id", "status"),
        Index("ix_tce_module_entitlement", "module_entitlement_id"),
        Index("ix_tce_tenant_category", "tenant_id", "category_id"),
    )

    tenant_id:             Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    module_entitlement_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    status:                Mapped[str]             = mapped_column(String(20), nullable=False, default="ACTIVE")
    source:                Mapped[str]             = mapped_column(String(40), nullable=False, default="admin_manual")
    configuration:         Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    enabled_at:            Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at:           Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_from:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_until:       Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by:            Mapped[uuid.UUID | None]= mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by:            Mapped[uuid.UUID | None]= mapped_column(UUID(as_uuid=True), nullable=True)
    version:                Mapped[int]            = mapped_column(Integer, nullable=False, default=1)


class EntitlementAuditLog(ServiceOSBase):
    """Append-only record of every entitlement mutation."""
    __tablename__ = "entitlement_audit_log"
    __table_args__ = (
        Index("ix_eal_tenant_id", "tenant_id"),
        Index("ix_eal_entity", "entity_type", "entity_id"),
        Index("ix_eal_created_at", "created_at"),
    )

    tenant_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type:     Mapped[str]             = mapped_column(String(20), nullable=False)  # module|category
    entity_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    event:           Mapped[str]             = mapped_column(String(60), nullable=False)
    previous_status: Mapped[str | None]      = mapped_column(String(20), nullable=True)
    new_status:      Mapped[str | None]      = mapped_column(String(20), nullable=True)
    actor_id:        Mapped[uuid.UUID | None]= mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:      Mapped[str | None]      = mapped_column(String(40), nullable=True)
    reason:          Mapped[str | None]      = mapped_column(Text, nullable=True)
    source:          Mapped[str | None]      = mapped_column(String(40), nullable=True)
    request_id:      Mapped[str | None]      = mapped_column(String(80), nullable=True)
