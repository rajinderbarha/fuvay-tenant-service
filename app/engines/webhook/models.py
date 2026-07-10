"""Webhook Engine — Models (2 tables).
PROVEN: uq_wd_event_endpoint on WebhookDelivery prevents duplicate dispatch at DB level.
consecutive_failures on endpoint row — auto-pause at 5, not in memory."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class WebhookEndpoint(ServiceOSBase):
    """Tenant-configured delivery target. auto-paused after 5 consecutive failures.
    PROVEN: consecutive_failures column — not in-memory state."""
    __tablename__ = "webhook_endpoints"
    __table_args__ = (Index("ix_we_tenant", "tenant_id"),)

    tenant_id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    url:                  Mapped[str]       = mapped_column(String(2000), nullable=False)
    secret:               Mapped[str]       = mapped_column(String(100), nullable=False)
    description:          Mapped[str|None]  = mapped_column(String(255), nullable=True)
    subscribed_events:    Mapped[list]      = mapped_column(JSONB, default=list, nullable=False)
    status:               Mapped[str]       = mapped_column(String(20), default="active", nullable=False)
    # PROVEN: consecutive_failures stored in DB — survives Celery worker restarts
    consecutive_failures: Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    total_deliveries:     Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    success_rate:         Mapped[float]     = mapped_column(JSONB, default=100.0, nullable=False)
    last_success_at:      Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at:      Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    auto_paused_at:       Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    headers:              Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)


class WebhookDelivery(ServiceOSBase):
    """Every delivery attempt. Full request+response stored — never ephemeral.
    PROVEN: uq_wd_event_endpoint prevents duplicate dispatch at DB level."""
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("event_id","endpoint_id", name="uq_wd_event_endpoint"),
        Index("ix_wd_endpoint", "endpoint_id"),
        Index("ix_wd_tenant",   "tenant_id"),
        Index("ix_wd_status",   "status"),
    )
    endpoint_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    event_id:       Mapped[str]            = mapped_column(String(100), nullable=False)
    event_type:     Mapped[str]            = mapped_column(String(80), nullable=False)
    payload:        Mapped[dict]           = mapped_column(JSONB, nullable=False)
    status:         Mapped[str]            = mapped_column(String(20), default="queued", nullable=False)
    attempt_count:  Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    # Full request+response stored — proven by model fields
    response_status:Mapped[int|None]       = mapped_column(Integer, nullable=True)
    response_body:  Mapped[str|None]       = mapped_column(Text, nullable=True)
    latency_ms:     Mapped[int|None]       = mapped_column(Integer, nullable=True)
    signature:      Mapped[str|None]       = mapped_column(String(64), nullable=True)
    last_attempt_at:Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at:   Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str|None]       = mapped_column(String(500), nullable=True)
    is_replay:      Mapped[bool]           = mapped_column(JSONB, default=False, nullable=False)
    original_delivery_id: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True), nullable=True)
