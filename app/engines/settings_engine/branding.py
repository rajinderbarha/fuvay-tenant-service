"""Validated, public-safe platform brand identity configuration.

The configuration lives in ``platform_settings`` so it inherits the existing
audit, version-history and rollback controls.  This module deliberately keeps
the public payload free of storage IDs or administrator information.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.settings_engine.models import PlatformSetting


PLATFORM_BRANDING_KEY = "platform_branding"

DEFAULT_PLATFORM_BRANDING: dict[str, Any] = {
    "brand_name": "Fuvay",
    "short_name": "Fuvay",
    "tagline": "Far Away Is Fare Way",
    "logo_light_url": None,
    "logo_dark_url": None,
    "brand_mark_url": None,
    "favicon_url": None,
    "apple_touch_icon_url": None,
    "email_logo_url": None,
    "document_logo_url": None,
    "social_share_image_url": None,
    "primary_color": "#0F6B60",
    "accent_color": "#2F9E8F",
}

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def unwrap_setting_value(value: Any) -> Any:
    """Support both current ``{"v": value}`` and legacy raw JSONB rows."""
    if isinstance(value, dict) and set(value) == {"v"}:
        return value["v"]
    return value


class PlatformBranding(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    brand_name: str = Field(default="Fuvay", min_length=2, max_length=80)
    short_name: str = Field(default="Fuvay", min_length=2, max_length=30)
    tagline: str = Field(default="Far Away Is Fare Way", max_length=140)
    logo_light_url: str | None = None
    logo_dark_url: str | None = None
    brand_mark_url: str | None = None
    favicon_url: str | None = None
    apple_touch_icon_url: str | None = None
    email_logo_url: str | None = None
    document_logo_url: str | None = None
    social_share_image_url: str | None = None
    primary_color: str = "#0F6B60"
    accent_color: str = "#2F9E8F"

    @field_validator(
        "logo_light_url", "logo_dark_url", "brand_mark_url", "favicon_url",
        "apple_touch_icon_url", "email_logo_url", "document_logo_url",
        "social_share_image_url",
    )
    @classmethod
    def validate_asset_url(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return None
        # Root-relative URLs preserve the bundled fallback assets. Uploaded
        # production artwork must be HTTPS so login pages never load mixed
        # content and external clients can resolve it.
        if value.startswith("/") and not value.startswith("//"):
            return value
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (
            host == "cloudinary.com" or host.endswith(".cloudinary.com")
        ):
            raise ValueError("Uploaded brand assets must use a secure Cloudinary URL.")
        return value

    @field_validator("primary_color", "accent_color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not _HEX_COLOR.fullmatch(value):
            raise ValueError("Brand colours must use six-digit hex format, for example #0F6B60.")
        return value.upper()

    @model_validator(mode="after")
    def validate_primary_contrast(self):
        def channel(component: int) -> float:
            value = component / 255
            return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        raw = self.primary_color.lstrip("#")
        red, green, blue = (int(raw[index:index + 2], 16) for index in (0, 2, 4))
        luminance = 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)
        white_contrast = 1.05 / (luminance + 0.05)
        if white_contrast < 4.5:
            raise ValueError("Primary colour must provide at least 4.5:1 contrast against white text.")
        return self


class PlatformBrandingUpdate(PlatformBranding):
    change_reason: str = Field(min_length=5, max_length=500)
    expected_updated_at: str | None = None


def normalized_branding(value: Any) -> PlatformBranding:
    raw = unwrap_setting_value(value)
    if not isinstance(raw, dict):
        return PlatformBranding(**DEFAULT_PLATFORM_BRANDING)
    merged = {**DEFAULT_PLATFORM_BRANDING, **raw}
    try:
        return PlatformBranding.model_validate(merged)
    except ValueError:
        # A malformed legacy row must never break public/login surfaces.
        return PlatformBranding(**DEFAULT_PLATFORM_BRANDING)


async def read_platform_branding(
    db: AsyncSession, *, active_only: bool = True,
) -> tuple[PlatformBranding, PlatformSetting | None]:
    query = select(PlatformSetting).where(PlatformSetting.key == PLATFORM_BRANDING_KEY)
    if active_only:
        query = query.where(PlatformSetting.status == "active")
    row = (await db.execute(query)).scalar_one_or_none()
    return normalized_branding(row.value if row else None), row


def public_branding_payload(branding: PlatformBranding, row: PlatformSetting | None) -> dict[str, Any]:
    return {
        **branding.model_dump(),
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }
