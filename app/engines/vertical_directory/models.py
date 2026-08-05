"""VERTICAL-DIRECTORY-FRAMEWORK: canonical Staff<->Vertical and
Customer<->Vertical relationships. Provider<->Vertical reuses the existing
`vertical_catalog.TenantVerticalEnrollment` (not duplicated here)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class StaffBusinessVertical(ServiceOSBase):
    """Explicit staff-to-vertical assignment. A tenant spanning multiple
    verticals does NOT automatically make its staff available in every one
    -- membership here is what gates a staff member's appearance in a
    vertical's Staff directory."""
    __tablename__ = "staff_business_verticals"
    __table_args__ = (
        UniqueConstraint("staff_id", "vertical_id", name="uq_sbv_staff_vertical"),
        Index("ix_sbv_staff", "staff_id"),
        Index("ix_sbv_tenant", "tenant_id"),
        Index("ix_sbv_vertical", "vertical_id"),
    )

    staff_id:              Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:             Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    vertical_id:           Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    designation:           Mapped[str | None]     = mapped_column(String(60), nullable=True)
    job_type_capabilities: Mapped[list | None]    = mapped_column(JSONB, nullable=True)
    service_capabilities:  Mapped[list | None]    = mapped_column(JSONB, nullable=True)
    is_active:             Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    verification_status:   Mapped[str]            = mapped_column(String(30), default="not_started", nullable=False)
    assignment_status:     Mapped[str]            = mapped_column(String(30), default="assigned", nullable=False)
    availability_status:   Mapped[str]            = mapped_column(String(30), default="unavailable", nullable=False)
    assigned_by_user_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "staff_id": str(self.staff_id), "tenant_id": str(self.tenant_id),
            "vertical_id": str(self.vertical_id), "designation": self.designation,
            "job_type_capabilities": self.job_type_capabilities, "service_capabilities": self.service_capabilities,
            "is_active": self.is_active, "verification_status": self.verification_status,
            "assignment_status": self.assignment_status, "availability_status": self.availability_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CustomerBusinessVertical(ServiceOSBase):
    """Derived/auditable relationship: a customer belongs in a vertical's
    Customer directory only after a real persisted transaction (booking,
    job, payment, subscription, complaint...), never a temporary UI
    selection. One row per (customer, vertical); booking_count/
    first_activity_at/last_activity_at are recalculated as new activity is
    recorded, never backdated."""
    __tablename__ = "customer_business_verticals"
    __table_args__ = (
        UniqueConstraint("customer_id", "vertical_id", name="uq_cbv_customer_vertical"),
        Index("ix_cbv_customer", "customer_id"),
        Index("ix_cbv_vertical", "vertical_id"),
    )

    customer_id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vertical_id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    first_activity_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at:     Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False)
    booking_count:        Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    relationship_status:  Mapped[str]       = mapped_column(String(20), default="active", nullable=False)
    source_relationship:  Mapped[str]       = mapped_column(String(30), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "customer_id": str(self.customer_id), "vertical_id": str(self.vertical_id),
            "first_activity_at": self.first_activity_at.isoformat() if self.first_activity_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "booking_count": self.booking_count, "relationship_status": self.relationship_status,
            "source_relationship": self.source_relationship,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
