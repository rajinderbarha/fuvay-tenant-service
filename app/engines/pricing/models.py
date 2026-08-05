"""Pricing Engine — 6 SQLAlchemy models. All price records versioned, never overwritten."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Index, Integer,
    Numeric, String, Text, Time, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class CityTierConfig(ServiceOSBase):
    """Platform-defined minimum prices per city × service category (and optionally per service).
    Admin-managed. Tenants cannot price below the floor_price.
    service_name='' means category-wide fallback; non-empty means service-specific rule."""
    __tablename__ = "city_tier_configs"
    __table_args__ = (
        UniqueConstraint("city_name", "service_category", "service_name",
                         name="uq_ctc_city_category_service"),
        Index("ix_ctc_tier", "tier"),
    )
    city_name:                Mapped[str]           = mapped_column(String(100), nullable=False)
    tier:                     Mapped[str]           = mapped_column(String(20),  nullable=False)
    service_category:         Mapped[str]           = mapped_column(String(100), nullable=False)
    service_name:             Mapped[str]           = mapped_column(String(200), nullable=False, default="")
    floor_price:              Mapped[Decimal]       = mapped_column(Numeric(10,2), nullable=False)
    min_price:                Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    max_price:                Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    default_estimate:         Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    visit_fee:                Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    bargain_floor:            Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    provider_override_allowed:Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    currency:                 Mapped[str]           = mapped_column(String(5), default="INR", nullable=False)
    is_active:                Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    set_by:                   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    notes:                    Mapped[str|None]      = mapped_column(Text, nullable=True)
    catalog_category_id:      Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)


class ServiceTypePrice(ServiceOSBase):
    """Tenant price per service type. VERSIONED — valid_until set on supersede, never deleted.
    Always one active row per (tenant_id, service_type_id) where valid_until IS NULL."""
    __tablename__ = "service_type_prices"
    __table_args__ = (
        Index("ix_stp_tenant_type", "tenant_id", "service_type_id"),
        Index("ix_stp_active", "tenant_id", "service_type_id", "valid_until"),
    )
    tenant_id:       Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    service_type_id: Mapped[str]          = mapped_column(String(100), nullable=False)
    service_category:Mapped[str]          = mapped_column(String(100), nullable=False)
    city_name:       Mapped[str]          = mapped_column(String(100), nullable=False)
    base_price:      Mapped[Decimal]      = mapped_column(Numeric(10,2), nullable=False)
    unit:            Mapped[str]          = mapped_column(String(30), default="per_visit", nullable=False)
    valid_from:      Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    valid_until:     Mapped[datetime|None]= mapped_column(DateTime(timezone=True), nullable=True)
    set_by:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_reason:   Mapped[str|None]     = mapped_column(String(500), nullable=True)
    previous_price:  Mapped[Decimal|None] = mapped_column(Numeric(10,2), nullable=True)


class BrandAdjustment(ServiceOSBase):
    """Tenant brand positioning — premium markup or budget discount on all prices.
    One active row per tenant. Versioned like ServiceTypePrice."""
    __tablename__ = "brand_adjustments"
    __table_args__ = (
        Index("ix_ba_tenant", "tenant_id"),
    )
    tenant_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    adjustment_pct:Mapped[Decimal]       = mapped_column(Numeric(6,2), nullable=False)  # -50 to +50
    label:         Mapped[str|None]      = mapped_column(String(100), nullable=True)    # "Premium", "Budget"
    valid_from:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    valid_until:   Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    set_by:        Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    reason:        Mapped[str|None]      = mapped_column(String(500), nullable=True)


class ZoneSurcharge(ServiceOSBase):
    """Tenant-defined geographic zones with a surcharge percentage.
    e.g. remote areas, high-demand neighbourhoods."""
    __tablename__ = "zone_surcharges"
    __table_args__ = (
        Index("ix_zs_tenant", "tenant_id"),
        Index("ix_zs_active", "tenant_id", "is_active"),
    )
    tenant_id:      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    zone_name:      Mapped[str]          = mapped_column(String(100), nullable=False)
    zone_type:      Mapped[str]          = mapped_column(String(30), default="pincode", nullable=False)
    zone_identifiers:Mapped[list]        = mapped_column(JSONB, default=list, nullable=False)
    surcharge_pct:  Mapped[Decimal]      = mapped_column(Numeric(6,2), nullable=False)
    is_active:      Mapped[bool]         = mapped_column(Boolean, default=True, nullable=False)
    set_by:         Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    notes:          Mapped[str|None]     = mapped_column(Text, nullable=True)


class DynamicPricingRule(ServiceOSBase):
    """Time-based pricing overrides. First matching active rule wins (priority order).
    Celery activates/deactivates based on active_from / active_until."""
    __tablename__ = "dynamic_pricing_rules"
    __table_args__ = (
        Index("ix_dpr_tenant_active", "tenant_id", "is_active"),
        Index("ix_dpr_active_from", "active_from"),
        Index("ix_dpr_active_until", "active_until"),
    )
    tenant_id:      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_name:      Mapped[str]          = mapped_column(String(100), nullable=False)
    rule_type:      Mapped[str]          = mapped_column(String(30), nullable=False)
    priority:       Mapped[int]          = mapped_column(Integer, default=10, nullable=False)
    adjustment_pct: Mapped[Decimal]      = mapped_column(Numeric(6,2), nullable=False)
    conditions:     Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    applies_to:     Mapped[list]         = mapped_column(JSONB, default=list, nullable=False)
    is_active:      Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    active_from:    Mapped[datetime|None]= mapped_column(DateTime(timezone=True), nullable=True)
    active_until:   Mapped[datetime|None]= mapped_column(DateTime(timezone=True), nullable=True)
    set_by:         Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    last_triggered_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)


class PriceSnapshot(ServiceOSBase):
    """Immutable record of every computed price. Stores full pipeline trace.
    Used for dispute resolution, auditing, and idempotency."""
    __tablename__ = "price_snapshots"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_ps_idem_key"),
        Index("ix_ps_tenant", "tenant_id"),
        Index("ix_ps_booking", "booking_id"),
        Index("ix_ps_created", "created_at"),
    )
    tenant_id:        Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:       Mapped[str|None]     = mapped_column(String(100), nullable=True)
    service_type_id:  Mapped[str]          = mapped_column(String(100), nullable=False)
    service_category: Mapped[str]          = mapped_column(String(100), nullable=False)
    city_name:        Mapped[str]          = mapped_column(String(100), nullable=False)
    pincode:          Mapped[str|None]     = mapped_column(String(20), nullable=True)
    requested_at:     Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    # Pipeline inputs
    pipeline_inputs:  Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    # Step-by-step trace
    step_city_floor:  Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    step_tenant_price:Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    step_brand_adj:   Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    step_zone_surge:  Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    step_dynamic_rule:Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    # Result
    final_price:      Mapped[Decimal]      = mapped_column(Numeric(10,2), nullable=False)
    currency:         Mapped[str]          = mapped_column(String(5), default="INR", nullable=False)
    idempotency_key:  Mapped[str|None]     = mapped_column(String(255), nullable=True, unique=True)
    requested_by:     Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
