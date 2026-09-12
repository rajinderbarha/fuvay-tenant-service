"""Explicit identity shortcuts for the temporary Instagram QA deployment.

The SMS-OTP bypass is scoped to Instagram and remains off unless the deployment
sets the dedicated switch. The IP-only compose overlay enables it temporarily;
the normal domain deployment does not. A contact number is still required.
"""
from __future__ import annotations

from app.config import get_settings


def instagram_phone_bypass_enabled(channel: str | None) -> bool:
    settings = get_settings()
    return bool(
        channel == "instagram"
        and getattr(settings, "MESSAGING_DEV_PHONE_BYPASS_ENABLED", False)
    )
