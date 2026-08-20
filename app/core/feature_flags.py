"""Feature-flag helpers used by runtime engines and route registration.

The Home Services pricing flags are read from the existing settings-engine
table. API-key routes use a deployment setting because a disabled API surface
must be removed before routers are mounted and before a database session exists.
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

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


def hide_disabled_api_key_routes(router: APIRouter) -> None:
    """Remove API-key routes from runtime routing and generated OpenAPI."""
    if get_settings().API_KEYS_ENABLED:
        return
    router.routes[:] = [
        route for route in router.routes
        if "/api-keys" not in getattr(route, "path", "")
    ]
