"""Sprint 23 — Invoice / Payment / Commission SQLAlchemy models (5 tables)."""
from __future__ import annotations
import uuid
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class ServiceInvoice(ServiceOSBase):
    __tablename__ = "service_invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_si_invoice_number"),
        Index("ix_si_job_id",          "job_id"),
        Index("ix_si_booking_id",      "booking_id"),
        Index("ix_si_tenant_id",       "tenant_id"),
        Index("ix_si_customer_id",     "customer_id"),
        Index("ix_si_status",          "status"),
        Index("ix_si_payment_status",  "payment_status"),
        Index("ix_si_tenant_created_at", "tenant_id", "created_at"),
        Index("uq_si_active_job", "job_id", unique=True,
              postgresql_where=text("status <> 'cancelled'")),
    )
    invoice_number:        Mapped[str]             = mapped_column(String(40),  nullable=False)
    booking_id:            Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:                Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    quote_id:              Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:             Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    status:                Mapped[str]             = mapped_column(String(30), nullable=False, default="draft")
    currency:              Mapped[str]             = mapped_column(String(10), nullable=False, default="INR")
    subtotal_amount:       Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    labour_amount:         Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    parts_amount:          Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    service_amount:        Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    discount_amount:       Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    tax_amount:            Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    total_amount:          Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    # MODULE-L5-10 (migration 141): the per-category customer charge captured on
    # the invoice. customer_payable_amount = total_amount (service value) +
    # platform_fee_amount. Commission is charged on total_amount only.
    platform_fee_amount:   Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    customer_payable_amount: Mapped[Decimal]       = mapped_column(Numeric(14,2), nullable=False, default=0)
    # MODULE-L5-28: service credit the customer applied to reduce what they owe.
    credit_applied_amount: Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    payment_mode:          Mapped[str]             = mapped_column(String(30), nullable=False, default="onsite")
    payment_status:        Mapped[str]             = mapped_column(String(30), nullable=False, default="pending")
    commission_status:     Mapped[str]             = mapped_column(String(30), nullable=False, default="pending")
    invoice_source:        Mapped[str]             = mapped_column(String(30), nullable=False, default="manual_final")
    issued_at:             Mapped[object|None]     = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at:               Mapped[object|None]     = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at:          Mapped[object|None]     = mapped_column(DateTime(timezone=True), nullable=True)
    notes:                 Mapped[str|None]        = mapped_column(Text(), nullable=True)
    created_by_user_id:    Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                      str(self.id),
            "invoice_number":          self.invoice_number,
            "booking_id":              str(self.booking_id),
            "job_id":                  str(self.job_id),
            "quote_id":                str(self.quote_id)   if self.quote_id   else None,
            "tenant_id":               str(self.tenant_id),
            "customer_id":             str(self.customer_id),
            "category_id":             str(self.category_id),
            "offering_id":             str(self.offering_id),
            "status":                  self.status,
            "currency":                self.currency,
            "subtotal_amount":         str(self.subtotal_amount),
            "labour_amount":           str(self.labour_amount),
            "parts_amount":            str(self.parts_amount),
            "service_amount":          str(self.service_amount),
            "discount_amount":         str(self.discount_amount),
            "tax_amount":              str(self.tax_amount),
            "total_amount":            str(self.total_amount),
            "platform_fee_amount":     str(self.platform_fee_amount),
            "customer_payable_amount": str(self.customer_payable_amount),
            "credit_applied_amount":   str(self.credit_applied_amount),
            "payment_mode":            self.payment_mode,
            "payment_status":          self.payment_status,
            "commission_status":       self.commission_status,
            "invoice_source":          self.invoice_source,
            "issued_at":               self.issued_at.isoformat()   if self.issued_at   else None,
            "paid_at":                 self.paid_at.isoformat()     if self.paid_at     else None,
            "cancelled_at":            self.cancelled_at.isoformat() if self.cancelled_at else None,
            "notes":                   self.notes,
            "created_at":              self.created_at.isoformat()  if self.created_at  else None,
            "updated_at":              self.updated_at.isoformat()  if self.updated_at  else None,
        }

    def to_customer_dict(self) -> dict:
        """Customer-safe view — no commission/wallet/provider-internal data."""
        return {
            "id":                      str(self.id),
            "invoice_number":          self.invoice_number,
            "booking_id":              str(self.booking_id),
            "job_id":                  str(self.job_id),
            "status":                  self.status,
            "currency":                self.currency,
            "subtotal_amount":         str(self.subtotal_amount),
            "discount_amount":         str(self.discount_amount),
            "tax_amount":              str(self.tax_amount),
            "total_amount":            str(self.total_amount),
            "platform_fee_amount":     str(self.platform_fee_amount),
            "customer_payable_amount": str(self.customer_payable_amount),
            "credit_applied_amount":   str(self.credit_applied_amount),
            "payment_mode":            "Pay provider directly on-site",
            "payment_status":          self.payment_status,
            "issued_at":               self.issued_at.isoformat() if self.issued_at else None,
            "paid_at":                 self.paid_at.isoformat()   if self.paid_at   else None,
        }


class ServiceInvoiceItem(ServiceOSBase):
    __tablename__ = "service_invoice_items"
    __table_args__ = (
        Index("ix_sii_invoice_id", "invoice_id"),
        Index("ix_sii_job_id",     "job_id"),
        Index("ix_sii_tenant_id",  "tenant_id"),
    )
    invoice_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:               Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:            Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    item_type:            Mapped[str]             = mapped_column(String(30),  nullable=False)
    item_name:            Mapped[str]             = mapped_column(String(255), nullable=False)
    item_description:     Mapped[str|None]        = mapped_column(Text(), nullable=True)
    quantity:             Mapped[Decimal]         = mapped_column(Numeric(10,3), nullable=False, default=1)
    unit_price:           Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    line_total:           Mapped[Decimal]         = mapped_column(Numeric(14,2), nullable=False, default=0)
    source_quote_item_id: Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    is_customer_visible:  Mapped[bool]            = mapped_column(Boolean, nullable=False, default=True)

    def to_dict(self) -> dict:
        return {
            "id":                  str(self.id),
            "invoice_id":         str(self.invoice_id),
            "item_type":          self.item_type,
            "item_name":          self.item_name,
            "item_description":   self.item_description,
            "quantity":           str(self.quantity),
            "unit_price":         str(self.unit_price),
            "line_total":         str(self.line_total),
            "is_customer_visible":self.is_customer_visible,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
        }


class ServicePaymentRecord(ServiceOSBase):
    __tablename__ = "service_payment_records"
    __table_args__ = (
        Index("ix_spr_invoice_id", "invoice_id"),
        Index("ix_spr_job_id",     "job_id"),
        Index("ix_spr_tenant_id",  "tenant_id"),
        Index("ix_spr_customer_reconciliation", "customer_id", "reconciliation_status"),
        Index("ix_spr_tenant_customer_reconciliation", "tenant_id", "customer_id", "reconciliation_status"),
    )
    invoice_id:                    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:                    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:                        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:                     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:                   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    payment_mode:                  Mapped[str]            = mapped_column(String(30), nullable=False)
    payment_status:                Mapped[str]            = mapped_column(String(30), nullable=False, default="pending")
    collected_amount:              Mapped[Decimal]        = mapped_column(Numeric(14,2), nullable=False, default=0)
    currency:                      Mapped[str]            = mapped_column(String(10), nullable=False, default="INR")
    collected_by_user_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    collected_by_staff_member_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    proof_media_url:               Mapped[str|None]       = mapped_column(String(1000), nullable=True)
    customer_confirmation_required:Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    customer_confirmed:            Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    customer_confirmed_at:         Mapped[object|None]    = mapped_column(DateTime(timezone=True), nullable=True)
    provider_confirmed_at:         Mapped[object|None]    = mapped_column(DateTime(timezone=True), nullable=True)
    admin_verified_at:             Mapped[object|None]    = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason:                Mapped[str|None]       = mapped_column(Text(), nullable=True)
    # Found missing from this model entirely during the Final Phase
    # end-to-end pass -- all 17 columns below are real, already-migrated
    # DB columns that direct_payments_service.py actively constructs
    # ServicePaymentRecord with; every /mobile-direct-payment/declare call
    # 500'd on "invalid keyword argument" until these were added back.
    expected_amount:                Mapped[Decimal|None]   = mapped_column(Numeric(14,2), nullable=True)
    payment_reference_id:           Mapped[str|None]       = mapped_column(String(120), nullable=True)
    declaration_note:               Mapped[str|None]       = mapped_column(Text(), nullable=True)
    declaration_version:            Mapped[int]            = mapped_column(Integer, nullable=False, default=1)
    correction_reason:              Mapped[str|None]       = mapped_column(Text(), nullable=True)
    amount_difference_reason:       Mapped[str|None]       = mapped_column(Text(), nullable=True)
    received_at:                    Mapped[object|None]    = mapped_column(DateTime(timezone=True), nullable=True)
    reconciliation_status:          Mapped[str|None]       = mapped_column(String(40), nullable=True)
    customer_reported_amount:       Mapped[Decimal|None]   = mapped_column(Numeric(14,2), nullable=True)
    customer_reported_method:       Mapped[str|None]       = mapped_column(String(40), nullable=True)
    customer_confirmation_action:   Mapped[str|None]       = mapped_column(String(40), nullable=True)
    customer_confirmation_note:     Mapped[str|None]       = mapped_column(Text(), nullable=True)
    dispute_complaint_id:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_reminder_at:               Mapped[object|None]    = mapped_column(DateTime(timezone=True), nullable=True)
    reminder_count:                 Mapped[int]            = mapped_column(Integer, nullable=False, default=0)
    evidence_media_id:              Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence_type:                  Mapped[str|None]       = mapped_column(String(40), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "invoice_id":        str(self.invoice_id),
            "job_id":            str(self.job_id),
            "payment_mode":      self.payment_mode,
            "payment_status":    self.payment_status,
            "collected_amount":  str(self.collected_amount),
            "currency":          self.currency,
            "proof_media_url":   self.proof_media_url,
            "customer_confirmed":self.customer_confirmed,
            "customer_confirmed_at":  self.customer_confirmed_at.isoformat() if self.customer_confirmed_at else None,
            "provider_confirmed_at":  self.provider_confirmed_at.isoformat() if self.provider_confirmed_at else None,
            "admin_verified_at":      self.admin_verified_at.isoformat()     if self.admin_verified_at     else None,
            "failure_reason":    self.failure_reason,
            "expected_amount":   str(self.expected_amount) if self.expected_amount is not None else None,
            "payment_reference_id": self.payment_reference_id,
            "declaration_note":  self.declaration_note,
            "declaration_version": self.declaration_version,
            "reconciliation_status": self.reconciliation_status,
            "evidence_media_id": str(self.evidence_media_id) if self.evidence_media_id else None,
            "evidence_type":     self.evidence_type,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
        }


class SvcCommissionRecord(ServiceOSBase):
    """Sprint 23 commission records for service_jobs. Uses svc_ prefix to avoid collision."""
    __tablename__ = "svc_commission_records"
    __table_args__ = (
        UniqueConstraint("invoice_id", name="uq_svccom_invoice"),
        Index("ix_svccom_tenant_id", "tenant_id"),
        Index("ix_svccom_status",    "status"),
        Index("ix_svccom_idem_key",  "idempotency_key"),
        Index("ix_svccom_tenant_created_at", "tenant_id", "created_at"),
    )
    invoice_id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:                  Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:               Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:                  Mapped[str]            = mapped_column(String(30), nullable=False, default="pending")
    commission_base_amount:  Mapped[Decimal]        = mapped_column(Numeric(14,2), nullable=False, default=0)
    commission_rate:         Mapped[Decimal|None]   = mapped_column(Numeric(5,2), nullable=True)
    commission_fixed_amount: Mapped[Decimal|None]   = mapped_column(Numeric(14,2), nullable=True)
    commission_amount:       Mapped[Decimal]        = mapped_column(Numeric(14,2), nullable=False, default=0)
    currency:                Mapped[str]            = mapped_column(String(10), nullable=False, default="INR")
    wallet_ledger_entry_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    failure_code:            Mapped[str|None]       = mapped_column(String(60), nullable=True)
    failure_message:         Mapped[str|None]       = mapped_column(Text(), nullable=True)
    idempotency_key:         Mapped[str|None]       = mapped_column(String(255), nullable=True)
    calculated_at:           Mapped[object|None]    = mapped_column(DateTime(timezone=True), nullable=True)
    deducted_at:             Mapped[object|None]    = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                      str(self.id),
            "invoice_id":             str(self.invoice_id),
            "job_id":                 str(self.job_id),
            "tenant_id":              str(self.tenant_id),
            "status":                 self.status,
            "commission_base_amount": str(self.commission_base_amount),
            "commission_rate":        str(self.commission_rate) if self.commission_rate else None,
            "commission_amount":      str(self.commission_amount),
            "currency":               self.currency,
            "wallet_ledger_entry_id": str(self.wallet_ledger_entry_id) if self.wallet_ledger_entry_id else None,
            "failure_code":           self.failure_code,
            "failure_message":        self.failure_message,
            "calculated_at":          self.calculated_at.isoformat() if self.calculated_at else None,
            "deducted_at":            self.deducted_at.isoformat()   if self.deducted_at   else None,
            "created_at":             self.created_at.isoformat()    if self.created_at    else None,
        }


class FinancialEvent(ServiceOSBase):
    __tablename__ = "financial_events"
    __table_args__ = (
        Index("ix_fev_record_type", "record_type"),
        Index("ix_fev_record_id",   "record_id"),
        Index("ix_fev_tenant_id",   "tenant_id"),
        Index("ix_fev_event_type",  "event_type"),
        Index("ix_fev_created_at", "created_at"),
        Index("ix_fev_tenant_created_at", "tenant_id", "created_at"),
    )
    record_type:   Mapped[str]             = mapped_column(String(30), nullable=False)
    record_id:     Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:     Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id:   Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_type:    Mapped[str]             = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type:    Mapped[str]             = mapped_column(String(60), nullable=False)
    old_value:     Mapped[dict|None]       = mapped_column(JSONB, nullable=True)
    new_value:     Mapped[dict|None]       = mapped_column(JSONB, nullable=True)
    reason:        Mapped[str|None]        = mapped_column(Text(), nullable=True)
    request_id:    Mapped[str|None]        = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":           str(self.id),
            "record_type":  self.record_type,
            "record_id":    str(self.record_id),
            "tenant_id":    str(self.tenant_id)     if self.tenant_id   else None,
            "actor_type":   self.actor_type,
            "event_type":   self.event_type,
            "old_value":    self.old_value,
            "new_value":    self.new_value,
            "reason":       self.reason,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }
