"""Review Engine — Models (4 tables)."""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, DateTime, Float, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class Review(ServiceOSBase):
    """Customer review of a completed job.
    PROVEN: uq_review_customer_job prevents duplicate reviews at DB level."""
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("customer_id", "job_id", name="uq_review_customer_job"),
        Index("ix_rv_tenant", "tenant_id"),
        Index("ix_rv_staff",  "staff_id"),
        Index("ix_rv_status", "status"),
    )
    tenant_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    job_id:          Mapped[str]            = mapped_column(String(100), nullable=False)
    customer_id:     Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_id:        Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Five signals — each 1-5
    overall_quality: Mapped[float]          = mapped_column(Float, nullable=False)
    punctuality:     Mapped[float]          = mapped_column(Float, nullable=False)
    cleanliness:     Mapped[float]          = mapped_column(Float, nullable=False)
    value_for_money: Mapped[float]          = mapped_column(Float, nullable=False)
    communication:   Mapped[float]          = mapped_column(Float, nullable=False)
    composite_score: Mapped[float]          = mapped_column(Float, nullable=False)
    comment:         Mapped[str|None]       = mapped_column(Text, nullable=True)
    status:          Mapped[str]            = mapped_column(String(20), default="published", nullable=False)
    # Tenant reply — one only, enforced at service layer
    tenant_reply:    Mapped[str|None]       = mapped_column(Text, nullable=True)
    replied_at:      Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    replied_by:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Moderation
    flagged_reason:  Mapped[str|None]       = mapped_column(String(500), nullable=True)
    flagged_by:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolved_by:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    idempotency_key: Mapped[str|None]       = mapped_column(String(64), nullable=True, unique=True)


class ReviewRequest(ServiceOSBase):
    """Created on job.closed event. Expires after 7 days."""
    __tablename__ = "review_requests"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_rvreq_job"),
        Index("ix_rvreq_customer", "customer_id"),
    )
    job_id:      Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    tenant_id:   Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_id:    Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    status:      Mapped[str]           = mapped_column(String(20), default="sent", nullable=False)
    expires_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False)
    review_id:   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    notified_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewAggregate(ServiceOSBase):
    """Pre-computed aggregates. Never queried at AVG() read time.
    PROVEN: test queries this table directly — not the average endpoint."""
    __tablename__ = "review_aggregates"
    __table_args__ = (
        UniqueConstraint("entity_type","entity_id", name="uq_rvagg_entity"),
        Index("ix_rvagg_tenant", "tenant_id"),
    )
    entity_type:        Mapped[str]        = mapped_column(String(20), nullable=False)
    entity_id:          Mapped[str]        = mapped_column(String(100), nullable=False)
    tenant_id:          Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    review_count:       Mapped[int]        = mapped_column(Integer, default=0, nullable=False)
    avg_composite:      Mapped[float]      = mapped_column(Float, default=0.0, nullable=False)
    avg_quality:        Mapped[float]      = mapped_column(Float, default=0.0, nullable=False)
    avg_punctuality:    Mapped[float]      = mapped_column(Float, default=0.0, nullable=False)
    avg_cleanliness:    Mapped[float]      = mapped_column(Float, default=0.0, nullable=False)
    avg_value:          Mapped[float]      = mapped_column(Float, default=0.0, nullable=False)
    avg_communication:  Mapped[float]      = mapped_column(Float, default=0.0, nullable=False)
    reply_rate:         Mapped[float]      = mapped_column(Float, default=0.0, nullable=False)
    last_computed_at:   Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReviewStatusHistory(ServiceOSBase):
    """APPEND-ONLY. Every review state change recorded."""
    __tablename__ = "review_status_history"
    __table_args__ = (Index("ix_rvsh_review", "review_id"),)
    review_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status: Mapped[str|None]       = mapped_column(String(20), nullable=True)
    to_status:   Mapped[str]            = mapped_column(String(20), nullable=False)
    changed_by:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason:      Mapped[str|None]       = mapped_column(String(500), nullable=True)
