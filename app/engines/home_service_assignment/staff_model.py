"""Sprint 20 — Read-only SQLAlchemy model for provider_team_members table.

This table was created by Sprint 11 migrations but lives without a Python model.
We define a read-only model here to support staff eligibility lookups.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase


class ProviderTeamMember(ServiceOSBase):
    """Provider team member / technician registered under a tenant."""
    __tablename__ = "provider_team_members"
    __table_args__ = (
        Index("ix_ptm_tenant_id",   "tenant_id"),
        Index("ix_ptm_user_id",     "user_id"),
        Index("ix_ptm_status",      "status"),
    )

    tenant_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    category_id:            Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id:                Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    member_type:            Mapped[str]              = mapped_column(String(50), nullable=False)
    full_name:              Mapped[str]              = mapped_column(String(200), nullable=False)
    phone:                  Mapped[str | None]       = mapped_column(String(30), nullable=True)
    email:                  Mapped[str | None]       = mapped_column(String(200), nullable=True)
    designation:            Mapped[str | None]       = mapped_column(String(100), nullable=True)
    status:                 Mapped[str]              = mapped_column(String(30), nullable=False, default="active")
    can_receive_assignment: Mapped[bool]             = mapped_column(Boolean, nullable=False, default=True)
    skills:                 Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    supported_offering_ids: Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    supported_type_ids:     Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    supported_brand_ids:    Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    service_area_ids:       Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    profile_photo_url:      Mapped[str | None]       = mapped_column(String(500), nullable=True)
    username:               Mapped[str | None]       = mapped_column(String(100), nullable=True)
    password_generated:     Mapped[bool]             = mapped_column(Boolean, nullable=False, default=False)
    last_login_at:          Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at:             Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":                    str(self.id),
            "tenant_id":             str(self.tenant_id),
            "category_id":           str(self.category_id),
            "user_id":               str(self.user_id) if self.user_id else None,
            "member_type":           self.member_type,
            "full_name":             self.full_name,
            "designation":           self.designation,
            "status":                self.status,
            "can_receive_assignment":self.can_receive_assignment,
            "skills":                self.skills,
        }
