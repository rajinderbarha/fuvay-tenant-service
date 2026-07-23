"""Inventory Engine — Models (5 tables). Append-only StockTransaction ledger."""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class InventoryItem(ServiceOSBase):
    """Master item catalogue per tenant."""
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("tenant_id","sku", name="uq_ii_tenant_sku"),
        Index("ix_ii_tenant", "tenant_id"),
    )
    tenant_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name:        Mapped[str]       = mapped_column(String(200), nullable=False)
    sku:         Mapped[str]       = mapped_column(String(100), nullable=False)
    category:    Mapped[str|None]  = mapped_column(String(100), nullable=True)
    unit:        Mapped[str]       = mapped_column(String(20), default="unit", nullable=False)
    unit_cost:   Mapped[Decimal]   = mapped_column(Numeric(10,2), nullable=False)
    min_quantity:Mapped[int]       = mapped_column(Integer, default=5, nullable=False)
    is_active:   Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    meta:        Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)
    # MODULE inventory_document_extraction: "draft" rows come from PDF
    # extraction and are not yet live; "published" is the normal/legacy
    # state (existing rows default here via migration 145's server_default).
    status:      Mapped[str]       = mapped_column(String(20), default="published", nullable=False)
    source_upload_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class InventoryExtractionUpload(ServiceOSBase):
    """One row per PDF uploaded for AI extraction. Idempotent on content_hash
    per tenant (mirrors KBDocument's idempotency pattern in the RAG engine)."""
    __tablename__ = "inventory_extraction_uploads"
    __table_args__ = (
        UniqueConstraint("tenant_id", "content_hash", name="uq_ieu_tenant_hash"),
        Index("ix_ieu_tenant", "tenant_id"),
    )
    tenant_id:             Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_name:             Mapped[str]       = mapped_column(String(255), nullable=False)
    content_hash:          Mapped[str]       = mapped_column(String(64), nullable=False)
    status:                Mapped[str]       = mapped_column(String(20), default="processing", nullable=False)
    error_message:         Mapped[str|None]  = mapped_column(String(1000), nullable=True)
    extracted_item_count:  Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    raw_llm_response:      Mapped[str|None]  = mapped_column(Text, nullable=True)
    uploaded_by:           Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class StockLocation(ServiceOSBase):
    """Warehouse, van, or site locations per tenant."""
    __tablename__ = "stock_locations"
    __table_args__ = (
        UniqueConstraint("tenant_id","location_name","location_type", name="uq_sl2_tenant_loc"),
        Index("ix_sl2_tenant", "tenant_id"),
    )
    tenant_id:     Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    location_name: Mapped[str]          = mapped_column(String(100), nullable=False)
    location_type: Mapped[str]          = mapped_column(String(20), nullable=False)
    staff_id:      Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
    is_active:     Mapped[bool]         = mapped_column(Boolean, default=True, nullable=False)


class StockBalance(ServiceOSBase):
    """Cached balance — always equals SUM(StockTransaction). SELECT FOR UPDATE on writes."""
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint("item_id","location_id", name="uq_sb_item_loc"),
        Index("ix_sb_location", "location_id"),
    )
    item_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    location_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity:     Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    reserved_qty: Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    last_txn_at:  Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)


class StockTransaction(ServiceOSBase):
    """APPEND-ONLY ledger. Every stock movement. SUM() = current balance."""
    __tablename__ = "stock_transactions"
    __table_args__ = (
        Index("ix_stxn_item_loc", "item_id", "location_id"),
        Index("ix_stxn_job", "job_id"),
        UniqueConstraint("idempotency_key", name="uq_stxn_idem"),
    )
    item_id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    location_id:     Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    txn_type:        Mapped[str]          = mapped_column(String(30), nullable=False)
    quantity:        Mapped[int]          = mapped_column(Integer, nullable=False)
    balance_before:  Mapped[int]          = mapped_column(Integer, nullable=False)
    balance_after:   Mapped[int]          = mapped_column(Integer, nullable=False)
    unit_cost:       Mapped[Decimal|None] = mapped_column(Numeric(10,2), nullable=True)
    job_id:          Mapped[str|None]     = mapped_column(String(100), nullable=True)
    reference_id:    Mapped[str|None]     = mapped_column(String(100), nullable=True)
    idempotency_key: Mapped[str|None]     = mapped_column(String(255), nullable=True, unique=True)
    notes:           Mapped[str|None]     = mapped_column(String(500), nullable=True)
    actor_id:        Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)


class StockReservation(ServiceOSBase):
    """Job-level stock hold. TTL enforced by Celery — never orphaned."""
    __tablename__ = "stock_reservations"
    __table_args__ = (
        UniqueConstraint("job_id","item_id","location_id", name="uq_sr_job_item_loc"),
        Index("ix_sr_job", "job_id"),
        Index("ix_sr_status", "status"),
        Index("ix_sr_expires", "expires_at"),
    )
    job_id:      Mapped[str]           = mapped_column(String(100), nullable=False)
    item_id:     Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    location_id: Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:   Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity:    Mapped[int]           = mapped_column(Integer, nullable=False)
    status:      Mapped[str]           = mapped_column(String(20), default="active", nullable=False)
    expires_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
