"""Regression coverage for the intentionally dormant API-key product."""
from app.config import get_settings
from app.core.feature_flags import (
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


def test_provider_first_matching_flag_remains_available() -> None:
    assert PROVIDER_FIRST_MATCHING_ENABLED == "provider_first_matching_enabled"
