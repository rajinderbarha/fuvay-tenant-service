"""Data Science Engine — Models (7 tables). All predictions immutable after creation."""
import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, Float, Index,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class PredictionRecord(ServiceOSBase):
    """Immutable log of every prediction. Stores inputs + model version + output.
    Replay any prediction by re-running with stored inputs."""
    __tablename__ = "prediction_records"
    __table_args__ = (
        Index("ix_pr_tenant_type", "tenant_id", "prediction_type"),
        Index("ix_pr_created", "created_at"),
    )

    tenant_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    entity_id:        Mapped[str | None]       = mapped_column(String(100), nullable=True)
    entity_type:      Mapped[str | None]       = mapped_column(String(50), nullable=True)
    prediction_type:  Mapped[str]              = mapped_column(String(50), nullable=False)
    model_type:       Mapped[str]              = mapped_column(String(80), nullable=False)
    model_version:    Mapped[str]              = mapped_column(String(40), nullable=False)
    ds_phase:         Mapped[int]              = mapped_column(Integer, nullable=False)
    observation_mode: Mapped[bool]             = mapped_column(Boolean, default=False, nullable=False)
    inputs:           Mapped[dict]             = mapped_column(JSONB, default=dict, nullable=False)
    output:           Mapped[dict]             = mapped_column(JSONB, default=dict, nullable=False)
    confidence:       Mapped[float | None]     = mapped_column(Float, nullable=True)
    computed_at:      Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ChurnSignal(ServiceOSBase):
    """Latest churn risk per tenant. Updated daily via Celery. One active row per tenant."""
    __tablename__ = "churn_signals"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_churn_tenant"),)

    tenant_id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    churn_score:        Mapped[float]     = mapped_column(Float, nullable=False)
    churn_band:         Mapped[str]       = mapped_column(String(20), nullable=False)
    observation_mode:   Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    ds_phase:           Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    contributing_factors: Mapped[list]    = mapped_column(JSONB, default=list, nullable=False)
    signal_values:      Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)
    prev_score:         Mapped[float | None] = mapped_column(Float, nullable=True)
    score_delta:        Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version:      Mapped[str]       = mapped_column(String(40), default="rule_based_v1", nullable=False)
    computed_at:        Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DemandForecast(ServiceOSBase):
    """14-day demand forecast per tenant. One active row per tenant."""
    __tablename__ = "demand_forecasts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "forecast_date", name="uq_df_tenant_date"),
        Index("ix_df_tenant", "tenant_id"),
    )

    tenant_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    forecast_date:    Mapped[date]      = mapped_column(Date, nullable=False)
    horizon_days:     Mapped[int]       = mapped_column(Integer, default=14, nullable=False)
    daily_forecasts:  Mapped[list]      = mapped_column(JSONB, default=list, nullable=False)
    total_predicted:  Mapped[float]     = mapped_column(Float, default=0.0, nullable=False)
    peak_day:         Mapped[str | None]= mapped_column(String(20), nullable=True)
    observation_mode: Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    ds_phase:         Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    model_version:    Mapped[str]       = mapped_column(String(40), default="rule_based_v1", nullable=False)
    computed_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class StaffPerformanceScore(ServiceOSBase):
    """Per-staff composite performance score. Updated after every job close."""
    __tablename__ = "staff_performance_scores"
    __table_args__ = (
        UniqueConstraint("staff_id", "tenant_id", name="uq_sps_staff_tenant"),
        Index("ix_sps_tenant", "tenant_id"),
    )

    staff_id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    composite_score:    Mapped[float]     = mapped_column(Float, nullable=False)
    rank_in_tenant:     Mapped[int]       = mapped_column(Integer, default=1, nullable=False)
    signal_values:      Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)
    jobs_completed:     Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    avg_customer_rating:Mapped[float]     = mapped_column(Float, default=0.0, nullable=False)
    sla_adherence_rate: Mapped[float]     = mapped_column(Float, default=100.0, nullable=False)
    observation_mode:   Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    computed_at:        Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CustomerLTVScore(ServiceOSBase):
    """Customer lifetime value prediction per tenant."""
    __tablename__ = "customer_ltv_scores"
    __table_args__ = (
        UniqueConstraint("customer_id", "tenant_id", name="uq_ltv_customer_tenant"),
        Index("ix_ltv_tenant", "tenant_id"),
    )

    customer_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    predicted_ltv:    Mapped[Decimal]   = mapped_column(Numeric(10, 2), nullable=False)
    ltv_band:         Mapped[str]       = mapped_column(String(20), nullable=False)
    booking_frequency:Mapped[float]     = mapped_column(Float, default=0.0, nullable=False)
    avg_job_value:    Mapped[Decimal]   = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    churn_probability:Mapped[float]     = mapped_column(Float, default=0.5, nullable=False)
    observation_mode: Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    computed_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AnomalyRecord(ServiceOSBase):
    """Detected anomalies with acknowledgment state. Publishes to Notification on creation."""
    __tablename__ = "anomaly_records"
    __table_args__ = (
        Index("ix_ar_tenant_status", "tenant_id", "status"),
        Index("ix_ar_created", "created_at"),
    )

    tenant_id:        Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    anomaly_type:     Mapped[str]          = mapped_column(String(60), nullable=False)
    severity:         Mapped[str]          = mapped_column(String(20), nullable=False)
    description:      Mapped[str]          = mapped_column(Text, nullable=False)
    detected_value:   Mapped[float]        = mapped_column(Float, nullable=False)
    threshold_value:  Mapped[float]        = mapped_column(Float, nullable=False)
    context:          Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    status:           Mapped[str]          = mapped_column(String(20), default="open", nullable=False)
    acknowledged_by:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    acknowledged_at:  Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None]   = mapped_column(String(500), nullable=True)
    notification_sent:Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)


class ModelVersion(ServiceOSBase):
    """MLflow-style model version tracking. Rollback = one API call."""
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("model_type", "version", name="uq_mv_type_version"),
        Index("ix_mv_type_active", "model_type", "is_active"),
    )

    model_type:     Mapped[str]          = mapped_column(String(80), nullable=False)
    version:        Mapped[str]          = mapped_column(String(40), nullable=False)
    is_active:      Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)
    training_date:  Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    training_rows:  Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    metrics:        Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    parameters:     Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    artifact_path:  Mapped[str | None]   = mapped_column(String(500), nullable=True)
    trained_by:     Mapped[str]          = mapped_column(String(50), default="celery_beat", nullable=False)
    notes:          Mapped[str | None]   = mapped_column(String(500), nullable=True)
