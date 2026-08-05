"""NOTIFICATION-CENTER-REBUILD Phase 3/4: NotificationPolicy -- the Event
Policies tab's backing entity.

Distinct from THREE existing things it must not be confused with:
  - NotificationEventRegistry (event_registry.py): code-defined, describes
    WHAT events exist and their default channels/mandatory flag. Read-only
    at runtime.
  - NotifEventTemplate (models.py): the rendered title/body copy for one
    event+channel. Unversioned today.
  - NotificationPolicy (here): the admin-configurable, versioned RULES for
    one event in one vertical -- recipient roles, required/fallback
    channels, escalation, retry/dedup/quiet-hours, and the safety
    guarantees the pipeline already provides (surfaced read-only, never
    toggleable -- isolation is a structural guarantee of fire_event(),
    not an admin setting).

Versioned like VerticalMonetizationPolicy: draft -> published -> superseded,
one is_current row per (event_key, vertical_key), immutable once published.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

DELIVERY_MODES = {"immediate", "digest"}
RECIPIENT_ROLES = {
    "customer", "provider", "assigned_staff", "technician",
    "operations_admin", "finance_admin", "security_admin", "escalation",
}


class NotificationPolicy(ServiceOSBase):
    __tablename__ = "notification_policies"
    __table_args__ = (
        Index("ix_notif_policy_event", "event_key"),
        Index("ix_notif_policy_vertical", "vertical_key"),
        # One current published policy per event+vertical scope (NULL vertical = global).
        Index("ix_notif_policy_current", "event_key", "vertical_key", unique=True,
              postgresql_where="is_current = true"),
        UniqueConstraint("event_key", "vertical_key", "version_number", name="uq_notif_policy_version"),
    )

    event_key:      Mapped[str]            = mapped_column(String(120), nullable=False)
    vertical_key:   Mapped[str | None]     = mapped_column(String(80), nullable=True)
    version_number: Mapped[int]            = mapped_column(Integer, nullable=False)
    status:         Mapped[str]            = mapped_column(String(20), default="draft", nullable=False)
    is_current:     Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)

    delivery_mode:  Mapped[str]            = mapped_column(String(20), default="immediate", nullable=False)

    # Channel policy
    required_channels: Mapped[list]        = mapped_column(JSONB, default=list, nullable=False)
    primary_channels:  Mapped[list]        = mapped_column(JSONB, default=list, nullable=False)
    fallback_channels: Mapped[list]        = mapped_column(JSONB, default=list, nullable=False)
    escalation_delay_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consent_required:  Mapped[bool]        = mapped_column(Boolean, default=False, nullable=False)

    # Delivery controls
    retry_interval_seconds: Mapped[int]    = mapped_column(Integer, default=300, nullable=False)
    max_attempts:            Mapped[int]   = mapped_column(Integer, default=3, nullable=False)
    dedup_window_seconds:    Mapped[int]   = mapped_column(Integer, default=600, nullable=False)
    rate_limit_per_hour:     Mapped[int | None] = mapped_column(Integer, nullable=True)
    quiet_hours_start:       Mapped[str | None] = mapped_column(String(5), nullable=True)   # "22:00"
    quiet_hours_end:         Mapped[str | None] = mapped_column(String(5), nullable=True)   # "07:00"
    severity_override_bypasses_quiet_hours: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expiry_minutes:          Mapped[int | None] = mapped_column(Integer, nullable=True)

    change_summary:      Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "event_key": self.event_key, "vertical_key": self.vertical_key,
            "version_number": self.version_number, "status": self.status, "is_current": self.is_current,
            "delivery_mode": self.delivery_mode,
            "required_channels": self.required_channels, "primary_channels": self.primary_channels,
            "fallback_channels": self.fallback_channels,
            "escalation_delay_minutes": self.escalation_delay_minutes,
            "consent_required": self.consent_required,
            "retry_interval_seconds": self.retry_interval_seconds, "max_attempts": self.max_attempts,
            "dedup_window_seconds": self.dedup_window_seconds, "rate_limit_per_hour": self.rate_limit_per_hour,
            "quiet_hours_start": self.quiet_hours_start, "quiet_hours_end": self.quiet_hours_end,
            "severity_override_bypasses_quiet_hours": self.severity_override_bypasses_quiet_hours,
            "expiry_minutes": self.expiry_minutes,
            "change_summary": self.change_summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationPolicyRecipientRule(ServiceOSBase):
    """Child of a specific policy VERSION -- a fresh rule set per version,
    matching the parent's immutability (mirrors MonetizationJobTypeRule)."""
    __tablename__ = "notification_policy_recipient_rules"
    __table_args__ = (
        UniqueConstraint("policy_id", "recipient_role", name="uq_npr_policy_role"),
        Index("ix_npr_policy", "policy_id"),
    )

    policy_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient_role: Mapped[str]       = mapped_column(String(30), nullable=False)
    is_required:    Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    notes:          Mapped[str | None] = mapped_column(String(300), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "policy_id": str(self.policy_id),
            "recipient_role": self.recipient_role, "is_required": self.is_required,
            "notes": self.notes,
        }


class NotificationPolicyAuditLog(ServiceOSBase):
    """Publish-time audit trail -- separate from VerticalAuditLog (that
    table is vertical_catalog's; this stays inside platform_notifications
    so a disabled/retired vertical never loses its policy history)."""
    __tablename__ = "notification_policy_audit_logs"
    __table_args__ = (
        Index("ix_npal_policy", "policy_id"),
        Index("ix_npal_event", "event_key"),
    )

    policy_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_key:   Mapped[str]              = mapped_column(String(120), nullable=False)
    vertical_key: Mapped[str | None]      = mapped_column(String(80), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_type: Mapped[str]              = mapped_column(String(60), nullable=False)
    before_state: Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    after_state:  Mapped[dict | None]     = mapped_column(JSONB, nullable=True)
    notes:        Mapped[str | None]      = mapped_column(String(500), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "policy_id": str(self.policy_id) if self.policy_id else None,
            "event_key": self.event_key, "vertical_key": self.vertical_key,
            "action_type": self.action_type, "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
