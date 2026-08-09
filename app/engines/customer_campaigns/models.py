"""LEVEL-5 REMEDIATION (2026-08-01, Phase 11) — Customer Campaign/Banner backend.

Prior audit (G9) confirmed no backend-controlled ZIP-targeted campaign/banner
model existed anywhere — `marketing`/`marketing_command_center` engines are
admin-side AI content-generation/publishing tools with no customer-facing
read surface or ZIP-targeting concept. This is the foundational model only
— no admin or customer frontend is built in this remediation.
"""
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class CustomerCampaign(ServiceOSBase):
    """A backend-controlled, ZIP/category-targetable Home-screen banner."""
    __tablename__ = "customer_campaigns"
    __table_args__ = (
        Index("ix_cc_active_window", "is_enabled", "starts_at", "ends_at"),
        Index("ix_cc_priority", "priority"),
    )

    internal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    eyebrow: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)

    artwork_url_light: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    artwork_url_dark: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    cta_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # A restricted, allowlisted deep-link target — never an arbitrary URL.
    # Validated against ALLOWED_DEEPLINK_PREFIXES in service.py before save.
    cta_deeplink: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Presentation, admin-chosen (migration 236). Both are fixed vocabularies --
    # see constants.CAMPAIGN_STYLES / CAMPAIGN_PLACEMENTS -- because the app
    # ships one renderer per style and one slot per placement; free text here
    # would let admin save a banner that renders as nothing.
    display_style: Mapped[str] = mapped_column(String(30), nullable=False, default="hero")
    placement: Mapped[str] = mapped_column(String(30), nullable=False, default="campaign_top")
    # Festival treatment only: the accent the card is painted in, and the small
    # badge above the title ("Diwali offer"). Null renders the ordinary theme.
    accent_color: Mapped[str | None] = mapped_column(String(9), nullable=True)
    badge_text: Mapped[str | None] = mapped_column(String(40), nullable=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Targeting — all optional; empty/null means "no restriction on this axis".
    eligible_vertical_keys: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    eligible_category_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_zipcodes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_zones: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    target_cities: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_customer_dict(self) -> dict:
        """Customer-safe projection — no internal_name, no created_by/updated_by."""
        return {
            "campaign_id": str(self.id),
            "eyebrow": self.eyebrow,
            "title": self.title,
            "description": self.description,
            "artwork_url_light": self.artwork_url_light,
            "artwork_url_dark": self.artwork_url_dark,
            "cta_label": self.cta_label,
            "cta_deeplink": self.cta_deeplink,
            "priority": self.priority,
            "display_style": self.display_style,
            "placement": self.placement,
            "accent_color": self.accent_color,
            "badge_text": self.badge_text,
            # The window is customer-visible for the festival style, which says
            # "ends 5 Nov" -- a real end date, never a manufactured countdown.
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
        }

    def to_admin_dict(self) -> dict:
        return {
            "campaign_id": str(self.id),
            "internal_name": self.internal_name,
            "eyebrow": self.eyebrow,
            "title": self.title,
            "description": self.description,
            "artwork_url_light": self.artwork_url_light,
            "artwork_url_dark": self.artwork_url_dark,
            "cta_label": self.cta_label,
            "cta_deeplink": self.cta_deeplink,
            "display_style": self.display_style,
            "placement": self.placement,
            "accent_color": self.accent_color,
            "badge_text": self.badge_text,
            "is_enabled": self.is_enabled,
            "priority": self.priority,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "eligible_vertical_keys": self.eligible_vertical_keys or [],
            "eligible_category_ids": self.eligible_category_ids or [],
            "target_zipcodes": self.target_zipcodes or [],
            "target_zones": self.target_zones or [],
            "target_cities": self.target_cities or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
