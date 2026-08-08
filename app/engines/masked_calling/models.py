"""Masked calling — persistence.

Deliberately does NOT store either party's real phone number. Numbers are read
from the booking / staff record at dial time and handed straight to the
telephony provider. Storing them here would create a second surface a leak
could come from, for no functional gain -- the whole point of this engine is
that a number is never at rest anywhere it could be read from.

`caller_id_used` IS stored: it is the platform's own number, which is what both
sides see, so it is not sensitive.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class MaskedCallSession(ServiceOSBase):
    """One bridged conversation about one job."""
    __tablename__ = "masked_call_sessions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_call_id", name="uq_mcs_provider_call_id"),
        Index("ix_mcs_job", "job_id"),
        Index("ix_mcs_tenant_status", "tenant_id", "status"),
    )

    job_id:               Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id:           Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    initiator_role:       Mapped[str]              = mapped_column(String(20), nullable=False)
    direction:            Mapped[str]              = mapped_column(String(30), nullable=False)

    provider:             Mapped[str]              = mapped_column(String(30), nullable=False)
    provider_call_id:     Mapped[str | None]       = mapped_column(String(120), nullable=True)
    caller_id_used:       Mapped[str | None]       = mapped_column(String(30), nullable=True)

    status:               Mapped[str]              = mapped_column(String(30), nullable=False, default="requested")
    failure_reason:       Mapped[str | None]       = mapped_column(String(200), nullable=True)
    duration_seconds:     Mapped[int | None]       = mapped_column(Integer, nullable=True)
    recording_url:        Mapped[str | None]       = mapped_column(String(1000), nullable=True)
    connected_at:         Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at:             Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:           Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        """Safe to return to either party -- contains no real phone number."""
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "booking_id": str(self.booking_id) if self.booking_id else None,
            "tenant_id": str(self.tenant_id),
            "initiator_role": self.initiator_role,
            "direction": self.direction,
            "provider": self.provider,
            "caller_id_used": self.caller_id_used,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "duration_seconds": self.duration_seconds,
            "recording_url": self.recording_url,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
