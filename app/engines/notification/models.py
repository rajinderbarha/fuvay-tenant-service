"""Notification Engine — Models (3 tables)."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class NotificationTemplate(ServiceOSBase):
    """Per-notif-type per-channel templates with variable interpolation.

    Enterprise Template Center fields (migration 102) added alongside the
    original columns — `notif_type`/`is_active` stay in sync with the newer
    `event_type`/`status` so the pre-existing NotificationService.send() path
    keeps working unmodified.
    """
    __tablename__ = "notification_templates"
    __table_args__ = (UniqueConstraint("tenant_id","notif_type","channel",
                                       name="uq_nt_tenant_type_channel"),
                      Index("ix_nt_tenant","tenant_id"))

    tenant_id:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notif_type:   Mapped[str]            = mapped_column(String(80), nullable=False)
    channel:      Mapped[str]            = mapped_column(String(20), nullable=False)
    title:        Mapped[str|None]       = mapped_column(String(255), nullable=True)
    body:         Mapped[str]            = mapped_column(Text, nullable=False)
    variables:    Mapped[list]           = mapped_column(JSONB, default=list, nullable=False)
    is_active:    Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    vertical:     Mapped[str|None]       = mapped_column(String(50), nullable=True)

    # ── Enterprise Template Center (migration 102) ──────────────────────────
    event_type:           Mapped[str|None]  = mapped_column(String(80), nullable=True)
    audience:             Mapped[str|None]  = mapped_column(String(30), nullable=True)
    app_scope:            Mapped[str|None]  = mapped_column(String(30), nullable=True)
    scope_type:           Mapped[str|None]  = mapped_column(String(30), nullable=True)
    category_id:          Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    language:             Mapped[str|None]  = mapped_column(String(10), nullable=True)
    status:               Mapped[str|None]  = mapped_column(String(30), nullable=True)
    subject:              Mapped[str|None]  = mapped_column(String(255), nullable=True)
    html_body:            Mapped[str|None]  = mapped_column(Text, nullable=True)
    plain_text_body:      Mapped[str|None]  = mapped_column(Text, nullable=True)
    action_label:         Mapped[str|None]  = mapped_column(String(100), nullable=True)
    action_url:           Mapped[str|None]  = mapped_column(String(500), nullable=True)
    priority:             Mapped[str|None]  = mapped_column(String(20), nullable=True)
    is_platform_default:  Mapped[bool|None] = mapped_column(Boolean, nullable=True)
    is_system:            Mapped[bool|None] = mapped_column(Boolean, nullable=True)
    fallback_template_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_user_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by_user_id:   Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    archived_at:          Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_admin_dict(self) -> dict:
        return {
            "template_id": str(self.id), "template_key": f"{self.event_type}_{self.audience}_{self.channel}",
            "name": self.title or self.event_type, "event_type": self.event_type,
            "channel": self.channel, "audience": self.audience, "app_scope": self.app_scope,
            "scope_type": self.scope_type, "vertical_key": self.vertical,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "language": self.language, "status": self.status,
            "title": self.title, "subject": self.subject, "body": self.body,
            "html_body": self.html_body, "plain_text_body": self.plain_text_body,
            "action_label": self.action_label, "action_url": self.action_url,
            "priority": self.priority, "variables": self.variables,
            "is_platform_default": self.is_platform_default, "is_system": self.is_system,
            "fallback_template_id": str(self.fallback_template_id) if self.fallback_template_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }


class NotificationTemplateVersion(ServiceOSBase):
    __tablename__ = "notification_template_versions"

    template_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number:      Mapped[int]        = mapped_column(Integer, nullable=False)
    snapshot_json:       Mapped[dict]       = mapped_column(JSONB, nullable=False)
    changed_by_user_id:  Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_reason:       Mapped[str|None]  = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "template_id": str(self.template_id),
            "version_number": self.version_number, "snapshot": self.snapshot_json,
            "change_reason": self.change_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NotificationTestSend(ServiceOSBase):
    __tablename__ = "notification_test_sends"

    template_id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient:           Mapped[str]        = mapped_column(String(255), nullable=False)
    sample_payload_json: Mapped[dict|None] = mapped_column(JSONB, nullable=True)
    rendered_title:      Mapped[str|None]  = mapped_column(Text, nullable=True)
    rendered_body:       Mapped[str|None]  = mapped_column(Text, nullable=True)
    sent_by_user_id:     Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "template_id": str(self.template_id), "recipient": self.recipient,
            "rendered_title": self.rendered_title, "rendered_body": self.rendered_body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NotificationTemplateAuditLog(ServiceOSBase):
    __tablename__ = "notification_template_audit_logs"

    action_type:      Mapped[str]        = mapped_column(String(80), nullable=False)
    template_id:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_role:       Mapped[str|None]  = mapped_column(String(40), nullable=True)
    old_value_json:   Mapped[dict|None] = mapped_column(JSONB, nullable=True)
    new_value_json:   Mapped[dict|None] = mapped_column(JSONB, nullable=True)
    reason:           Mapped[str|None]  = mapped_column(Text, nullable=True)
    request_id:       Mapped[str|None]  = mapped_column(String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "action_type": self.action_type,
            "template_id": str(self.template_id) if self.template_id else None,
            "actor_role": self.actor_role, "old_value": self.old_value_json,
            "new_value": self.new_value_json, "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NotificationRecord(ServiceOSBase):
    """Every dispatched notification. Append-only delivery trace."""
    __tablename__ = "notification_records"
    __table_args__ = (Index("ix_nr_tenant","tenant_id"),
                      Index("ix_nr_recipient","recipient_id"),
                      Index("ix_nr_status","status"),
                      Index("ix_nr_created","created_at"))

    tenant_id:      Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient_id:   Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), nullable=False)
    recipient_type: Mapped[str]          = mapped_column(String(30), nullable=False)
    notif_type:     Mapped[str]          = mapped_column(String(80), nullable=False)
    channel:        Mapped[str]          = mapped_column(String(20), nullable=False)
    title:          Mapped[str|None]     = mapped_column(String(255), nullable=True)
    body:           Mapped[str]          = mapped_column(Text, nullable=False)
    data:           Mapped[dict]         = mapped_column(JSONB, default=dict, nullable=False)
    status:         Mapped[str]          = mapped_column(String(20), default="pending", nullable=False)
    attempt_count:  Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at:Mapped[datetime|None]= mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at:   Mapped[datetime|None]= mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason:  Mapped[str|None]     = mapped_column(String(500), nullable=True)
    idempotency_key:Mapped[str|None]     = mapped_column(String(255), nullable=True, unique=True)
    reference_id:   Mapped[str|None]     = mapped_column(String(100), nullable=True)
    reference_type: Mapped[str|None]     = mapped_column(String(50), nullable=True)
    template_id:    Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)


class NotificationChannelConfig(ServiceOSBase):
    """Per-tenant channel credentials and preferences."""
    __tablename__ = "notification_channel_configs"
    __table_args__ = (UniqueConstraint("tenant_id","channel", name="uq_ncc_tenant_channel"),)

    tenant_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel:     Mapped[str]       = mapped_column(String(20), nullable=False)
    is_enabled:  Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    config:      Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)
    verified_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
