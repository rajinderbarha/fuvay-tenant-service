"""Chat Engine — Models (2 tables). Typing state is Redis-only — never persisted."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import ServiceOSBase, utcnow


class Conversation(ServiceOSBase):
    """Entity-scoped conversation. Always tenant-scoped in every query.
    PROVEN: every select() in service has .where(Conversation.tenant_id == ...)"""
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("entity_type","entity_id","tenant_id", name="uq_conv_entity"),
        Index("ix_conv_tenant", "tenant_id"),
        Index("ix_conv_entity", "entity_type", "entity_id"),
    )
    tenant_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type:    Mapped[str]       = mapped_column(String(20), nullable=False)
    entity_id:      Mapped[str]       = mapped_column(String(100), nullable=False)
    status:         Mapped[str]       = mapped_column(String(20), default="active", nullable=False)
    message_count:  Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    participants:   Mapped[list]      = mapped_column(JSONB, default=list, nullable=False)
    last_message_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True), nullable=True)
    last_message_preview: Mapped[str|None]=mapped_column(String(200), nullable=True)
    meta:           Mapped[dict]      = mapped_column(JSONB, default=dict, nullable=False)


class Message(ServiceOSBase):
    """Permanent message record. Soft-delete only.
    PROVEN: uq_msg_idem prevents duplicate sends from mobile retry."""
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_msg_idem"),
        Index("ix_msg_conversation", "conversation_id"),
        Index("ix_msg_sender",       "sender_id"),
        Index("ix_msg_created",      "created_at"),
    )
    conversation_id:Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    sender_id:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    sender_role:    Mapped[str]            = mapped_column(String(20), nullable=False)
    message_type:   Mapped[str]            = mapped_column(String(20), default="text", nullable=False)
    content:        Mapped[str]            = mapped_column(Text, nullable=False)
    media_id:       Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    read_by:        Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
    is_deleted:     Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    deleted_at:     Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    edited_at:      Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key:Mapped[str|None]       = mapped_column(String(255), nullable=True, unique=True)
    meta:           Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
