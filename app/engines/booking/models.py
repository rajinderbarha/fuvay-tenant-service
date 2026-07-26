"""Booking Engine — Models (4 tables)."""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, DateTime, Index, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class Booking(ServiceOSBase):
    """A customer's intent to purchase a service. Price locked at creation via snapshot."""
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bk_tenant_status",   "tenant_id", "status"),
        Index("ix_bk_customer_status", "customer_id", "status"),
        Index("ix_bk_customer",        "customer_id"),
        Index("ix_bk_idem_key",        "idempotency_key"),
        Index("ix_bk_service_id",      "service_id"),
        Index("ix_bk_address_id",      "address_id"),
        Index("ix_bk_converted_job",   "converted_job_id"),
        Index("ix_bk_scheduled_at",    "scheduled_at"),
    )

    tenant_id:           Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:         Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    service_type_id:     Mapped[str]           = mapped_column(String(100), nullable=False)
    service_category:    Mapped[str]           = mapped_column(String(100), nullable=False)
    status:              Mapped[str]           = mapped_column(String(30), default="draft", nullable=False)
    booking_number:      Mapped[str]           = mapped_column(String(30), nullable=False, unique=True)
    # Price — locked from PriceSnapshot at creation. Never recalculated.
    quoted_price:        Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    price_snapshot_id:   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    # Scheduling
    preferred_date:      Mapped[str|None]      = mapped_column(String(10), nullable=True)
    preferred_slot:      Mapped[str|None]      = mapped_column(String(30), nullable=True)
    scheduled_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Location
    address:             Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    pincode:             Mapped[str|None]      = mapped_column(String(20), nullable=True)
    # Serviceability — set server-side by ServiceabilityService, never trusted from client
    address_id:             Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    matched_service_area_id:Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    coverage_match_level:   Mapped[str|None]       = mapped_column(String(20), nullable=True)
    service_id:              Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    job_type:                Mapped[str|None]       = mapped_column(String(30), nullable=True)
    job_type_id:             Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Extended location (Step 4)
    city:                           Mapped[str|None]       = mapped_column(String(100), nullable=True)
    # Extended serviceability (Step 4) — mapping UUID from TenantServiceAreaService
    matched_service_area_service_id:Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Extended pricing + SLA (Step 4)
    estimated_price:                Mapped[Decimal|None]   = mapped_column(Numeric(10,2), nullable=True)
    final_price:                    Mapped[Decimal|None]   = mapped_column(Numeric(10,2), nullable=True)
    sla_minutes:                    Mapped[int|None]       = mapped_column(Integer, nullable=True)
    # Matching snapshot — top-3 candidates at booking time (Step 4)
    matching_snapshot:              Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    # Preflight
    preflight_passed:    Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    preflight_result:    Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    blocking_reason:     Mapped[str|None]      = mapped_column(String(500), nullable=True)
    # Conversion to job
    job_id:              Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    converted_at:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Confirmation (Step 5)
    confirmed_at:           Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_user_id:   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    # Rejection (Step 5)
    rejected_at:            Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by_user_id:    Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    rejection_reason:       Mapped[str|None]      = mapped_column(String(500), nullable=True)
    # Cancellation
    cancelled_at:           Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason:    Mapped[str|None]      = mapped_column(String(500), nullable=True)
    cancelled_by_user_id:   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    cancellation_policy:    Mapped[str]           = mapped_column(String(20), default="standard", nullable=False)
    within_cancel_window:   Mapped[bool|None]     = mapped_column(Boolean, nullable=True)
    reschedule_count:       Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    # Conversion to Job (Step 5)
    converted_to_job_at:    Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_job_id:       Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    status_updated_at:      Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Idempotency — SHA-256 of (customer+tenant+service+date)
    idempotency_key:     Mapped[str|None]      = mapped_column(String(64), nullable=True, unique=True)
    # Credit reservation reference
    reservation_id:      Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    # Customer Service Credit application (migration 092) — payable_amount is the
    # authoritative "collect from customer" figure shown to provider/technician
    # once credit_applied has been deducted from quoted_price.
    credit_applied:      Mapped[Decimal]       = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    payable_amount:      Mapped[Decimal|None]  = mapped_column(Numeric(10,2), nullable=True)
    # Notes / meta
    customer_notes:      Mapped[str|None]      = mapped_column(Text, nullable=True)
    internal_notes:      Mapped[str|None]      = mapped_column(Text, nullable=True)
    tags:                Mapped[list]          = mapped_column(JSONB, default=list, nullable=False)
    meta:                Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)


class BookingStatusHistory(ServiceOSBase):
    """APPEND-ONLY. Every booking state transition. Full lifecycle queryable."""
    __tablename__ = "booking_status_history"
    __table_args__ = (Index("ix_bsh_booking_id", "booking_id"),)

    booking_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status:    Mapped[str|None]       = mapped_column(String(30), nullable=True)
    to_status:      Mapped[str]            = mapped_column(String(30), nullable=False)
    changed_by:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    changed_by_role:Mapped[str|None]       = mapped_column(String(30), nullable=True)
    reason:         Mapped[str|None]       = mapped_column(String(500), nullable=True)
    meta:           Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)


class BookingNote(ServiceOSBase):
    """Notes attached to a booking — internal or customer-visible."""
    __tablename__ = "booking_notes"
    __table_args__ = (Index("ix_bn_booking_id", "booking_id"),)

    booking_id:  Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    author_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    author_role: Mapped[str|None]       = mapped_column(String(30), nullable=True)
    content:     Mapped[str]            = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)


class BookingRescheduleRequest(ServiceOSBase):
    """One row per reschedule attempt. Tenant accepts or rejects."""
    __tablename__ = "booking_reschedule_requests"
    __table_args__ = (Index("ix_brr_booking_id", "booking_id"),)

    booking_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    requested_by:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    original_slot:    Mapped[str|None]       = mapped_column(String(50), nullable=True)
    requested_slot:   Mapped[str|None]       = mapped_column(String(50), nullable=True)
    requested_date:   Mapped[str|None]       = mapped_column(String(10), nullable=True)
    reason:           Mapped[str|None]       = mapped_column(String(500), nullable=True)
    status:           Mapped[str]            = mapped_column(String(20), default="pending", nullable=False)
    resolved_at:      Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str|None]       = mapped_column(String(500), nullable=True)
