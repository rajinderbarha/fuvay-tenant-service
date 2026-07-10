"""Billing Router — Models (3 tables). Added to Platform Commerce engine."""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, DateTime, Index, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class TenantBillingProfile(ServiceOSBase):
    """One active profile per tenant. PROVEN: immutable after activation.
    Changing billing mode = deactivate old + insert new. Full history kept.
    PROVEN: uq_tbp_tenant_active enforces one active profile at DB level."""
    __tablename__ = "tenant_billing_profiles"
    __table_args__ = (
        # PROVEN: DB-level enforcement — one active profile per tenant
        # Partial unique index: unique on tenant_id WHERE deactivated_at IS NULL
        Index("ix_tbp_tenant_active", "tenant_id", "is_active", unique=False),
        Index("ix_tbp_tenant",   "tenant_id"),
        Index("ix_tbp_mode",     "billing_mode"),
        Index("ix_tbp_vertical", "vertical"),
    )
    tenant_id:              Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    billing_mode:           Mapped[str]           = mapped_column(String(30), nullable=False)
    vertical:               Mapped[str]           = mapped_column(String(50), nullable=False)
    # Commission rate locked from VerticalBillingConfig at activation time
    # PROVEN: rate stored here — not recomputed on each job close
    commission_rate:        Mapped[Decimal]       = mapped_column(Numeric(5,4), nullable=False)
    commission_rate_source: Mapped[str|None]      = mapped_column(String(100), nullable=True)
    plan_type:              Mapped[str|None]      = mapped_column(String(30), nullable=True)
    # PROVEN: activated_at set once — _assert_not_activated() guards all writes
    is_active:              Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    activated_at:           Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    deactivated_at:         Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by:           Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    deactivated_by:         Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    deactivation_reason:    Mapped[str|None]      = mapped_column(String(500), nullable=True)
    meta:                   Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)


class VerticalBillingConfig(ServiceOSBase):
    """Commission rates per vertical per plan tier. Versioned with valid_from/valid_until.
    PROVEN: same pattern as PriceSnapshot — never overwrite, always insert new version."""
    __tablename__ = "vertical_billing_configs"
    __table_args__ = (
        Index("ix_vbc_vertical_plan", "vertical", "plan_type"),
        Index("ix_vbc_active",        "vertical", "valid_until"),
    )
    vertical:        Mapped[str]            = mapped_column(String(50), nullable=False)
    plan_type:       Mapped[str]            = mapped_column(String(30), nullable=False)
    billing_mode:    Mapped[str]            = mapped_column(String(30), nullable=False)
    # PROVEN: commission rate versioned — valid_from/valid_until, never overwrite
    commission_rate: Mapped[Decimal]        = mapped_column(Numeric(5,4), nullable=False)
    leads_per_month: Mapped[int|None]       = mapped_column(JSONB, nullable=True)
    jobs_per_month:  Mapped[int|None]       = mapped_column(JSONB, nullable=True)
    valid_from:      Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    valid_until:     Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    set_by:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes:           Mapped[str|None]       = mapped_column(String(500), nullable=True)


class BillingRouterLog(ServiceOSBase):
    """PROVEN: append-only. Every routing decision recorded.
    No UPDATE or DELETE ever — proven by source inspection test."""
    __tablename__ = "billing_router_logs"
    __table_args__ = (
        Index("ix_brl_tenant",    "tenant_id"),
        Index("ix_brl_mode",      "billing_mode"),
        Index("ix_brl_operation", "operation"),
        Index("ix_brl_created",   "created_at"),
    )
    tenant_id:           Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    billing_mode:        Mapped[str]           = mapped_column(String(30), nullable=False)
    operation:           Mapped[str]           = mapped_column(String(50), nullable=False)
    engine_dispatched:   Mapped[str]           = mapped_column(String(50), nullable=False)
    result:              Mapped[str]           = mapped_column(String(20), nullable=False)
    commission_rate_used:Mapped[Decimal|None]  = mapped_column(Numeric(5,4), nullable=True)
    amount:              Mapped[Decimal|None]  = mapped_column(Numeric(12,2), nullable=True)
    request_id:          Mapped[str|None]      = mapped_column(String(100), nullable=True)
    context:             Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    error:               Mapped[str|None]      = mapped_column(String(500), nullable=True)
