"""Payment Engine — Models (4 tables). All append-only. No updates after creation."""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class PaymentRecord(ServiceOSBase):
    """IMMUTABLE after capture. Raw gateway payload stored — replay possible."""
    __tablename__ = "payment_records"
    __table_args__ = (
        UniqueConstraint("gateway_payment_id", name="uq_pr_gateway_id"),
        Index("ix_pr_tenant", "tenant_id"),
        Index("ix_pr_booking", "booking_id"),
        Index("ix_pr_job", "job_id"),
        Index("ix_pr_payment_status", "payment_status"),
    )
    tenant_id:          Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:         Mapped[str|None]     = mapped_column(String(100), nullable=True)
    customer_id:        Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    payment_type:       Mapped[str]          = mapped_column(String(30), nullable=False)
    gateway:            Mapped[str]          = mapped_column(String(20), nullable=False)
    gateway_payment_id: Mapped[str]          = mapped_column(String(100), nullable=False, unique=True)
    gateway_order_id:   Mapped[str|None]     = mapped_column(String(100), nullable=True)
    amount:             Mapped[Decimal]      = mapped_column(Numeric(12,2), nullable=False)
    currency:           Mapped[str]          = mapped_column(String(5), default="INR", nullable=False)
    status:             Mapped[str]          = mapped_column(String(20), nullable=False)
    platform_fee:       Mapped[Decimal]      = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    tax_amount:         Mapped[Decimal]      = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    net_to_tenant:      Mapped[Decimal]      = mapped_column(Numeric(12,2), default=Decimal("0"), nullable=False)
    raw_payload:        Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    invoice_id:         Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    captured_at:        Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason:      Mapped[str|None]     = mapped_column(String(500), nullable=True)
    # Step 9 — job-level on-site/cash payment recording
    job_id:                Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payment_number:        Mapped[str|None]       = mapped_column(String(50), nullable=True, unique=True)
    payment_method:        Mapped[str|None]       = mapped_column(String(30), nullable=True)
    payment_status:        Mapped[str|None]        = mapped_column(String(20), nullable=True)
    collected_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    collected_by_staff_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    paid_at:               Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    notes:                 Mapped[str|None]       = mapped_column(Text, nullable=True)


class RefundRecord(ServiceOSBase):
    """References original PaymentRecord. Never modifies it."""
    __tablename__ = "refund_records"
    __table_args__ = (
        UniqueConstraint("gateway_refund_id", name="uq_rr_gateway_id"),
        Index("ix_rr_payment", "payment_id"),
    )
    payment_id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:          Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    gateway:            Mapped[str]          = mapped_column(String(20), nullable=False)
    gateway_refund_id:  Mapped[str]          = mapped_column(String(100), nullable=False, unique=True)
    amount:             Mapped[Decimal]      = mapped_column(Numeric(12,2), nullable=False)
    reason:             Mapped[str]          = mapped_column(String(500), nullable=False)
    status:             Mapped[str]          = mapped_column(String(20), nullable=False)
    initiated_by:       Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    processed_at:       Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload:        Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)


class InvoiceRecord(ServiceOSBase):
    """Sequential per-tenant invoice numbers via Redis INCR. PDF stored in Media Vault."""
    __tablename__ = "invoice_records"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_ir_number"),
        Index("ix_ir_tenant", "tenant_id"),
        Index("ix_ir_payment", "payment_id"),
        Index("ix_ir_job", "job_id"),
        Index("ix_ir_customer", "customer_id"),
        Index("ix_ir_status", "status"),
    )
    tenant_id:      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    payment_id:     Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    booking_id:     Mapped[str|None]     = mapped_column(String(100), nullable=True)
    invoice_number: Mapped[str]          = mapped_column(String(50), nullable=False, unique=True)
    invoice_type:   Mapped[str]          = mapped_column(String(30), nullable=False)
    amount:         Mapped[Decimal]      = mapped_column(Numeric(12,2), nullable=False)
    tax_amount:     Mapped[Decimal]      = mapped_column(Numeric(10,2), nullable=False)
    total_amount:   Mapped[Decimal]      = mapped_column(Numeric(12,2), nullable=False)
    currency:       Mapped[str]          = mapped_column(String(5), default="INR", nullable=False)
    status:         Mapped[str]          = mapped_column(String(20), default="issued", nullable=False)
    media_file_id:  Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    storage_key:    Mapped[str|None]     = mapped_column(String(500), nullable=True)
    line_items:     Mapped[list]         = mapped_column(JSONB, default=list, nullable=False)
    issued_at:      Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    due_at:         Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    # Step 9 — job-level invoice fields
    job_id:            Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id:        Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    job_type:          Mapped[str|None]       = mapped_column(String(20), nullable=True)
    subtotal_amount:   Mapped[Decimal|None]   = mapped_column(Numeric(12,2), nullable=True)
    parts_amount:      Mapped[Decimal]        = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    labour_amount:     Mapped[Decimal]        = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    visit_fee:         Mapped[Decimal]        = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    discount_amount:   Mapped[Decimal]        = mapped_column(Numeric(10,2), default=Decimal("0"), nullable=False)
    paid_at:           Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    pdf_url:           Mapped[str|None]       = mapped_column(String(500), nullable=True)
    meta:              Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)


class PayoutRecord(ServiceOSBase):
    """Tenant payout disbursement record."""
    __tablename__ = "payout_records"
    __table_args__ = (Index("ix_por_tenant", "tenant_id"),)
    tenant_id:       Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    amount:          Mapped[Decimal]      = mapped_column(Numeric(12,2), nullable=False)
    currency:        Mapped[str]          = mapped_column(String(5), default="INR", nullable=False)
    status:          Mapped[str]          = mapped_column(String(20), nullable=False)
    gateway:         Mapped[str]          = mapped_column(String(20), nullable=False)
    gateway_transfer_id: Mapped[str|None]=mapped_column(String(100), nullable=True)
    bank_account:    Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    requested_by:    Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    processed_at:    Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason:  Mapped[str|None]     = mapped_column(String(500), nullable=True)
    raw_payload:     Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    # Finance Hub enterprise upgrade (migration 078)
    payout_number:   Mapped[str|None]     = mapped_column(String(60), nullable=True)
    payout_type:     Mapped[str]          = mapped_column(String(30), default="tenant_settlement", nullable=False)
    approved_amount: Mapped[Decimal|None] = mapped_column(Numeric(12,2), nullable=True)
    approved_by:     Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at:     Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason:Mapped[str|None]     = mapped_column(String(500), nullable=True)
