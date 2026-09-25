"""Contracts for runtime-configurable platform identity."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.engines.settings_engine.branding import (
    DEFAULT_PLATFORM_BRANDING,
    PlatformBranding,
    PlatformBrandingUpdate,
    normalized_branding,
    unwrap_setting_value,
)


ROOT = Path(__file__).resolve().parents[1]


def test_branding_accepts_cloudinary_assets_and_normalizes_colours():
    value = PlatformBranding(
        **{
            **DEFAULT_PLATFORM_BRANDING,
            "brand_name": "Acme Services",
            "logo_light_url": "https://res.cloudinary.com/demo/image/upload/logo.png",
            "favicon_url": "https://res.cloudinary.com/demo/image/upload/icon.webp",
            "primary_color": "#0f6b60",
        }
    )
    assert value.brand_name == "Acme Services"
    assert value.primary_color == "#0F6B60"


@pytest.mark.parametrize("url", ["http://example.com/logo.png", "https://example.com/logo.png", "//example.com/logo.png", "javascript:alert(1)"])
def test_branding_rejects_insecure_asset_urls(url: str):
    with pytest.raises(ValidationError):
        PlatformBranding(**{**DEFAULT_PLATFORM_BRANDING, "favicon_url": url})


def test_branding_publish_requires_reason_and_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        PlatformBrandingUpdate(**{**DEFAULT_PLATFORM_BRANDING, "change_reason": "no"})
    with pytest.raises(ValidationError):
        PlatformBranding(**{**DEFAULT_PLATFORM_BRANDING, "private_storage_key": "secret"})


def test_primary_brand_colour_must_keep_action_text_accessible():
    with pytest.raises(ValidationError):
        PlatformBranding(**{**DEFAULT_PLATFORM_BRANDING, "primary_color": "#FFFFFF"})


def test_legacy_and_wrapped_jsonb_values_are_supported_safely():
    custom = {**DEFAULT_PLATFORM_BRANDING, "brand_name": "New Brand"}
    assert unwrap_setting_value({"v": custom}) == custom
    assert normalized_branding(custom).brand_name == "New Brand"
    assert normalized_branding({"v": custom}).brand_name == "New Brand"
    assert normalized_branding("corrupt").brand_name == "Fuvay"


def test_branding_routes_precede_dynamic_put_and_remain_public_read_only():
    admin = (ROOT / "app/engines/settings_engine/admin_router.py").read_text(encoding="utf-8")
    public = (ROOT / "app/engines/public_app_config/router.py").read_text(encoding="utf-8")
    assert admin.index('@router.put("/branding"') < admin.index('@router.put("/{setting_key}"')
    assert '@router.get("/branding")' in public
    assert '@router.put("/branding")' not in public
    assert 'require_permission(P.SETTINGS_UPDATE)' in admin[admin.index('@router.put("/branding"'):admin.index('class UpdateSettingBody')]


def test_branding_artwork_is_cloudinary_only_and_available_in_admin_picker():
    validation = (ROOT / "app/engines/media/validation.py").read_text(encoding="utf-8")
    storage = (ROOT / "app/engines/media/storage.py").read_text(encoding="utf-8")
    picker = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    assert '"platform_brand_asset"' in validation
    assert '"platform_brand_asset"' in storage
    assert '"platform_brand_asset"' in picker


def test_every_web_surface_consumes_the_runtime_brand_profile():
    files = [
        ROOT / "frontend/super-admin/app/layout.tsx",
        ROOT / "frontend/tenant-portal/app/layout.tsx",
        ROOT / "frontend/public-site/app/layout.tsx",
    ]
    for file in files:
        text = file.read_text(encoding="utf-8")
        assert "PlatformBrand" in text or "getPlatformBranding" in text
