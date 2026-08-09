"""Admin control over which Home sections appear, and in what order.

The app's Home layout was fixed in code, so re-ordering it or hiding a section
needed an app release. These rows are the ordering the customer payload reports;
the app renders the enabled ones in the given order.

Deliberately a CLOSED vocabulary (see constants.HOME_SECTION_KEYS, seeded by
migration 236): a key the app has no renderer for is not a section, it is a row
that does nothing. Adding one is a code + migration change, on purpose.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class HomeSectionSetting(ServiceOSBase):
    __tablename__ = "home_section_settings"
    __table_args__ = (
        Index("ix_hss_order", "display_order"),
    )

    section_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    # Null means the app uses the wording it ships with. An override renames a
    # section; it can never invent one.
    title_override: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "section_key": self.section_key,
            "is_enabled": self.is_enabled,
            "display_order": self.display_order,
            "title_override": self.title_override,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_customer_dict(self) -> dict:
        """What the app needs to lay the screen out: which section, where, and
        under what heading. Disabled sections are filtered out before this."""
        return {
            "key": self.section_key,
            "order": self.display_order,
            "title": self.title_override,
        }
