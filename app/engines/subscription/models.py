"""Subscription Engine — Models (3 tables). Proration from immutable SubscriptionPeriod."""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class Subscription(ServiceOSBase):
    """One active subscription per tenant."""
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_sub_tenant"),)

    tenant_id:       Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    plan_type:       Mapped[str]          = mapped_column(String(30), nullable=False)
    billing_cycle:   Mapped[str]          = mapped_column(String(20), nullable=False)
    status:          Mapped[str]          = mapped_column(String(20), nullable=False)
    amount:          Mapped[Decimal]      = mapped_column(Numeric(10,2), nullable=False)
    currency:        Mapped[str]          = mapped_column(String(5), default="INR", nullable=False)
    current_period_start: Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end:   Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    trial_end:       Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at:    Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    dunning_count:   Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    next_retry_at:   Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    payment_method:  Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    meta:            Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)


class SubscriptionPeriod(ServiceOSBase):
    """IMMUTABLE billing period records. Proration always computed from these rows."""
    __tablename__ = "subscription_periods"
    __table_args__ = (Index("ix_sp_subscription", "subscription_id"),)

    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_type:       Mapped[str]       = mapped_column(String(30), nullable=False)
    started_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at:         Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    amount:          Mapped[Decimal]   = mapped_column(Numeric(10,2), nullable=False)
    status:          Mapped[str]       = mapped_column(String(20), default="active", nullable=False)
    jobs_included:   Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    jobs_used:       Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    overage_amount:  Mapped[Decimal]   = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    payment_id:      Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    invoice_id:      Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)


class SubscriptionEvent(ServiceOSBase):
    """APPEND-ONLY subscription lifecycle events."""
    __tablename__ = "subscription_events"
    __table_args__ = (Index("ix_se_subscription", "subscription_id"),)

    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type:      Mapped[str]       = mapped_column(String(50), nullable=False)
    from_plan:       Mapped[str|None]  = mapped_column(String(30), nullable=True)
    to_plan:         Mapped[str|None]  = mapped_column(String(30), nullable=True)
    proration_amount:Mapped[Decimal|None]=mapped_column(Numeric(10,2), nullable=True)
    actor_id:        Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    meta:            Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)
