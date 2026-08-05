"""Phase R — per-technician document lifecycle. Confirmed genuinely missing
(audited): `TenantDocument` is tenant-level compliance only, no document
row anywhere references `ProviderTeamMember`. Reuses the generic media
engine purely for file storage (`media_id` below points at a real
`MediaAsset` row) -- this table only tracks the verification lifecycle,
never a second file-storage system.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

DOC_STATUS_PENDING_REVIEW = "pending_review"
DOC_STATUS_VERIFIED = "verified"
DOC_STATUS_CHANGES_REQUESTED = "changes_requested"
DOC_STATUS_REJECTED = "rejected"


class StaffDocument(ServiceOSBase):
    __tablename__ = "staff_documents"
    __table_args__ = (
        Index("ix_sdoc_tenant_staff", "tenant_id", "staff_member_id"),
        Index("ix_sdoc_status", "status"),
    )

    tenant_id:          Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id:    Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    document_type:      Mapped[str]              = mapped_column(String(60), nullable=False)
    media_id:           Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    status:             Mapped[str]              = mapped_column(String(30), nullable=False, default=DOC_STATUS_PENDING_REVIEW)
    expiry_date:        Mapped[date | None]      = mapped_column(Date(), nullable=True)
    reviewer_note:      Mapped[str | None]       = mapped_column(Text(), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at:        Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_user_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    is_current:         Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)
    superseded_at:      Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "document_type": self.document_type, "media_id": str(self.media_id),
            "status": self.status, "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "reviewer_note": self.reviewer_note, "is_current": self.is_current,
            "submitted_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
