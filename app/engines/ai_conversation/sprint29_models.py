"""Sprint 29 — ai_action_logs SQLAlchemy model."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class AIActionLog(ServiceOSBase):
    """Structured log for every backend_action_request the AI produces."""
    __tablename__ = "ai_action_logs"

    id               : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id       : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id      : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action           : Mapped[str]            = mapped_column(String(100), nullable=False)
    intent           : Mapped[str|None]       = mapped_column(String(100), nullable=True)
    flow_type        : Mapped[str|None]       = mapped_column(String(100), nullable=True)
    draft_type       : Mapped[str|None]       = mapped_column(String(100), nullable=True)
    draft_id         : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status           : Mapped[str]            = mapped_column(String(50),  nullable=False, server_default="requested")
    failure_code     : Mapped[str|None]       = mapped_column(String(100), nullable=True)
    failure_message  : Mapped[str|None]       = mapped_column(Text,        nullable=True)
    request_payload  : Mapped[dict|None]      = mapped_column(JSONB,       nullable=True)
    response_payload : Mapped[dict|None]      = mapped_column(JSONB,       nullable=True)
    created_at       : Mapped[datetime]       = mapped_column(DateTime(timezone=True),
                                                              nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":               str(self.id),
            "session_id":       str(self.session_id),
            "customer_id":      str(self.customer_id) if self.customer_id else None,
            "action":           self.action,
            "intent":           self.intent,
            "flow_type":        self.flow_type,
            "draft_type":       self.draft_type,
            "draft_id":         str(self.draft_id) if self.draft_id else None,
            "status":           self.status,
            "failure_code":     self.failure_code,
            "failure_message":  self.failure_message,
            "request_payload":  self.request_payload,
            "response_payload": self.response_payload,
            "created_at":       self.created_at.isoformat() if self.created_at else None,
        }
