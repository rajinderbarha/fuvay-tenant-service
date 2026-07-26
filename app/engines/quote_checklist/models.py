"""Sprint 22 — Quote Approval + Checklist Engine SQLAlchemy models (7 tables)."""
from __future__ import annotations
import uuid
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class ServiceJobQuote(ServiceOSBase):
    __tablename__ = "service_job_quotes"
    __table_args__ = (
        UniqueConstraint("quote_number", name="uq_sjq_quote_number"),
        Index("ix_sjq_job_id",     "job_id"),
        Index("ix_sjq_booking_id", "booking_id"),
        Index("ix_sjq_tenant_id",  "tenant_id"),
        Index("ix_sjq_customer_id","customer_id"),
        Index("ix_sjq_status",     "status"),
    )
    quote_number:              Mapped[str]               = mapped_column(String(40),  nullable=False)
    booking_id:                Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:                    Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:                 Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:               Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by_staff_member_id:Mapped[uuid.UUID | None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_user_id:        Mapped[uuid.UUID | None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    status:                    Mapped[str]               = mapped_column(String(40),  nullable=False, default="draft")
    quote_type:                Mapped[str]               = mapped_column(String(40),  nullable=False, default="repair_quote")
    currency:                  Mapped[str]               = mapped_column(String(10),  nullable=False, default="INR")
    labour_amount:             Mapped[Decimal]           = mapped_column(Numeric(14,2), nullable=False, default=0)
    parts_amount:              Mapped[Decimal]           = mapped_column(Numeric(14,2), nullable=False, default=0)
    service_amount:            Mapped[Decimal]           = mapped_column(Numeric(14,2), nullable=False, default=0)
    discount_amount:           Mapped[Decimal]           = mapped_column(Numeric(14,2), nullable=False, default=0)
    tax_amount:                Mapped[Decimal]           = mapped_column(Numeric(14,2), nullable=False, default=0)
    total_amount:              Mapped[Decimal]           = mapped_column(Numeric(14,2), nullable=False, default=0)
    customer_payable_amount:   Mapped[Decimal]           = mapped_column(Numeric(14,2), nullable=False, default=0)
    provider_internal_notes:   Mapped[str | None]        = mapped_column(Text(),       nullable=True)
    customer_visible_notes:    Mapped[str | None]        = mapped_column(Text(),       nullable=True)
    rejection_reason:          Mapped[str | None]        = mapped_column(Text(),       nullable=True)
    revision_reason:           Mapped[str | None]        = mapped_column(Text(),       nullable=True)
    idempotency_key:           Mapped[str | None]        = mapped_column(String(255),  nullable=True)
    expires_at:                Mapped[object | None]     = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at:               Mapped[object | None]     = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at:               Mapped[object | None]     = mapped_column(DateTime(timezone=True), nullable=True)
    sent_to_customer_at:       Mapped[object | None]     = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at:                 Mapped[object | None]     = mapped_column(DateTime(timezone=True), nullable=True)
    # HOME-SERVICES-RUNTIME-SAFETY Phase 2A -- version lineage (migration 167).
    # create_quote() supersedes the prior current quote for a job rather than
    # letting two independent quote rows both claim to be authoritative.
    version_number:            Mapped[int]               = mapped_column(Integer, nullable=False, default=1)
    is_current:                Mapped[bool]              = mapped_column(Boolean, nullable=False, default=True)
    supersedes_quote_id:       Mapped[uuid.UUID | None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    superseded_at:             Mapped[object | None]     = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by:               Mapped[uuid.UUID | None]  = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                       str(self.id),
            "quote_number":             self.quote_number,
            "booking_id":               str(self.booking_id),
            "job_id":                   str(self.job_id),
            "tenant_id":                str(self.tenant_id),
            "customer_id":              str(self.customer_id),
            "status":                   self.status,
            "quote_type":               self.quote_type,
            "currency":                 self.currency,
            "labour_amount":            str(self.labour_amount),
            "parts_amount":             str(self.parts_amount),
            "service_amount":           str(self.service_amount),
            "discount_amount":          str(self.discount_amount),
            "tax_amount":               str(self.tax_amount),
            "total_amount":             str(self.total_amount),
            "customer_payable_amount":  str(self.customer_payable_amount),
            "provider_internal_notes":  self.provider_internal_notes,
            "customer_visible_notes":   self.customer_visible_notes,
            "rejection_reason":         self.rejection_reason,
            "revision_reason":          self.revision_reason,
            "idempotency_key":          self.idempotency_key,
            "expires_at":               self.expires_at.isoformat() if self.expires_at else None,
            "approved_at":              self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at":              self.rejected_at.isoformat() if self.rejected_at else None,
            "sent_to_customer_at":      self.sent_to_customer_at.isoformat() if self.sent_to_customer_at else None,
            "locked_at":                self.locked_at.isoformat() if self.locked_at else None,
            "version_number":           self.version_number,
            "is_current":               self.is_current,
            "supersedes_quote_id":      str(self.supersedes_quote_id) if self.supersedes_quote_id else None,
            "superseded_at":            self.superseded_at.isoformat() if self.superseded_at else None,
            "approved_by":              str(self.approved_by) if self.approved_by else None,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceJobQuoteItem(ServiceOSBase):
    __tablename__ = "service_job_quote_items"
    __table_args__ = (
        Index("ix_sjqi_quote_id",  "quote_id"),
        Index("ix_sjqi_job_id",    "job_id"),
        Index("ix_sjqi_tenant_id", "tenant_id"),
    )
    quote_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    item_type:           Mapped[str]              = mapped_column(String(30),  nullable=False)
    item_name:           Mapped[str]              = mapped_column(String(255), nullable=False)
    item_description:    Mapped[str | None]       = mapped_column(Text(),      nullable=True)
    quantity:            Mapped[Decimal]          = mapped_column(Numeric(10,3), nullable=False, default=1)
    unit_price:          Mapped[Decimal]          = mapped_column(Numeric(14,2), nullable=False, default=0)
    line_total:          Mapped[Decimal]          = mapped_column(Numeric(14,2), nullable=False, default=0)
    is_required:         Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)
    is_customer_visible: Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)
    item_metadata:       Mapped[dict | None]      = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                str(self.id),
            "quote_id":          str(self.quote_id),
            "job_id":            str(self.job_id),
            "item_type":         self.item_type,
            "item_name":         self.item_name,
            "item_description":  self.item_description,
            "quantity":          str(self.quantity),
            "unit_price":        str(self.unit_price),
            "line_total":        str(self.line_total),
            "is_required":       self.is_required,
            "is_customer_visible": self.is_customer_visible,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
        }


class ServiceJobQuoteEvent(ServiceOSBase):
    __tablename__ = "service_job_quote_events"
    __table_args__ = (
        Index("ix_sjqe_quote_id",  "quote_id"),
        Index("ix_sjqe_job_id",    "job_id"),
        Index("ix_sjqe_tenant_id", "tenant_id"),
    )
    quote_id:       Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:     Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type:     Mapped[str]              = mapped_column(String(20),  nullable=False)
    actor_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type:     Mapped[str]              = mapped_column(String(60),  nullable=False)
    old_status:     Mapped[str | None]       = mapped_column(String(40),  nullable=True)
    new_status:     Mapped[str | None]       = mapped_column(String(40),  nullable=True)
    old_value:      Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    new_value:      Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    reason:         Mapped[str | None]       = mapped_column(Text(),       nullable=True)
    request_id:     Mapped[str | None]       = mapped_column(String(100),  nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":           str(self.id),
            "quote_id":     str(self.quote_id),
            "event_type":   self.event_type,
            "actor_type":   self.actor_type,
            "old_status":   self.old_status,
            "new_status":   self.new_status,
            "reason":       self.reason,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }


class SjChecklistTemplate(ServiceOSBase):
    __tablename__ = "sj_checklist_templates"
    __table_args__ = (
        Index("ix_sjct_category_id", "category_id"),
        Index("ix_sjct_tenant_id",   "tenant_id"),
        Index("ix_sjct_active",      "is_active"),
    )
    category_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    offering_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    template_name:  Mapped[str]              = mapped_column(String(255), nullable=False)
    template_type:  Mapped[str]              = mapped_column(String(30),  nullable=False)
    applies_to:     Mapped[str]              = mapped_column(String(20),  nullable=False, default="offering")
    is_required:    Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    is_active:      Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "category_id":   str(self.category_id)  if self.category_id  else None,
            "offering_id":   str(self.offering_id)  if self.offering_id  else None,
            "tenant_id":     str(self.tenant_id)    if self.tenant_id    else None,
            "template_name": self.template_name,
            "template_type": self.template_type,
            "applies_to":    self.applies_to,
            "is_required":   self.is_required,
            "is_active":     self.is_active,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
        }


class SjChecklistTemplateItem(ServiceOSBase):
    __tablename__ = "sj_checklist_template_items"
    __table_args__ = (
        Index("ix_sjcti_template_id", "template_id"),
    )
    template_id:      Mapped[uuid.UUID]   = mapped_column(UUID(as_uuid=True), nullable=False)
    item_label:       Mapped[str]         = mapped_column(String(255), nullable=False)
    item_description: Mapped[str | None]  = mapped_column(Text(),      nullable=True)
    input_type:       Mapped[str]         = mapped_column(String(20),  nullable=False, default="checkbox")
    is_required:      Mapped[bool]        = mapped_column(Boolean, nullable=False, default=False)
    sort_order:       Mapped[int]         = mapped_column(Integer, nullable=False, default=0)
    options:          Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":               str(self.id),
            "template_id":      str(self.template_id),
            "item_label":       self.item_label,
            "item_description": self.item_description,
            "input_type":       self.input_type,
            "is_required":      self.is_required,
            "sort_order":       self.sort_order,
            "options":          self.options,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }


class ServiceJobChecklist(ServiceOSBase):
    __tablename__ = "service_job_checklists"
    __table_args__ = (
        Index("ix_sjcl_job_id",    "job_id"),
        Index("ix_sjcl_tenant_id", "tenant_id"),
    )
    booking_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:               Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    template_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:               Mapped[str]              = mapped_column(String(20),  nullable=False, default="pending")
    checklist_type:       Mapped[str]              = mapped_column(String(30),  nullable=False)
    created_by_user_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_at:         Mapped[object | None]    = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "booking_id":           str(self.booking_id),
            "job_id":               str(self.job_id),
            "tenant_id":            str(self.tenant_id),
            "template_id":          str(self.template_id) if self.template_id else None,
            "status":               self.status,
            "checklist_type":       self.checklist_type,
            "completed_at":         self.completed_at.isoformat() if self.completed_at else None,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }


class ServiceJobChecklistItem(ServiceOSBase):
    __tablename__ = "service_job_checklist_items"
    __table_args__ = (
        Index("ix_sjcli_checklist_id", "checklist_id"),
        Index("ix_sjcli_job_id",       "job_id"),
    )
    checklist_id:         Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:               Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    item_label:           Mapped[str]              = mapped_column(String(255), nullable=False)
    input_type:           Mapped[str]              = mapped_column(String(20),  nullable=False, default="checkbox")
    is_required:          Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    status:               Mapped[str]              = mapped_column(String(20),  nullable=False, default="pending")
    value_text:           Mapped[str | None]       = mapped_column(Text(), nullable=True)
    value_number:         Mapped[Decimal | None]   = mapped_column(Numeric(14,4), nullable=True)
    value_json:           Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    media_url:            Mapped[str | None]       = mapped_column(String(1000), nullable=True)
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    completed_at:         Mapped[object | None]    = mapped_column(DateTime(timezone=True), nullable=True)
    sort_order:           Mapped[int]              = mapped_column(Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "id":           str(self.id),
            "checklist_id": str(self.checklist_id),
            "job_id":       str(self.job_id),
            "item_label":   self.item_label,
            "input_type":   self.input_type,
            "is_required":  self.is_required,
            "status":       self.status,
            "value_text":   self.value_text,
            "value_number": str(self.value_number) if self.value_number is not None else None,
            "value_json":   self.value_json,
            "media_url":    self.media_url,
            "sort_order":   self.sort_order,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }
