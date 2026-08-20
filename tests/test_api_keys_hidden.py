"""Regression coverage for the intentionally dormant API-key product."""
from app.config import get_settings
from app.core.feature_flags import (
    AUTO_PRICE_OPTIONS_ENABLED,
    MANUAL_BARGAIN_RULES_ENABLED,
    PROVIDER_FIRST_MATCHING_ENABLED,
)
from app.engines.auth.router import router as auth_router
from app.engines.security.admin_router import router as security_admin_router
from app.engines.security.router import router as security_router


def test_api_keys_are_disabled_by_default() -> None:
    assert get_settings().API_KEYS_ENABLED is False


def test_api_key_routes_are_not_registered() -> None:
    for router in (auth_router, security_router, security_admin_router):
        paths = {getattr(route, "path", "") for route in router.routes}
        assert not any("/api-keys" in path for path in paths)


def test_existing_pricing_feature_flags_remain_available() -> None:
    assert MANUAL_BARGAIN_RULES_ENABLED == "manual_bargain_rules_enabled"
    assert AUTO_PRICE_OPTIONS_ENABLED == "auto_price_options_enabled"
    assert PROVIDER_FIRST_MATCHING_ENABLED == "provider_first_matching_enabled"
