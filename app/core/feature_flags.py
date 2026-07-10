"""Thin read helper over the real `feature_flags` table (settings_engine) for
the Home Services automatic price-options flags. Uses the existing feature
flag system rather than inventing a parallel config mechanism — see
app/engines/settings_engine/models.py::FeatureFlag.

Defaults (used when a flag row hasn't been seeded yet) match the ticket's
final business decision: manual bargain rule setup is off, automatic
Low/Mid/High and provider-first matching are on.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MANUAL_BARGAIN_RULES_ENABLED = "manual_bargain_rules_enabled"
AUTO_PRICE_OPTIONS_ENABLED = "auto_price_options_enabled"
PROVIDER_FIRST_MATCHING_ENABLED = "provider_first_matching_enabled"

DEFAULTS = {
    MANUAL_BARGAIN_RULES_ENABLED: False,
    AUTO_PRICE_OPTIONS_ENABLED: True,
    PROVIDER_FIRST_MATCHING_ENABLED: True,
}


async def _flag_enabled(db: AsyncSession, flag_key: str) -> bool:
    from app.engines.settings_engine.models import FeatureFlag
    row = await db.scalar(select(FeatureFlag).where(FeatureFlag.flag_key == flag_key))
    if row is None:
        return DEFAULTS[flag_key]
    return row.status == "enabled"


async def get_home_services_pricing_flags(db: AsyncSession) -> dict:
    return {
        MANUAL_BARGAIN_RULES_ENABLED: await _flag_enabled(db, MANUAL_BARGAIN_RULES_ENABLED),
        AUTO_PRICE_OPTIONS_ENABLED: await _flag_enabled(db, AUTO_PRICE_OPTIONS_ENABLED),
        PROVIDER_FIRST_MATCHING_ENABLED: await _flag_enabled(db, PROVIDER_FIRST_MATCHING_ENABLED),
        "home_services_only": True,
    }
