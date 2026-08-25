from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


LEAD_STATUSES = {"new", "contacted", "converted", "closed"}


class PlatformGlobalService(ServiceOSBase):
    """A Fuvay-owned digital service visible independent of customer ZIP."""

    __tablename__ = "platform_global_services"
    __table_args__ = (Index("ix_pgs_active", "is_active"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tagline: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class GlobalServiceLead(ServiceOSBase):
    """A callback request, deliberately separate from bookings and jobs."""

    __tablename__ = "global_service_leads"
    __table_args__ = (
        Index("ix_gsl_service", "global_service_id"),
        Index("ix_gsl_status", "status"),
        Index("ix_gsl_customer", "customer_id"),
    )

    global_service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    zipcode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
