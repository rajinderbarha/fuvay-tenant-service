"""
ServiceOS — Engine Registry DB Models
tenant_engines: which engines are enabled per tenant + their config.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class TenantEngine(ServiceOSBase):
    """
    Maps which engines are enabled for each tenant.
    Core engines have is_enabled=True and cannot be disabled via this table.
    Plugin engines start with is_enabled=False and are toggled per tenant.

    The config JSONB stores engine-specific configuration:
    - field_ops: { "sla_hours": 4, "require_photo": true, "auto_close_after_hours": 48 }
    - rag: { "model": "gpt-4o-mini", "chunk_size": 512, "top_k": 5 }
    - payment: { "gateway": "razorpay", "auto_invoice": true }
    """
    __tablename__ = "tenant_engines"
    __table_args__ = (
        UniqueConstraint("tenant_id", "engine_id", name="uq_tenant_engine"),
        Index("ix_tenant_engines_tenant_id", "tenant_id"),
        Index("ix_tenant_engines_engine_id", "engine_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    engine_id: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def enable(self, activated_by: uuid.UUID) -> None:
        self.is_enabled = True
        self.activated_at = utcnow()
        self.deactivated_at = None
        self.activated_by = activated_by

    def disable(self) -> None:
        self.is_enabled = False
        self.deactivated_at = utcnow()
