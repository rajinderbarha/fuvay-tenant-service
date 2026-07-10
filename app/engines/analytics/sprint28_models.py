"""Sprint 28 — Analytics ORM models (migration 046).

Two new tables:
  - analytics_daily_metrics  (optional cache for expensive aggregates)
  - analytics_report_runs    (report job tracking)
"""
from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class AnalyticsDailyMetric(ServiceOSBase):
    """Optional summary cache for expensive daily aggregates.

    Upserted by a refresh job; never used as sole source of truth for live APIs.
    The 'metric_metadata' column name uses the SQL alias to avoid the Python
    reserved attribute name 'metadata'.
    """
    __tablename__ = "analytics_daily_metrics"
    __table_args__ = (
        UniqueConstraint(
            "metric_date", "metric_key", "tenant_id", "category_id", "offering_id",
            name="uq_adm_daily",
        ),
        Index("ix_adm_date",       "metric_date"),
        Index("ix_adm_tenant",     "tenant_id"),
        Index("ix_adm_category",   "category_id"),
        Index("ix_adm_metric_key", "metric_key"),
    )

    metric_date:     Mapped[date]             = mapped_column(Date(), nullable=False)
    tenant_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    offering_id:     Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    city:            Mapped[str | None]       = mapped_column(String(100), nullable=True)
    zone_id:         Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metric_key:      Mapped[str]              = mapped_column(String(120), nullable=False)
    metric_value:    Mapped[Decimal]          = mapped_column(Numeric(18, 4), nullable=False, default=0)
    adm_metadata:    Mapped[dict | None]      = mapped_column("metric_metadata", JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":           str(self.id),
            "metric_date":  self.metric_date.isoformat(),
            "tenant_id":    str(self.tenant_id) if self.tenant_id else None,
            "category_id":  str(self.category_id) if self.category_id else None,
            "offering_id":  str(self.offering_id) if self.offering_id else None,
            "city":         self.city,
            "metric_key":   self.metric_key,
            "metric_value": str(self.metric_value),
            "created_at":   self.created_at.isoformat(),
        }


class AnalyticsReportRun(ServiceOSBase):
    """Tracks report generation jobs.

    scope='admin'    → platform-wide report, tenant_id is null
    scope='provider' → tenant-scoped report, tenant_id = requester's tenant
    """
    __tablename__ = "analytics_report_runs"
    __table_args__ = (
        Index("ix_arr_status",       "status"),
        Index("ix_arr_tenant",       "tenant_id"),
        Index("ix_arr_requested_by", "requested_by_user_id"),
        Index("ix_arr_report_key",   "report_key"),
        Index("ix_arr_created_at",   "created_at"),
    )

    report_key:           Mapped[str]              = mapped_column(String(100), nullable=False)
    report_name:          Mapped[str | None]       = mapped_column(String(200), nullable=True)
    scope:                Mapped[str]              = mapped_column(String(20), nullable=False, default="admin")
    requested_by_user_id: Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:               Mapped[str]              = mapped_column(String(20), nullable=False, default="pending")
    filters:              Mapped[dict]             = mapped_column(JSONB, nullable=False, default=dict)
    result_summary:       Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    row_count:            Mapped[int | None]       = mapped_column(Integer, nullable=True)
    file_url:             Mapped[str | None]       = mapped_column(String(1000), nullable=True)
    export_format:        Mapped[str | None]       = mapped_column(String(10), nullable=True)
    failure_reason:       Mapped[str | None]       = mapped_column(Text, nullable=True)
    completed_at:         Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                   str(self.id),
            "report_key":           self.report_key,
            "report_name":          self.report_name,
            "scope":                self.scope,
            "requested_by_user_id": str(self.requested_by_user_id),
            "tenant_id":            str(self.tenant_id) if self.tenant_id else None,
            "status":               self.status,
            "filters":              self.filters,
            "result_summary":       self.result_summary,
            "row_count":            self.row_count,
            "file_url":             self.file_url,
            "export_format":        self.export_format,
            "failure_reason":       self.failure_reason,
            "created_at":           self.created_at.isoformat(),
            "completed_at":         self.completed_at.isoformat() if self.completed_at else None,
        }
