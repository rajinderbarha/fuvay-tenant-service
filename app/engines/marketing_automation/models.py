"""Sprint 29 — Marketing Automation SQLAlchemy models (4 tables)."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, Text, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class MarketingCampaign(ServiceOSBase):
    __tablename__ = "marketing_campaigns"
    __table_args__ = (
        UniqueConstraint("campaign_key", name="uq_mcamp_key"),
        Index("ix_mcamp_status",   "status"),
        Index("ix_mcamp_type",     "campaign_type"),
        Index("ix_mcamp_audience", "target_audience"),
    )

    id                 : Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_key       : Mapped[str]             = mapped_column(String(200), nullable=False)
    campaign_name      : Mapped[str]             = mapped_column(String(300), nullable=False)
    campaign_type      : Mapped[str]             = mapped_column(String(100), nullable=False)
    status             : Mapped[str]             = mapped_column(String(50),  nullable=False, server_default="draft")
    target_audience    : Mapped[str]             = mapped_column(String(50),  nullable=False)
    category_id        : Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id          : Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    city               : Mapped[str|None]        = mapped_column(String(100), nullable=True)
    zone_id            : Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    starts_at          : Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at            : Mapped[datetime|None]   = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id : Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    # Command Center additive fields (migration 100)
    goal               : Mapped[str|None]        = mapped_column(Text, nullable=True)
    vertical_key       : Mapped[str|None]        = mapped_column(Text, nullable=True)
    budget_amount      : Mapped[float|None]      = mapped_column(Numeric(10, 2), nullable=True)
    budget_used_amount : Mapped[float]           = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    channels_json      : Mapped[list|None]       = mapped_column(JSONB, nullable=True)
    owner_user_id      : Mapped[uuid.UUID|None]  = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at         : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at         : Mapped[datetime]        = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":                 str(self.id),
            "campaign_key":       self.campaign_key,
            "campaign_name":      self.campaign_name,
            "campaign_type":      self.campaign_type,
            "status":             self.status,
            "target_audience":    self.target_audience,
            "category_id":        str(self.category_id)  if self.category_id  else None,
            "tenant_id":          str(self.tenant_id)    if self.tenant_id    else None,
            "city":               self.city,
            "zone_id":            str(self.zone_id)      if self.zone_id      else None,
            "starts_at":          self.starts_at.isoformat()  if self.starts_at  else None,
            "ends_at":            self.ends_at.isoformat()    if self.ends_at    else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "goal":               self.goal,
            "vertical_key":       self.vertical_key,
            "budget_amount":      float(self.budget_amount) if self.budget_amount is not None else None,
            "budget_used_amount": float(self.budget_used_amount or 0),
            "channels":           self.channels_json or [],
            "owner_user_id":      str(self.owner_user_id) if self.owner_user_id else None,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
            "updated_at":         self.updated_at.isoformat() if self.updated_at else None,
        }


class MarketingCampaignRule(ServiceOSBase):
    __tablename__ = "marketing_campaign_rules"

    id          : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    rule_type   : Mapped[str]       = mapped_column(String(50), nullable=False)
    rule_config : Mapped[dict]      = mapped_column(JSONB, nullable=False, server_default=text("'{}'"))
    is_active   : Mapped[bool]      = mapped_column(Boolean, nullable=False, server_default="true")
    created_at  : Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at  : Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":          str(self.id),
            "campaign_id": str(self.campaign_id),
            "rule_type":   self.rule_type,
            "rule_config": self.rule_config,
            "is_active":   self.is_active,
        }


class MarketingCampaignMessage(ServiceOSBase):
    __tablename__ = "marketing_campaign_messages"

    id           : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id  : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    channel      : Mapped[str]       = mapped_column(String(50),  nullable=False)
    title        : Mapped[str]       = mapped_column(String(300), nullable=False)
    body         : Mapped[str]       = mapped_column(Text,        nullable=False)
    action_label : Mapped[str|None]  = mapped_column(String(100), nullable=True)
    action_url   : Mapped[str|None]  = mapped_column(String(500), nullable=True)
    is_active    : Mapped[bool]      = mapped_column(Boolean, nullable=False, server_default="true")
    created_at   : Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at   : Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":           str(self.id),
            "campaign_id":  str(self.campaign_id),
            "channel":      self.channel,
            "title":        self.title,
            "body":         self.body,
            "action_label": self.action_label,
            "action_url":   self.action_url,
            "is_active":    self.is_active,
        }


class MarketingCampaignEvent(ServiceOSBase):
    __tablename__ = "marketing_campaign_events"

    id                 : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id        : Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    recipient_user_id  : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    tenant_id          : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type         : Mapped[str]            = mapped_column(String(50), nullable=False)
    source_record_type : Mapped[str|None]       = mapped_column(String(100), nullable=True)
    source_record_id   : Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    camp_metadata      : Mapped[dict|None]      = mapped_column(JSONB, nullable=True)
    created_at         : Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":                 str(self.id),
            "campaign_id":        str(self.campaign_id),
            "recipient_user_id":  str(self.recipient_user_id) if self.recipient_user_id else None,
            "tenant_id":          str(self.tenant_id)         if self.tenant_id         else None,
            "event_type":         self.event_type,
            "source_record_type": self.source_record_type,
            "source_record_id":   str(self.source_record_id) if self.source_record_id else None,
            "camp_metadata":      self.camp_metadata,
            "created_at":         self.created_at.isoformat() if self.created_at else None,
        }
