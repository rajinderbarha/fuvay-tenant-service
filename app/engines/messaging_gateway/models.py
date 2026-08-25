"""Messaging Gateway — thread mapping and inbound de-duplication.

Two tables, both deliberately small:

* `messaging_threads` maps a channel identity (a WhatsApp phone number, an
  Instagram-scoped user id) to the customer account and the currently-open
  `AIConversationSession`. Without it every inbound message would start a new
  conversation and the agent would lose the booking draft it is halfway
  through building.

* `messaging_inbound_messages` records each provider message id. Meta retries
  a webhook until it gets a 200, so the SAME message arrives repeatedly on any
  slow response or transient error. Without a uniqueness record, one customer
  message would be replayed into the agent several times — re-running tool
  calls and, in the worst case, creating duplicate booking drafts.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class MessagingThread(ServiceOSBase):
    """One conversation thread with one person on one channel."""

    __tablename__ = "messaging_threads"
    __table_args__ = (
        # One live thread per identity per channel. The channel identity is the
        # account key: on WhatsApp the sender's phone number IS the identity we
        # log them in with, which is why phone-OTP accounts fit this cleanly.
        UniqueConstraint("channel", "channel_user_id", name="uq_msg_thread_channel_user"),
        Index("ix_msg_thread_customer", "customer_id"),
        Index("ix_msg_thread_session", "ai_session_id"),
        Index("ix_msg_thread_last_inbound", "last_inbound_at"),
    )

    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    #: WhatsApp: E.164 phone. Instagram: the page-scoped user id (NOT a phone).
    channel_user_id: Mapped[str] = mapped_column(String(120), nullable=False)
    #: The business number/page the customer messaged, so one deployment can
    #: serve several tenants' numbers later without a schema change.
    channel_business_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)

    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    #: The live agent session. Cleared by /fuvay and /reset so the next message
    #: opens a fresh one.
    ai_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    #: /stop. Honoured for automated sends; a human agent can still reply.
    opted_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: Set by /human — suppresses bot replies until an agent closes the handoff.
    human_handoff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "channel": self.channel,
            "channel_user_id": self.channel_user_id,
            "display_name": self.display_name,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "ai_session_id": str(self.ai_session_id) if self.ai_session_id else None,
            "opted_out": self.opted_out,
            "human_handoff": self.human_handoff,
            "last_inbound_at": self.last_inbound_at.isoformat() if self.last_inbound_at else None,
            "last_outbound_at": self.last_outbound_at.isoformat() if self.last_outbound_at else None,
            "session_count": self.session_count,
        }


class MessagingInboundMessage(ServiceOSBase):
    """One provider message id, processed at most once."""

    __tablename__ = "messaging_inbound_messages"
    __table_args__ = (
        # THE idempotency guard. Meta redelivers until it sees a 200, so this
        # unique constraint is what stops one customer message being replayed
        # into the agent — and its tools — more than once.
        UniqueConstraint("channel", "provider_message_id", name="uq_msg_inbound_provider_id"),
        Index("ix_msg_inbound_thread", "thread_id"),
        Index("ix_msg_inbound_created", "created_at"),
    )

    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(200), nullable=False)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    from_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "channel": self.channel,
            "provider_message_id": self.provider_message_id,
            "thread_id": str(self.thread_id) if self.thread_id else None,
            "from_id": self.from_id,
            "message_type": self.message_type,
            "status": self.status,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
