"""Sprint 24 — Customer Reviews ORM models (migration 042)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CustomerReview(Base):
    __tablename__ = "customer_reviews"
    __table_args__ = (
        UniqueConstraint("review_number", name="uq_cr_number"),
        UniqueConstraint("customer_id", "record_type", "record_id", name="uq_cr_customer_record"),
        Index("ix_cr_tenant_id",     "tenant_id"),
        Index("ix_cr_customer_id",   "customer_id"),
        Index("ix_cr_status",        "status"),
        Index("ix_cr_created_at",    "created_at"),
        Index("ix_cr_tenant_status", "tenant_id", "status"),
        Index("ix_cr_tenant_created","tenant_id", "created_at"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_number    = Column(String(40), nullable=False)
    customer_id      = Column(UUID(as_uuid=True), nullable=False)
    tenant_id        = Column(UUID(as_uuid=True), nullable=False)
    category_id      = Column(UUID(as_uuid=True), nullable=True)
    offering_id      = Column(UUID(as_uuid=True), nullable=True)
    record_type      = Column(String(40), nullable=False)
    record_id        = Column(UUID(as_uuid=True), nullable=False)
    booking_id       = Column(UUID(as_uuid=True), nullable=True)
    job_id           = Column(UUID(as_uuid=True), nullable=True)
    appointment_id   = Column(UUID(as_uuid=True), nullable=True)
    lead_id          = Column(UUID(as_uuid=True), nullable=True)
    staff_member_id  = Column(UUID(as_uuid=True), nullable=True)
    agent_id         = Column(UUID(as_uuid=True), nullable=True)

    overall_rating       = Column(Integer, nullable=False)
    provider_rating      = Column(Integer, nullable=True)
    staff_rating         = Column(Integer, nullable=True)
    communication_rating = Column(Integer, nullable=True)
    punctuality_rating   = Column(Integer, nullable=True)
    quality_rating       = Column(Integer, nullable=True)
    value_rating         = Column(Integer, nullable=True)

    review_title    = Column(String(200), nullable=True)
    review_text     = Column(Text, nullable=True)
    review_tags     = Column(JSONB, nullable=True)
    media_urls      = Column(JSONB, nullable=True)

    status          = Column(String(30), nullable=False, default="pending")
    visibility      = Column(String(40), nullable=False, default="private_until_approved")
    moderation_reason = Column(Text, nullable=True)
    rejection_reason  = Column(Text, nullable=True)

    edited_at    = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_at  = Column(DateTime(timezone=True), nullable=True)
    rejected_at  = Column(DateTime(timezone=True), nullable=True)
    hidden_at    = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at   = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":               str(self.id),
            "review_number":    self.review_number,
            "customer_id":      str(self.customer_id),
            "tenant_id":        str(self.tenant_id),
            "category_id":      str(self.category_id) if self.category_id else None,
            "offering_id":      str(self.offering_id) if self.offering_id else None,
            "record_type":      self.record_type,
            "record_id":        str(self.record_id),
            "booking_id":       str(self.booking_id) if self.booking_id else None,
            "job_id":           str(self.job_id) if self.job_id else None,
            "appointment_id":   str(self.appointment_id) if self.appointment_id else None,
            "lead_id":          str(self.lead_id) if self.lead_id else None,
            "staff_member_id":  str(self.staff_member_id) if self.staff_member_id else None,
            "agent_id":         str(self.agent_id) if self.agent_id else None,
            "overall_rating":       self.overall_rating,
            "provider_rating":      self.provider_rating,
            "staff_rating":         self.staff_rating,
            "communication_rating": self.communication_rating,
            "punctuality_rating":   self.punctuality_rating,
            "quality_rating":       self.quality_rating,
            "value_rating":         self.value_rating,
            "review_title":     self.review_title,
            "review_text":      self.review_text,
            "review_tags":      self.review_tags,
            "media_urls":       self.media_urls,
            "status":           self.status,
            "visibility":       self.visibility,
            "moderation_reason":self.moderation_reason,
            "rejection_reason": self.rejection_reason,
            "edited_at":        self.edited_at.isoformat() if self.edited_at else None,
            "submitted_at":     self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at":      self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at":      self.rejected_at.isoformat() if self.rejected_at else None,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "updated_at":       self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_public_dict(self) -> dict:
        d = self.to_dict()
        d.pop("customer_id", None)
        d.pop("moderation_reason", None)
        return d


class ReviewReply(Base):
    __tablename__ = "review_replies"
    __table_args__ = (
        UniqueConstraint("review_id", name="uq_rr_review"),
    )

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id          = Column(UUID(as_uuid=True), nullable=False)
    tenant_id          = Column(UUID(as_uuid=True), nullable=False)
    replied_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    reply_text         = Column(Text, nullable=False)
    status             = Column(String(20), nullable=False, default="pending")
    moderation_reason  = Column(Text, nullable=True)
    submitted_at       = Column(DateTime(timezone=True), nullable=True)
    approved_at        = Column(DateTime(timezone=True), nullable=True)
    created_at         = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at         = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "review_id":          str(self.review_id),
            "tenant_id":          str(self.tenant_id),
            "replied_by_user_id": str(self.replied_by_user_id) if self.replied_by_user_id else None,
            "reply_text":         self.reply_text,
            "status":             self.status,
            "moderation_reason":  self.moderation_reason,
            "submitted_at":       self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at":        self.approved_at.isoformat() if self.approved_at else None,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
            "updated_at":         self.updated_at.isoformat() if self.updated_at else None,
        }


class ReviewFlag(Base):
    __tablename__ = "review_flags"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id          = Column(UUID(as_uuid=True), nullable=False)
    tenant_id          = Column(UUID(as_uuid=True), nullable=True)
    flagged_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    flagged_by_type    = Column(String(20), nullable=False)
    reason_code        = Column(String(30), nullable=False)
    reason_text        = Column(Text, nullable=True)
    status             = Column(String(20), nullable=False, default="open")
    created_at         = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at         = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                 str(self.id),
            "review_id":          str(self.review_id),
            "tenant_id":          str(self.tenant_id) if self.tenant_id else None,
            "flagged_by_user_id": str(self.flagged_by_user_id) if self.flagged_by_user_id else None,
            "flagged_by_type":    self.flagged_by_type,
            "reason_code":        self.reason_code,
            "reason_text":        self.reason_text,
            "status":             self.status,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
            "updated_at":         self.updated_at.isoformat() if self.updated_at else None,
        }


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id     = Column(UUID(as_uuid=True), nullable=False)
    tenant_id     = Column(UUID(as_uuid=True), nullable=True)
    actor_type    = Column(String(20), nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    event_type    = Column(String(60), nullable=False)
    old_value     = Column(JSONB, nullable=True)
    new_value     = Column(JSONB, nullable=True)
    reason        = Column(Text, nullable=True)
    request_id    = Column(String(100), nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=True, default=_now)

    def to_dict(self) -> dict:
        return {
            "id":            str(self.id),
            "review_id":     str(self.review_id),
            "tenant_id":     str(self.tenant_id) if self.tenant_id else None,
            "actor_type":    self.actor_type,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "event_type":    self.event_type,
            "old_value":     self.old_value,
            "new_value":     self.new_value,
            "reason":        self.reason,
            "request_id":    self.request_id,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }


class TenantRatingSummary(Base):
    __tablename__ = "tenant_rating_summaries"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_trs_tenant"),
    )

    id                           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id                    = Column(UUID(as_uuid=True), nullable=False)
    total_reviews                = Column(Integer, nullable=False, default=0)
    average_rating               = Column(Numeric(4, 2), nullable=False, default=0)
    provider_average_rating      = Column(Numeric(4, 2), nullable=False, default=0)
    communication_average_rating = Column(Numeric(4, 2), nullable=False, default=0)
    punctuality_average_rating   = Column(Numeric(4, 2), nullable=False, default=0)
    quality_average_rating       = Column(Numeric(4, 2), nullable=False, default=0)
    value_average_rating         = Column(Numeric(4, 2), nullable=False, default=0)
    five_star_count              = Column(Integer, nullable=False, default=0)
    four_star_count              = Column(Integer, nullable=False, default=0)
    three_star_count             = Column(Integer, nullable=False, default=0)
    two_star_count               = Column(Integer, nullable=False, default=0)
    one_star_count               = Column(Integer, nullable=False, default=0)
    last_review_at               = Column(DateTime(timezone=True), nullable=True)
    updated_at                   = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                           str(self.id),
            "tenant_id":                    str(self.tenant_id),
            "total_reviews":                self.total_reviews,
            "average_rating":               str(self.average_rating),
            "provider_average_rating":      str(self.provider_average_rating),
            "communication_average_rating": str(self.communication_average_rating),
            "punctuality_average_rating":   str(self.punctuality_average_rating),
            "quality_average_rating":       str(self.quality_average_rating),
            "value_average_rating":         str(self.value_average_rating),
            "five_star_count":              self.five_star_count,
            "four_star_count":              self.four_star_count,
            "three_star_count":             self.three_star_count,
            "two_star_count":               self.two_star_count,
            "one_star_count":               self.one_star_count,
            "last_review_at":               self.last_review_at.isoformat() if self.last_review_at else None,
            "updated_at":                   self.updated_at.isoformat() if self.updated_at else None,
        }


class StaffRatingSummary(Base):
    __tablename__ = "staff_rating_summaries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "staff_member_id", name="uq_srs_staff"),
    )

    id                           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id                    = Column(UUID(as_uuid=True), nullable=False)
    staff_member_id              = Column(UUID(as_uuid=True), nullable=False)
    total_reviews                = Column(Integer, nullable=False, default=0)
    average_rating               = Column(Numeric(4, 2), nullable=False, default=0)
    communication_average_rating = Column(Numeric(4, 2), nullable=False, default=0)
    punctuality_average_rating   = Column(Numeric(4, 2), nullable=False, default=0)
    quality_average_rating       = Column(Numeric(4, 2), nullable=False, default=0)
    last_review_at               = Column(DateTime(timezone=True), nullable=True)
    updated_at                   = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                           str(self.id),
            "tenant_id":                    str(self.tenant_id),
            "staff_member_id":              str(self.staff_member_id),
            "total_reviews":                self.total_reviews,
            "average_rating":               str(self.average_rating),
            "communication_average_rating": str(self.communication_average_rating),
            "punctuality_average_rating":   str(self.punctuality_average_rating),
            "quality_average_rating":       str(self.quality_average_rating),
            "last_review_at":               self.last_review_at.isoformat() if self.last_review_at else None,
            "updated_at":                   self.updated_at.isoformat() if self.updated_at else None,
        }


class ReviewPolicy(Base):
    __tablename__ = "review_policies"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id              = Column(UUID(as_uuid=True), nullable=True)
    tenant_id                = Column(UUID(as_uuid=True), nullable=True)
    policy_key               = Column(String(80), nullable=False)
    policy_name              = Column(String(200), nullable=False)
    auto_approve_enabled     = Column(Boolean, nullable=False, default=False)
    require_admin_moderation = Column(Boolean, nullable=False, default=True)
    allow_provider_reply     = Column(Boolean, nullable=False, default=True)
    require_reply_moderation = Column(Boolean, nullable=False, default=True)
    allow_review_edit        = Column(Boolean, nullable=False, default=True)
    edit_window_hours        = Column(Integer, nullable=False, default=48)
    min_rating               = Column(Integer, nullable=False, default=1)
    max_rating               = Column(Integer, nullable=False, default=5)
    allow_media              = Column(Boolean, nullable=False, default=True)
    max_media_count          = Column(Integer, nullable=False, default=5)
    eligible_statuses        = Column(JSONB, nullable=True)
    is_active                = Column(Boolean, nullable=False, default=True)
    created_at               = Column(DateTime(timezone=True), nullable=True, default=_now)
    updated_at               = Column(DateTime(timezone=True), nullable=True, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id":                       str(self.id),
            "category_id":              str(self.category_id) if self.category_id else None,
            "tenant_id":                str(self.tenant_id) if self.tenant_id else None,
            "policy_key":               self.policy_key,
            "policy_name":              self.policy_name,
            "auto_approve_enabled":     self.auto_approve_enabled,
            "require_admin_moderation": self.require_admin_moderation,
            "allow_provider_reply":     self.allow_provider_reply,
            "require_reply_moderation": self.require_reply_moderation,
            "allow_review_edit":        self.allow_review_edit,
            "edit_window_hours":        self.edit_window_hours,
            "min_rating":               self.min_rating,
            "max_rating":               self.max_rating,
            "allow_media":              self.allow_media,
            "max_media_count":          self.max_media_count,
            "eligible_statuses":        self.eligible_statuses,
            "is_active":                self.is_active,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if self.updated_at else None,
        }
