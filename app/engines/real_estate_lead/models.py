"""Sprint 18 — Real Estate Lead Flow models."""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase, utcnow


class RealEstateLeadDraft(ServiceOSBase):
    __tablename__ = "real_estate_lead_drafts"
    __table_args__ = (
        Index("ix_reld_customer",   "customer_id"),
        Index("ix_reld_status",     "status"),
        Index("ix_reld_intent",     "lead_intent"),
        Index("ix_reld_city",       "city"),
        Index("ix_reld_ai_session", "ai_session_id"),
        Index("ix_reld_category",   "category_id"),
    )

    customer_id:              Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    guest_session_id:         Mapped[str | None]       = mapped_column(String(120), nullable=True)
    ai_session_id:            Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    offering_id:              Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    selected_tenant_id:       Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    selected_agent_id:        Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status:                   Mapped[str]              = mapped_column(String(40), nullable=False, default="draft")
    lead_intent:              Mapped[str | None]       = mapped_column(String(40), nullable=True)
    property_type:            Mapped[str | None]       = mapped_column(String(40), nullable=True)
    city:                     Mapped[str | None]       = mapped_column(String(100), nullable=True)
    locality:                 Mapped[str | None]       = mapped_column(String(150), nullable=True)
    zipcode:                  Mapped[str | None]       = mapped_column(String(20), nullable=True)
    budget_min:               Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    budget_max:               Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    rent_min:                 Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    rent_max:                 Mapped[Decimal | None]   = mapped_column(Numeric(14, 2), nullable=True)
    bedrooms:                 Mapped[int | None]       = mapped_column(Integer, nullable=True)
    bathrooms:                Mapped[int | None]       = mapped_column(Integer, nullable=True)
    area_sqft_min:            Mapped[int | None]       = mapped_column(Integer, nullable=True)
    area_sqft_max:            Mapped[int | None]       = mapped_column(Integer, nullable=True)
    furnishing:               Mapped[str | None]       = mapped_column(String(40), nullable=True)
    possession_preference:    Mapped[str | None]       = mapped_column(String(40), nullable=True)
    customer_name:            Mapped[str | None]       = mapped_column(String(200), nullable=True)
    customer_phone:           Mapped[str | None]       = mapped_column(String(30), nullable=True)
    customer_email:           Mapped[str | None]       = mapped_column(String(255), nullable=True)
    preferred_contact_time:   Mapped[str | None]       = mapped_column(String(100), nullable=True)
    notes:                    Mapped[str | None]       = mapped_column(Text, nullable=True)
    requirement_snapshot:     Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    provider_options:         Mapped[list | None]      = mapped_column(JSONB, nullable=True)
    selected_provider_snapshot: Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    lead_score_snapshot:      Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    lead_summary:             Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    fallback_payload:         Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    failure_code:             Mapped[str | None]       = mapped_column(String(100), nullable=True)
    failure_message:          Mapped[str | None]       = mapped_column(Text, nullable=True)
    expires_at:               Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":                       str(self.id),
            "customer_id":              str(self.customer_id) if self.customer_id else None,
            "ai_session_id":            str(self.ai_session_id) if self.ai_session_id else None,
            "category_id":              str(self.category_id),
            "offering_id":              str(self.offering_id),
            "selected_tenant_id":       str(self.selected_tenant_id) if self.selected_tenant_id else None,
            "status":                   self.status,
            "lead_intent":              self.lead_intent,
            "property_type":            self.property_type,
            "city":                     self.city,
            "locality":                 self.locality,
            "zipcode":                  self.zipcode,
            "budget_min":               float(self.budget_min) if self.budget_min is not None else None,
            "budget_max":               float(self.budget_max) if self.budget_max is not None else None,
            "rent_min":                 float(self.rent_min) if self.rent_min is not None else None,
            "rent_max":                 float(self.rent_max) if self.rent_max is not None else None,
            "bedrooms":                 self.bedrooms,
            "bathrooms":                self.bathrooms,
            "area_sqft_min":            self.area_sqft_min,
            "area_sqft_max":            self.area_sqft_max,
            "furnishing":               self.furnishing,
            "possession_preference":    self.possession_preference,
            "customer_name":            self.customer_name,
            "customer_phone":           self.customer_phone,
            "customer_email":           self.customer_email,
            "preferred_contact_time":   self.preferred_contact_time,
            "notes":                    self.notes,
            "requirement_snapshot":     self.requirement_snapshot,
            "provider_options":         self.provider_options,
            "selected_provider_snapshot": self.selected_provider_snapshot,
            "lead_score_snapshot":      self.lead_score_snapshot,
            "lead_summary":             self.lead_summary,
            "fallback_payload":         self.fallback_payload,
            "failure_code":             self.failure_code,
            "failure_message":          self.failure_message,
            "expires_at":               self.expires_at.isoformat() if self.expires_at else None,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if self.updated_at else None,
        }


class RealEstateLeadDraftEvent(ServiceOSBase):
    __tablename__ = "real_estate_lead_draft_events"
    __table_args__ = (
        Index("ix_relde_draft", "draft_id"),
        Index("ix_relde_event", "event_type"),
    )

    draft_id:   Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str]        = mapped_column(String(30), nullable=False)
    event_type: Mapped[str]        = mapped_column(String(60), nullable=False)
    old_value:  Mapped[dict | None]= mapped_column(JSONB, nullable=True)
    new_value:  Mapped[dict | None]= mapped_column(JSONB, nullable=True)
    message:    Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":         str(self.id),
            "draft_id":   str(self.draft_id),
            "actor_type": self.actor_type,
            "event_type": self.event_type,
            "old_value":  self.old_value,
            "new_value":  self.new_value,
            "message":    self.message,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RealEstateLeadRoutingRule(ServiceOSBase):
    __tablename__ = "real_estate_lead_routing_rules"
    __table_args__ = (
        UniqueConstraint("category_id", "rule_key", name="uq_relrr_cat_key"),
        Index("ix_relrr_category", "category_id"),
        Index("ix_relrr_active",   "is_active"),
    )

    category_id:               Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_key:                  Mapped[str]       = mapped_column(String(100), nullable=False)
    rule_name:                 Mapped[str]       = mapped_column(String(200), nullable=False)
    lead_intent:               Mapped[str | None]= mapped_column(String(40), nullable=True)
    match_scope:               Mapped[str]       = mapped_column(String(40), nullable=False)
    priority:                  Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    require_agent_available:   Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    require_provider_bookable: Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)
    require_subscription_active: Mapped[bool]   = mapped_column(Boolean, default=True, nullable=False)
    require_lead_credit:       Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    max_providers:             Mapped[int]       = mapped_column(Integer, default=5, nullable=False)
    is_active:                 Mapped[bool]      = mapped_column(Boolean, default=True, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":                       str(self.id),
            "category_id":              str(self.category_id),
            "rule_key":                 self.rule_key,
            "rule_name":                self.rule_name,
            "lead_intent":              self.lead_intent,
            "match_scope":              self.match_scope,
            "priority":                 self.priority,
            "require_agent_available":  self.require_agent_available,
            "require_provider_bookable":self.require_provider_bookable,
            "require_subscription_active": self.require_subscription_active,
            "require_lead_credit":      self.require_lead_credit,
            "max_providers":            self.max_providers,
            "is_active":                self.is_active,
            "created_at":               self.created_at.isoformat() if self.created_at else None,
            "updated_at":               self.updated_at.isoformat() if self.updated_at else None,
        }


class RealEstateLeadScore(ServiceOSBase):
    __tablename__ = "real_estate_lead_scores"
    __table_args__ = (
        Index("ix_rels_draft", "draft_id"),
    )

    draft_id:      Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    score:         Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    score_label:   Mapped[str]        = mapped_column(String(20), nullable=False)
    score_factors: Mapped[dict | None]= mapped_column(JSONB, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":            str(self.id),
            "draft_id":      str(self.draft_id),
            "score":         self.score,
            "score_label":   self.score_label,
            "score_factors": self.score_factors,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
        }
