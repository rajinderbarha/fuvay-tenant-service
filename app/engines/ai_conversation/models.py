"""Sprint 15 — AI Conversation Engine SQLAlchemy models."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class AIConversationSession(Base):
    __tablename__ = "ai_conversation_sessions"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_key      = Column(String(128), nullable=False, unique=True)
    customer_id      = Column(UUID(as_uuid=True), nullable=True, index=True)
    category_id      = Column(UUID(as_uuid=True), nullable=True)
    current_intent   = Column(String(100), nullable=True)
    workflow_status  = Column(String(50), nullable=False, server_default=text("'active'"))
    collected_fields = Column(JSONB, nullable=True)
    context_data     = Column(JSONB, nullable=True)
    turn_count       = Column(Integer, nullable=False, server_default=text("0"))
    last_activity_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    completed_at     = Column(DateTime(timezone=True), nullable=True)
    is_active        = Column(Boolean, nullable=False, server_default=text("true"))
    created_at       = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    language         = Column(String(10), nullable=False, server_default=text("'en'"))
    updated_at       = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    messages     = relationship("AIConversationMessage", back_populates="session",
                                cascade="all, delete-orphan", lazy="dynamic")
    workflow_states = relationship("AIWorkflowState", back_populates="session",
                                  cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":               str(self.id),
            "session_key":      self.session_key,
            "customer_id":      str(self.customer_id) if self.customer_id else None,
            "category_id":      str(self.category_id) if self.category_id else None,
            "current_intent":   self.current_intent,
            "workflow_status":  self.workflow_status,
            "collected_fields": self.collected_fields or {},
            "context_data":     self.context_data or {},
            "turn_count":       self.turn_count,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "completed_at":     self.completed_at.isoformat() if self.completed_at else None,
            "is_active":        self.is_active,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "updated_at":       self.updated_at.isoformat() if self.updated_at else None,
            # Real column (server_default 'en'), was never serialized here --
            # the customer app's AssistantSessionResponseDto requires
            # `language` as a non-optional field, so every session response
            # failed that contract check.
            "language":         self.language,
        }


class AIConversationMessage(Base):
    __tablename__ = "ai_conversation_messages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id      = Column(UUID(as_uuid=True), ForeignKey("ai_conversation_sessions.id",
                             ondelete="CASCADE"), nullable=False, index=True)
    role            = Column(String(20), nullable=False)
    content         = Column(Text, nullable=False)
    intent_at_time  = Column(String(100), nullable=True)
    tool_calls_made = Column(JSONB, nullable=True)
    latency_ms      = Column(Integer, nullable=True)
    token_count     = Column(Integer, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    session = relationship("AIConversationSession", back_populates="messages")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":              str(self.id),
            "session_id":      str(self.session_id),
            "role":            self.role,
            "content":         self.content,
            "intent_at_time":  self.intent_at_time,
            "tool_calls_made": self.tool_calls_made or [],
            "latency_ms":      self.latency_ms,
            "token_count":     self.token_count,
            "created_at":      self.created_at.isoformat() if self.created_at else None,
        }


class AIWorkflowState(Base):
    __tablename__ = "ai_workflow_states"
    __table_args__ = (
        UniqueConstraint("session_id", "workflow_name", name="uq_aws_session_workflow"),
    )

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id        = Column(UUID(as_uuid=True), ForeignKey("ai_conversation_sessions.id",
                               ondelete="CASCADE"), nullable=False, index=True)
    workflow_name     = Column(String(100), nullable=False)
    current_step      = Column(String(100), nullable=True)
    steps_completed   = Column(JSONB, nullable=True)
    steps_pending     = Column(JSONB, nullable=True)
    extracted_data    = Column(JSONB, nullable=True)
    validation_errors = Column(JSONB, nullable=True)
    is_complete       = Column(Boolean, nullable=False, server_default=text("false"))
    created_at        = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    session = relationship("AIConversationSession", back_populates="workflow_states")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":                str(self.id),
            "session_id":        str(self.session_id),
            "workflow_name":     self.workflow_name,
            "current_step":      self.current_step,
            "steps_completed":   self.steps_completed or [],
            "steps_pending":     self.steps_pending or [],
            "extracted_data":    self.extracted_data or {},
            "validation_errors": self.validation_errors or [],
            "is_complete":       self.is_complete,
            "created_at":        self.created_at.isoformat() if self.created_at else None,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
        }


class AIPromptTemplate(Base):
    __tablename__ = "ai_prompt_templates"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_key     = Column(String(100), nullable=False, unique=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text, nullable=True)
    category         = Column(String(50), nullable=False, server_default=text("'system'"))
    template_content = Column(Text, nullable=False)
    variables        = Column(JSONB, nullable=True)
    version          = Column(Integer, nullable=False, server_default=text("1"))
    is_active        = Column(Boolean, nullable=False, server_default=text("true"))
    created_at       = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    updated_at       = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":               str(self.id),
            "template_key":     self.template_key,
            "name":             self.name,
            "description":      self.description,
            "category":         self.category,
            "template_content": self.template_content,
            "variables":        self.variables or [],
            "version":          self.version,
            "is_active":        self.is_active,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
            "updated_at":       self.updated_at.isoformat() if self.updated_at else None,
        }


class AILLMCallLog(Base):
    __tablename__ = "ai_llm_call_logs"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id           = Column(UUID(as_uuid=True), ForeignKey("ai_conversation_sessions.id",
                                  ondelete="SET NULL"), nullable=True, index=True)
    call_type            = Column(String(50), nullable=False, server_default=text("'chat'"))
    model_used           = Column(String(100), nullable=False)
    prompt_tokens        = Column(Integer, nullable=True)
    completion_tokens    = Column(Integer, nullable=True)
    latency_ms           = Column(Integer, nullable=True)
    had_tool_calls       = Column(Boolean, nullable=False, server_default=text("false"))
    tool_names           = Column(JSONB, nullable=True)
    response_status      = Column(String(30), nullable=False, server_default=text("'success'"))
    error_message        = Column(Text, nullable=True)
    request_payload_size = Column(Integer, nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    tool_calls = relationship("AIToolCallLog", back_populates="llm_call",
                              cascade="all, delete-orphan", lazy="dynamic")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":                   str(self.id),
            "session_id":           str(self.session_id) if self.session_id else None,
            "call_type":            self.call_type,
            "model_used":           self.model_used,
            "prompt_tokens":        self.prompt_tokens,
            "completion_tokens":    self.completion_tokens,
            "latency_ms":           self.latency_ms,
            "had_tool_calls":       self.had_tool_calls,
            "tool_names":           self.tool_names or [],
            "response_status":      self.response_status,
            "error_message":        self.error_message,
            "request_payload_size": self.request_payload_size,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
        }


class AIToolCallLog(Base):
    __tablename__ = "ai_tool_call_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    llm_call_id  = Column(UUID(as_uuid=True), ForeignKey("ai_llm_call_logs.id",
                           ondelete="SET NULL"), nullable=True, index=True)
    session_id   = Column(UUID(as_uuid=True), ForeignKey("ai_conversation_sessions.id",
                           ondelete="SET NULL"), nullable=True, index=True)
    tool_name    = Column(String(100), nullable=False, index=True)
    input_params = Column(JSONB, nullable=True)
    output_data  = Column(JSONB, nullable=True)
    success      = Column(Boolean, nullable=False, server_default=text("true"))
    latency_ms   = Column(Integer, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    llm_call = relationship("AILLMCallLog", back_populates="tool_calls")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":           str(self.id),
            "llm_call_id":  str(self.llm_call_id) if self.llm_call_id else None,
            "session_id":   str(self.session_id) if self.session_id else None,
            "tool_name":    self.tool_name,
            "input_params": self.input_params or {},
            "output_data":  self.output_data or {},
            "success":      self.success,
            "latency_ms":   self.latency_ms,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
        }


class AIConversationAuditLog(Base):
    __tablename__ = "ai_conversation_audit_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id  = Column(UUID(as_uuid=True), ForeignKey("ai_conversation_sessions.id",
                          ondelete="SET NULL"), nullable=True, index=True)
    event_type  = Column(String(80), nullable=False, index=True)
    event_data  = Column(JSONB, nullable=True)
    severity    = Column(String(20), nullable=False, server_default=text("'info'"))
    customer_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address  = Column(String(50), nullable=True)
    user_agent  = Column(String(500), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":          str(self.id),
            "session_id":  str(self.session_id) if self.session_id else None,
            "event_type":  self.event_type,
            "event_data":  self.event_data or {},
            "severity":    self.severity,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "ip_address":  self.ip_address,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }
