"""Service Catalog Engine — Models. Replaces hardcoded services with
tenant-defined ones; service_type_id is the same string key already used
across booking, field_ops, and pricing engines."""
import uuid
from decimal import Decimal
from sqlalchemy import Boolean, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class ServiceCatalogItem(ServiceOSBase):
    """One service a tenant offers (e.g. 'AC Not Cooling' — repair, post-assessment)."""
    __tablename__ = "service_catalog_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "service_type_id", name="uq_sci_tenant_service_type"),
        Index("ix_sci_tenant_active", "tenant_id", "is_active"),
        Index("ix_sci_category", "tenant_id", "category"),
    )

    tenant_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    service_type_id:  Mapped[str]       = mapped_column(String(100), nullable=False)
    name:             Mapped[str]       = mapped_column(String(200), nullable=False)
    service_type:     Mapped[str]       = mapped_column(String(20), nullable=False)  # repair/service/consultation
    category:         Mapped[str]       = mapped_column(String(100), nullable=False, default="general")
    description:      Mapped[str|None]  = mapped_column(Text, nullable=True)
    pricing_model:    Mapped[str]       = mapped_column(String(20), nullable=False)
    base_price:       Mapped[Decimal|None] = mapped_column(Numeric(10, 2), nullable=True)
    max_price:        Mapped[Decimal|None] = mapped_column(Numeric(10, 2), nullable=True)
    visit_fee:        Mapped[Decimal|None] = mapped_column(Numeric(10, 2), nullable=True)
    pre_approval_limit: Mapped[Decimal|None] = mapped_column(Numeric(10, 2), nullable=True)
    estimated_duration_minutes: Mapped[int|None] = mapped_column(Integer, nullable=True)
    checklist_required: Mapped[bool]    = mapped_column(Boolean, default=False, nullable=False)
    checklist_template: Mapped[list]    = mapped_column(JSONB, default=list, nullable=False)
    is_active:        Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
