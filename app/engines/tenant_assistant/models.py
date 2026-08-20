"""Tenant AI Assistant ORM models (migration 293).

Deliberately separate from ai_conversation_* — that engine is the customer
booking assistant with its own lifecycle, drafts and workflow states. Sharing
its tables would have meant a customer-facing feature and a tenant-facing one
mutating the same rows.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, Index, Integer, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TenantAssistantConfig(Base):
    """Admin-owned configuration. One 'global' row; optional per-vertical or
    per-tenant overrides resolved most-specific-first."""
    __tablename__ = "tenant_assistant_configs"
    __table_args__ = (
        UniqueConstraint("scope", "scope_id", name="uq_ta_config_global"),
        Index("ix_ta_configs_scope", "scope", "scope_id"),
    )

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope    = Column(String(20), nullable=False, default="global")   # global|vertical|tenant
    scope_id = Column(UUID(as_uuid=True), nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)

    display_name      = Column(String(80), nullable=False, default="Fuvay AI")
    tagline           = Column(String(160), nullable=True)
    avatar_emoji      = Column(String(16), nullable=False, default="✨")
    greeting          = Column(Text, nullable=True)
    input_placeholder = Column(String(160), nullable=False, default="Ask about your business…")
    disabled_message  = Column(Text, nullable=True)

    llm_enabled         = Column(Boolean, nullable=False, default=True)
    model               = Column(String(60), nullable=False, default="deepseek-chat")
    temperature         = Column(Numeric(3, 2), nullable=False, default=Decimal("0.20"))
    max_tokens          = Column(Integer, nullable=False, default=700)
    max_tool_iterations = Column(Integer, nullable=False, default=4)
    system_prompt       = Column(Text, nullable=False)

    retrieval_top_k       = Column(Integer, nullable=False, default=5)
    retrieval_min_score   = Column(Numeric(4, 3), nullable=False, default=Decimal("0.180"))
    require_citation      = Column(Boolean, nullable=False, default=True)
    allowed_product_areas = Column(JSONB, nullable=True)
    allowed_tools         = Column(JSONB, nullable=False, default=list)

    out_of_scope_message = Column(Text, nullable=False)
    no_answer_message    = Column(Text, nullable=False)

    show_categories      = Column(Boolean, nullable=False, default=True)
    show_most_asked      = Column(Boolean, nullable=False, default=True)
    show_live_state      = Column(Boolean, nullable=False, default=True)
    show_recent_requests = Column(Boolean, nullable=False, default=True)
    show_page_context    = Column(Boolean, nullable=False, default=True)
    show_announcements   = Column(Boolean, nullable=False, default=True)
    max_options_total     = Column(Integer, nullable=False, default=24)
    max_options_per_group = Column(Integer, nullable=False, default=6)

    escalation_enabled             = Column(Boolean, nullable=False, default=True)
    auto_escalate_after_unresolved = Column(Integer, nullable=False, default=2)
    escalation_category            = Column(String(60), nullable=False, default="other")
    escalation_impact              = Column(String(40), nullable=False, default="question")
    escalation_include_transcript  = Column(Boolean, nullable=False, default=True)
    # RESERVED — currently has no effect and is deliberately not surfaced in the
    # admin console. Ticket notifications are owned by the support engine's
    # event registry (support.request.*), which routes in_app + email for every
    # ticket regardless of how it was raised. Honouring a per-assistant override
    # means threading a suppression flag through support.create_ticket; until
    # that exists, this column must not be presented as a working switch.
    email_on_escalation            = Column(Boolean, nullable=False, default=True)

    rate_limit_per_hour  = Column(Integer, nullable=False, default=40)
    session_idle_minutes = Column(Integer, nullable=False, default=120)
    allowed_roles        = Column(JSONB, nullable=True)

    updated_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "scope": self.scope,
            "scope_id": str(self.scope_id) if self.scope_id else None,
            "is_enabled": self.is_enabled,
            "display_name": self.display_name, "tagline": self.tagline,
            "avatar_emoji": self.avatar_emoji, "greeting": self.greeting,
            "input_placeholder": self.input_placeholder,
            "disabled_message": self.disabled_message,
            "llm_enabled": self.llm_enabled, "model": self.model,
            "temperature": float(self.temperature), "max_tokens": self.max_tokens,
            "max_tool_iterations": self.max_tool_iterations,
            "system_prompt": self.system_prompt,
            "retrieval_top_k": self.retrieval_top_k,
            "retrieval_min_score": float(self.retrieval_min_score),
            "require_citation": self.require_citation,
            "allowed_product_areas": self.allowed_product_areas,
            "allowed_tools": self.allowed_tools or [],
            "out_of_scope_message": self.out_of_scope_message,
            "no_answer_message": self.no_answer_message,
            "show_categories": self.show_categories,
            "show_most_asked": self.show_most_asked,
            "show_live_state": self.show_live_state,
            "show_recent_requests": self.show_recent_requests,
            "show_page_context": self.show_page_context,
            "show_announcements": self.show_announcements,
            "max_options_total": self.max_options_total,
            "max_options_per_group": self.max_options_per_group,
            "escalation_enabled": self.escalation_enabled,
            "auto_escalate_after_unresolved": self.auto_escalate_after_unresolved,
            "escalation_category": self.escalation_category,
            "escalation_impact": self.escalation_impact,
            "escalation_include_transcript": self.escalation_include_transcript,
            "email_on_escalation": self.email_on_escalation,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "session_idle_minutes": self.session_idle_minutes,
            "allowed_roles": self.allowed_roles,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TenantAssistantOption(Base):
    """An admin-authored entry in the assistant's opening menu."""
    __tablename__ = "tenant_assistant_options"
    __table_args__ = (
        Index("ix_ta_options_group", "group_key", "display_order"),
        Index("ix_ta_options_enabled", "is_enabled"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(UUID(as_uuid=True), nullable=True)
    group_key = Column(String(60), nullable=False)
    label       = Column(String(160), nullable=False)
    description = Column(String(300), nullable=True)
    icon        = Column(String(60), nullable=True)
    action_type   = Column(String(20), nullable=False)
    action_target = Column(Text, nullable=True)
    role_keys     = Column(JSONB, nullable=True)
    vertical_keys = Column(JSONB, nullable=True)
    page_prefixes = Column(JSONB, nullable=True)
    display_order = Column(Integer, nullable=False, default=100)
    is_enabled    = Column(Boolean, nullable=False, default=True)
    is_featured   = Column(Boolean, nullable=False, default=False)
    click_count   = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "group_key": self.group_key, "label": self.label,
            "description": self.description, "icon": self.icon,
            "action_type": self.action_type, "action_target": self.action_target,
            "role_keys": self.role_keys, "vertical_keys": self.vertical_keys,
            "page_prefixes": self.page_prefixes,
            "display_order": self.display_order, "is_enabled": self.is_enabled,
            "is_featured": self.is_featured, "click_count": self.click_count,
        }


class TenantAssistantSession(Base):
    __tablename__ = "tenant_assistant_sessions"
    __table_args__ = (
        Index("ix_ta_sessions_tenant", "tenant_id"),
        Index("ix_ta_sessions_user_active", "user_id", "status", "last_activity_at"),
    )

    id        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    user_id   = Column(UUID(as_uuid=True), nullable=False)
    user_role = Column(String(60), nullable=True)
    status    = Column(String(20), nullable=False, default="active")
    turn_count        = Column(Integer, nullable=False, default=0)
    unresolved_streak = Column(Integer, nullable=False, default=0)
    escalated_ticket_id = Column(UUID(as_uuid=True), nullable=True)
    opened_from_path    = Column(String(300), nullable=True)
    context_data        = Column(JSONB, nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    created_at       = Column(DateTime(timezone=True), nullable=False, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "status": self.status,
            "turn_count": self.turn_count,
            "unresolved_streak": self.unresolved_streak,
            "escalated_ticket_id": (str(self.escalated_ticket_id)
                                    if self.escalated_ticket_id else None),
            "last_activity_at": (self.last_activity_at.isoformat()
                                 if self.last_activity_at else None),
        }


class TenantAssistantMessage(Base):
    __tablename__ = "tenant_assistant_messages"
    __table_args__ = (
        Index("ix_ta_messages_session", "session_id", "created_at"),
        Index("ix_ta_messages_resolution", "resolution"),
    )

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id  = Column(UUID(as_uuid=True), nullable=False)
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    resolution = Column(String(30), nullable=True)
    citations  = Column(JSONB, nullable=True)
    tools_used = Column(JSONB, nullable=True)
    retrieval_score = Column(Numeric(5, 4), nullable=True)
    used_llm   = Column(Boolean, nullable=False, default=False)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "role": self.role, "content": self.content,
            "resolution": self.resolution, "citations": self.citations or [],
            "tools_used": self.tools_used or [],
            "used_llm": self.used_llm,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TenantAssistantFeedback(Base):
    __tablename__ = "tenant_assistant_feedback"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_ta_feedback_once"),
    )

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), nullable=False)
    tenant_id  = Column(UUID(as_uuid=True), nullable=False)
    user_id    = Column(UUID(as_uuid=True), nullable=False)
    is_helpful = Column(Boolean, nullable=False)
    note       = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
