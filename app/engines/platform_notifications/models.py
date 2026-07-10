"""Sprint 27 — Platform Notifications + Chat ORM Models."""
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class NotificationEvent(ServiceOSBase):
    __tablename__ = "notification_events"
    __table_args__ = (
        Index("ix_notif_events_key", "event_key"),
        Index("ix_notif_events_tenant", "tenant_id"),
        Index("ix_notif_events_status", "status"),
        Index("ix_notif_events_created", "created_at"),
    )
    event_key:          Mapped[str]            = mapped_column(String(120), nullable=False)
    event_name:         Mapped[str]            = mapped_column(String(200), nullable=False)
    source_engine:      Mapped[str]            = mapped_column(String(80), nullable=False)
    source_record_type: Mapped[str | None]     = mapped_column(String(80), nullable=True)
    source_record_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payload:            Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    severity:           Mapped[str]            = mapped_column(String(20), default="info", nullable=False)
    status:             Mapped[str]            = mapped_column(String(20), default="created", nullable=False)
    processed_at:       Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "event_key": self.event_key,
            "event_name": self.event_name, "source_engine": self.source_engine,
            "source_record_type": self.source_record_type,
            "source_record_id": str(self.source_record_id) if self.source_record_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "severity": self.severity, "status": self.status,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class NotificationOutbox(ServiceOSBase):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        Index("ix_notif_outbox_status", "delivery_status"),
        Index("ix_notif_outbox_recipient", "recipient_user_id"),
        Index("ix_notif_outbox_event", "notification_event_id"),
        Index("ix_notif_outbox_created", "created_at"),
    )
    notification_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    recipient_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    recipient_type:     Mapped[str]            = mapped_column(String(30), nullable=False)
    tenant_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    channel:            Mapped[str]            = mapped_column(String(20), nullable=False)
    template_key:       Mapped[str]            = mapped_column(String(120), nullable=False)
    title:              Mapped[str]            = mapped_column(String(255), nullable=False)
    body:               Mapped[str]            = mapped_column(Text, nullable=False)
    action_url:         Mapped[str | None]     = mapped_column(String(500), nullable=True)
    action_label:       Mapped[str | None]     = mapped_column(String(100), nullable=True)
    payload:            Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    delivery_status:    Mapped[str]            = mapped_column(String(30), default="pending", nullable=False)
    provider_name:      Mapped[str | None]     = mapped_column(String(80), nullable=True)
    provider_message_id:Mapped[str | None]     = mapped_column(String(255), nullable=True)
    failure_code:       Mapped[str | None]     = mapped_column(String(80), nullable=True)
    failure_message:    Mapped[str | None]     = mapped_column(Text, nullable=True)
    retry_count:        Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    max_retries:        Mapped[int]            = mapped_column(Integer, default=3, nullable=False)
    scheduled_at:       Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    sent_at:            Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at:       Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "notification_event_id": str(self.notification_event_id) if self.notification_event_id else None,
            "recipient_user_id": str(self.recipient_user_id) if self.recipient_user_id else None,
            "recipient_type": self.recipient_type, "channel": self.channel,
            "template_key": self.template_key, "title": self.title, "body": self.body,
            "action_url": self.action_url, "action_label": self.action_label,
            "delivery_status": self.delivery_status, "provider_name": self.provider_name,
            "failure_code": self.failure_code, "failure_message": self.failure_message,
            "retry_count": self.retry_count, "max_retries": self.max_retries,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat(),
        }


class InAppNotification(ServiceOSBase):
    __tablename__ = "in_app_notifications"
    __table_args__ = (
        Index("ix_in_app_notif_user", "user_id"),
        Index("ix_in_app_notif_read", "read_status"),
        Index("ix_in_app_notif_created", "created_at"),
    )
    outbox_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id:            Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notification_type:  Mapped[str]            = mapped_column(String(120), nullable=False)
    title:              Mapped[str]            = mapped_column(String(255), nullable=False)
    body:               Mapped[str]            = mapped_column(Text, nullable=False)
    action_url:         Mapped[str | None]     = mapped_column(String(500), nullable=True)
    action_label:       Mapped[str | None]     = mapped_column(String(100), nullable=True)
    source_record_type: Mapped[str | None]     = mapped_column(String(80), nullable=True)
    source_record_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    severity:           Mapped[str]            = mapped_column(String(20), default="info", nullable=False)
    read_status:        Mapped[str]            = mapped_column(String(20), default="unread", nullable=False)
    read_at:            Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "notification_type": self.notification_type,
            "title": self.title, "body": self.body,
            "action_url": self.action_url, "action_label": self.action_label,
            "source_record_type": self.source_record_type,
            "source_record_id": str(self.source_record_id) if self.source_record_id else None,
            "severity": self.severity, "read_status": self.read_status,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat(),
        }


class NotifEventTemplate(ServiceOSBase):
    __tablename__ = "notif_event_templates"
    __table_args__ = (
        Index("ix_notif_evt_tmpl_key", "template_key"),
        Index("ix_notif_evt_tmpl_channel", "channel"),
    )
    template_key:          Mapped[str]         = mapped_column(String(150), nullable=False, unique=True)
    template_name:         Mapped[str]         = mapped_column(String(200), nullable=False)
    channel:               Mapped[str]         = mapped_column(String(20), nullable=False)
    subject_template:      Mapped[str | None]  = mapped_column(String(255), nullable=True)
    body_template:         Mapped[str]         = mapped_column(Text, nullable=False)
    action_label_template: Mapped[str | None]  = mapped_column(String(100), nullable=True)
    action_url_template:   Mapped[str | None]  = mapped_column(String(500), nullable=True)
    is_active:             Mapped[bool]        = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "template_key": self.template_key,
            "template_name": self.template_name, "channel": self.channel,
            "subject_template": self.subject_template,
            "body_template": self.body_template,
            "action_label_template": self.action_label_template,
            "action_url_template": self.action_url_template,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


class NotificationPreference(ServiceOSBase):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "event_key", "channel", name="uq_notif_pref_user_event_channel"),
        Index("ix_notif_pref_user", "user_id"),
    )
    user_id:    Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_key:  Mapped[str]            = mapped_column(String(120), nullable=False)
    channel:    Mapped[str]            = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "event_key": self.event_key, "channel": self.channel,
            "is_enabled": self.is_enabled,
            "updated_at": self.updated_at.isoformat(),
        }


class ChatThread(ServiceOSBase):
    __tablename__ = "chat_threads"
    __table_args__ = (
        UniqueConstraint("record_type", "record_id", name="uq_chat_thread_record"),
        Index("ix_chat_thread_tenant", "tenant_id"),
        Index("ix_chat_thread_record", "record_type", "record_id"),
        Index("ix_chat_thread_customer", "customer_id"),
    )
    thread_number:      Mapped[str]            = mapped_column(String(40), nullable=False, unique=True)
    tenant_id:          Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    record_type:        Mapped[str]            = mapped_column(String(50), nullable=False)
    record_id:          Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    status:             Mapped[str]            = mapped_column(String(20), default="open", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_message_at:    Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "thread_number": self.thread_number,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "record_type": self.record_type,
            "record_id": str(self.record_id),
            "status": self.status,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat(),
        }


class ChatThreadParticipant(ServiceOSBase):
    __tablename__ = "chat_thread_participants"
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_chat_participant"),
        Index("ix_chat_participant_thread", "thread_id"),
        Index("ix_chat_participant_user", "user_id"),
    )
    thread_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id:          Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    participant_type: Mapped[str]            = mapped_column(String(20), nullable=False)
    tenant_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    can_read:         Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    can_send:         Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    joined_at:        Mapped[datetime]       = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    left_at:          Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "thread_id": str(self.thread_id),
            "user_id": str(self.user_id),
            "participant_type": self.participant_type,
            "can_read": self.can_read, "can_send": self.can_send,
            "joined_at": self.joined_at.isoformat(),
        }


class ChatMessage(ServiceOSBase):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_msg_thread", "thread_id"),
        Index("ix_chat_msg_sender", "sender_user_id"),
        Index("ix_chat_msg_created", "created_at"),
    )
    thread_id:        Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    sender_user_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    sender_type:      Mapped[str]            = mapped_column(String(20), nullable=False)
    message_type:     Mapped[str]            = mapped_column(String(20), default="text", nullable=False)
    message_text:     Mapped[str | None]     = mapped_column(Text, nullable=True)
    media_urls:       Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    msg_metadata:     Mapped[dict | None]    = mapped_column("metadata", JSONB, nullable=True)
    visibility:       Mapped[str]            = mapped_column(String(20), default="thread", nullable=False)
    delivery_status:  Mapped[str]            = mapped_column(String(20), default="sent", nullable=False)
    is_hidden:        Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    hidden_by_user_id:Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    hidden_at:        Mapped[datetime | None]= mapped_column(DateTime(timezone=True), nullable=True)

    def is_visible_to(self, viewer_type: str) -> bool:
        if self.is_hidden:
            return False
        if self.visibility == "thread":
            return True
        if self.visibility == "admin_only":
            return viewer_type == "admin"
        if self.visibility == "provider_only":
            return viewer_type in ("provider", "staff", "admin")
        if self.visibility == "customer_only":
            return viewer_type in ("customer", "admin")
        return True

    def to_dict(self, viewer_type: str = "admin") -> dict:
        if not self.is_visible_to(viewer_type):
            return {}
        return {
            "id": str(self.id),
            "thread_id": str(self.thread_id),
            "sender_user_id": str(self.sender_user_id) if self.sender_user_id else None,
            "sender_type": self.sender_type,
            "message_type": self.message_type,
            "message_text": self.message_text,
            "media_urls": self.media_urls,
            "visibility": self.visibility,
            "delivery_status": self.delivery_status,
            "created_at": self.created_at.isoformat(),
        }


class ChatMessageRead(ServiceOSBase):
    __tablename__ = "chat_message_reads"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_msg_read"),
        Index("ix_msg_reads_user", "user_id"),
        Index("ix_msg_reads_thread", "thread_id"),
    )
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    thread_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    read_at:    Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
