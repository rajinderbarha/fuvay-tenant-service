"""Analytics Engine — Models (2 tables)."""
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class AnalyticsEvent(ServiceOSBase):
    """Raw domain events ingested from all engines. Idempotent on event_id."""
    __tablename__ = "analytics_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_ae_event_id"),
                      Index("ix_ae_tenant_type","tenant_id","event_type"),
                      Index("ix_ae_created","created_at"))

    event_id:    Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    tenant_id:   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    event_type:  Mapped[str]           = mapped_column(String(80), nullable=False)
    engine_id:   Mapped[str]           = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str|None]      = mapped_column(String(50), nullable=True)
    entity_id:   Mapped[str|None]      = mapped_column(String(100), nullable=True)
    actor_id:    Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    payload:     Mapped[dict]          = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DailyMetric(ServiceOSBase):
    """Pre-computed daily rollups. Never recalculate at read time."""
    __tablename__ = "daily_metrics"
    __table_args__ = (UniqueConstraint("tenant_id","metric_date","metric_key",
                                       name="uq_dm_tenant_date_key"),
                      Index("ix_dm_tenant_date","tenant_id","metric_date"))

    tenant_id:   Mapped[uuid.UUID|None]= mapped_column(UUID(as_uuid=True), nullable=True)
    metric_date: Mapped[date]          = mapped_column(Date, nullable=False)
    metric_key:  Mapped[str]           = mapped_column(String(100), nullable=False)
    value_num:   Mapped[Decimal|None]  = mapped_column(Numeric(14,4), nullable=True)
    value_json:  Mapped[dict|None]     = mapped_column(JSONB, nullable=True)
    computed_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
