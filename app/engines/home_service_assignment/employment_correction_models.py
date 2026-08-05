"""Phase S -- per-skill verification and employment correction-request models.

Confirmed by audit: `ProviderTeamMember.skills` is a raw JSONB blob with no
verification metadata, and no generic "field correction request" workflow
existed anywhere in the codebase. Both are genuinely new, additive tables
(migration 215) -- not a duplicate of any existing employment/staff model.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase

SKILL_STATUS_VERIFIED = "verified"
SKILL_STATUS_PENDING = "pending"

CORRECTION_STATUS_PENDING_REVIEW = "pending_review"
CORRECTION_STATUS_APPROVED = "approved"
CORRECTION_STATUS_CHANGES_REQUESTED = "changes_requested"
CORRECTION_STATUS_REJECTED = "rejected"
CORRECTION_STATUS_APPLIED = "applied"

# Fields a technician may request a correction for (spec section 10). Never
# tenant identity, platform user id, audit records, security state, raw
# permission codes, or another employee's data.
CORRECTABLE_FIELDS = (
    "designation", "reports_to", "service_group", "job_type",
    "skill", "service_area", "joined_at",
)

# Of the correctable fields above, only these can be safely auto-applied by
# writing a single scalar/text field through the canonical employment
# record today. The rest require a tenant admin to make the underlying
# structural change (service/job-type/skill assignment, service-area
# geometry) through the existing admin console -- approving those still
# records a real decision + notification, it just doesn't silently pretend
# a complex reassignment happened with no admin action.
AUTO_APPLY_FIELDS = ("designation", "reports_to")


class StaffSkillRecord(ServiceOSBase):
    __tablename__ = "staff_skill_records"
    __table_args__ = (Index("ix_ssr_tenant_staff", "tenant_id", "staff_member_id"),)

    tenant_id:           Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id:     Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    skill_name:          Mapped[str]             = mapped_column(String(150), nullable=False)
    verification_status: Mapped[str]             = mapped_column(String(20), nullable=False, default=SKILL_STATUS_PENDING)
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    verified_at:         Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at:          Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.skill_name,
            "verification_status": self.verification_status,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class StaffCorrectionRequest(ServiceOSBase):
    __tablename__ = "staff_correction_requests"
    __table_args__ = (
        Index("ix_scr_tenant_staff", "tenant_id", "staff_member_id"),
        Index("ix_scr_status", "status"),
    )

    tenant_id:            Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    staff_member_id:      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    field_key:            Mapped[str]             = mapped_column(String(40), nullable=False)
    current_value:        Mapped[str | None]      = mapped_column(Text, nullable=True)
    requested_value:      Mapped[str]             = mapped_column(Text, nullable=False)
    reason:               Mapped[str]             = mapped_column(Text, nullable=False)
    status:                Mapped[str]            = mapped_column(String(30), nullable=False, default=CORRECTION_STATUS_PENDING_REVIEW)
    reviewer_note:         Mapped[str | None]      = mapped_column(Text, nullable=True)
    reviewed_by_user_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at:           Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at:            Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "field_key": self.field_key,
            "current_value": self.current_value,
            "requested_value": self.requested_value,
            "reason": self.reason,
            "status": self.status,
            "reviewer_note": self.reviewer_note,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "auto_applies": self.field_key in AUTO_APPLY_FIELDS,
        }
