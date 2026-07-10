"""Marketing Automation Command Center — SQLAlchemy models (migration 100).

Platform-pays-AI-cost rule: MarketingAIBudget/MarketingAIBudgetLedger have no
relationship whatsoever to tenant_wallets or customer_service_credits — tenant
usage credits can never be touched by marketing generation cost.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class MarketingPost(ServiceOSBase):
    __tablename__ = "marketing_posts"
    __table_args__ = (
        Index("ix_mpost_status_2", "status"),
    )

    id                   : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_code            : Mapped[str]            = mapped_column(String(60), nullable=False)
    campaign_id          : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title                : Mapped[str]             = mapped_column(Text, nullable=False)
    caption              : Mapped[str|None]       = mapped_column(Text, nullable=True)
    short_caption        : Mapped[str|None]       = mapped_column(Text, nullable=True)
    hashtags_json        : Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    vertical_key         : Mapped[str|None]       = mapped_column(Text, nullable=True)
    category_id          : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    service_id           : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id            : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_locations_json: Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    language             : Mapped[str]             = mapped_column(Text, nullable=False, default="english")
    tone                 : Mapped[str|None]       = mapped_column(Text, nullable=True)
    post_type            : Mapped[str]             = mapped_column(Text, nullable=False, default="image_post")
    goal                 : Mapped[str|None]       = mapped_column(Text, nullable=True)
    cta                  : Mapped[str|None]       = mapped_column(Text, nullable=True)
    channels_json        : Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    status               : Mapped[str]             = mapped_column(Text, nullable=False, default="draft")
    approval_status      : Mapped[str]             = mapped_column(Text, nullable=False, default="not_required")
    approved_by_user_id  : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at          : Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason     : Mapped[str|None]       = mapped_column(Text, nullable=True)
    scheduled_at         : Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    published_at         : Mapped[datetime|None]  = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id   : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at           : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at           : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id), "post_code": self.post_code,
            "campaign_id": str(self.campaign_id) if self.campaign_id else None,
            "title": self.title, "caption": self.caption, "short_caption": self.short_caption,
            "hashtags": self.hashtags_json or [], "vertical_key": self.vertical_key,
            "category_id": str(self.category_id) if self.category_id else None,
            "service_id": str(self.service_id) if self.service_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "target_locations": self.target_locations_json or [],
            "language": self.language, "tone": self.tone, "post_type": self.post_type,
            "goal": self.goal, "cta": self.cta, "channels": self.channels_json or [],
            "status": self.status, "approval_status": self.approval_status,
            "approved_by_user_id": str(self.approved_by_user_id) if self.approved_by_user_id else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketingPostAsset(ServiceOSBase):
    __tablename__ = "marketing_post_assets"

    id             : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id        : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    asset_type     : Mapped[str]             = mapped_column(Text, nullable=False, default="image")
    media_id       : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    url            : Mapped[str|None]       = mapped_column(Text, nullable=True)
    generated_by_ai: Mapped[bool]            = mapped_column(Boolean, nullable=False, default=True)
    ai_model       : Mapped[str|None]       = mapped_column(Text, nullable=True)
    ai_prompt      : Mapped[str|None]       = mapped_column(Text, nullable=True)
    alt_text       : Mapped[str|None]       = mapped_column(Text, nullable=True)
    cost_amount    : Mapped[float|None]     = mapped_column(Numeric(10, 2), nullable=True)
    status         : Mapped[str]             = mapped_column(Text, nullable=False, default="ready")
    created_at     : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id), "post_id": str(self.post_id), "asset_type": self.asset_type,
            "media_id": str(self.media_id) if self.media_id else None, "url": self.url,
            "generated_by_ai": self.generated_by_ai, "ai_model": self.ai_model, "ai_prompt": self.ai_prompt,
            "alt_text": self.alt_text, "cost_amount": float(self.cost_amount) if self.cost_amount is not None else None,
            "status": self.status, "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MarketingAIBudget(ServiceOSBase):
    __tablename__ = "marketing_ai_budget"

    id                          : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope                       : Mapped[str]             = mapped_column(Text, nullable=False, default="platform")
    daily_budget                : Mapped[float]           = mapped_column(Numeric(10, 2), nullable=False, default=500)
    monthly_budget              : Mapped[float]           = mapped_column(Numeric(10, 2), nullable=False, default=10000)
    cost_alert_threshold_pct    : Mapped[int]             = mapped_column(Integer, nullable=False, default=80)
    auto_disable_on_exceed      : Mapped[bool]            = mapped_column(Boolean, nullable=False, default=True)
    require_approval_above_cost : Mapped[float|None]     = mapped_column(Numeric(10, 2), nullable=True)
    updated_by_user_id          : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at                  : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at                  : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id), "scope": self.scope,
            "daily_budget": float(self.daily_budget), "monthly_budget": float(self.monthly_budget),
            "cost_alert_threshold_pct": self.cost_alert_threshold_pct,
            "auto_disable_on_exceed": self.auto_disable_on_exceed,
            "require_approval_above_cost": float(self.require_approval_above_cost) if self.require_approval_above_cost is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketingAIBudgetLedger(ServiceOSBase):
    __tablename__ = "marketing_ai_budget_ledger"

    id                : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_type   : Mapped[str]             = mapped_column(Text, nullable=False)
    model             : Mapped[str|None]       = mapped_column(Text, nullable=True)
    cost_amount       : Mapped[float]           = mapped_column(Numeric(10, 2), nullable=False)
    post_id           : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    campaign_id       : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at        : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id), "generation_type": self.generation_type, "model": self.model,
            "cost_amount": float(self.cost_amount),
            "post_id": str(self.post_id) if self.post_id else None,
            "campaign_id": str(self.campaign_id) if self.campaign_id else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MarketingContentTemplateV2(ServiceOSBase):
    __tablename__ = "marketing_content_templates"

    id               : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name    : Mapped[str]             = mapped_column(Text, nullable=False)
    vertical_key     : Mapped[str|None]       = mapped_column(Text, nullable=True)
    post_type        : Mapped[str]             = mapped_column(Text, nullable=False, default="image_post")
    language         : Mapped[str]             = mapped_column(Text, nullable=False, default="english")
    prompt_template  : Mapped[str|None]       = mapped_column(Text, nullable=True)
    caption_structure: Mapped[str|None]       = mapped_column(Text, nullable=True)
    hashtag_set_json : Mapped[list|None]      = mapped_column(JSONB, nullable=True)
    cta              : Mapped[str|None]       = mapped_column(Text, nullable=True)
    status           : Mapped[str]             = mapped_column(Text, nullable=False, default="active")
    created_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at       : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at       : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id), "template_name": self.template_name, "vertical_key": self.vertical_key,
            "post_type": self.post_type, "language": self.language, "prompt_template": self.prompt_template,
            "caption_structure": self.caption_structure, "hashtag_set": self.hashtag_set_json or [],
            "cta": self.cta, "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MarketingPublishAttempt(ServiceOSBase):
    __tablename__ = "marketing_publish_attempts"

    id               : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id          : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    channel          : Mapped[str]             = mapped_column(Text, nullable=False)
    social_account_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status           : Mapped[str]             = mapped_column(Text, nullable=False, default="pending")
    attempt_number   : Mapped[int]             = mapped_column(Integer, nullable=False, default=1)
    external_post_id : Mapped[str|None]       = mapped_column(Text, nullable=True)
    error_code       : Mapped[str|None]       = mapped_column(Text, nullable=True)
    error_message    : Mapped[str|None]       = mapped_column(Text, nullable=True)
    created_at       : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at       : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id), "post_id": str(self.post_id), "channel": self.channel,
            "social_account_id": str(self.social_account_id) if self.social_account_id else None,
            "status": self.status, "attempt_number": self.attempt_number,
            "external_post_id": self.external_post_id, "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketingAuditLog(ServiceOSBase):
    __tablename__ = "marketing_audit_logs"

    id             : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id  : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action_type    : Mapped[str]             = mapped_column(Text, nullable=False)
    target_type    : Mapped[str]             = mapped_column(Text, nullable=False)
    target_id      : Mapped[str|None]       = mapped_column(Text, nullable=True)
    old_value_json : Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    new_value_json : Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    reason         : Mapped[str|None]       = mapped_column(Text, nullable=True)
    request_id     : Mapped[str|None]       = mapped_column(Text, nullable=True)
    created_at     : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id), "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "action_type": self.action_type, "target_type": self.target_type, "target_id": self.target_id,
            "old_value": self.old_value_json, "new_value": self.new_value_json,
            "reason": self.reason, "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
