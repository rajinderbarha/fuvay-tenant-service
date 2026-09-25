from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.engines.settings_engine.models import PlatformSetting
from app.engines.settings_engine.branding import public_branding_payload, read_platform_branding, unwrap_setting_value
from app.schemas.base import ok

router = APIRouter(prefix="/v1/public/app-config", tags=["Public App Configuration"])


@router.get("/customer")
async def customer_app_config(request: Request, db: AsyncSession = Depends(get_db)):
    keys = {
        "customer_min_supported_version",
        "customer_ios_store_url",
        "customer_android_store_url",
        "maintenance_mode_enabled",
        "home_services_enabled",
    }
    rows = (await db.execute(
        select(PlatformSetting).where(PlatformSetting.key.in_(keys), PlatformSetting.status == "active")
    )).scalars().all()
    values = {row.key: unwrap_setting_value(row.value) for row in rows}
    branding, branding_row = await read_platform_branding(db)
    payload = {
        "minimum_supported_version": str(values.get("customer_min_supported_version") or "1.0.0"),
        "ios_store_url": str(values.get("customer_ios_store_url") or "") or None,
        "android_store_url": str(values.get("customer_android_store_url") or "") or None,
        "maintenance": bool(values.get("maintenance_mode_enabled", False)),
        "enabled_verticals": (["home_services"] if values.get("home_services_enabled", True) else []),
        "branding": public_branding_payload(branding, branding_row),
    }
    request_id = getattr(request.state, "request_id", "public")
    return ok(payload, request_id, "public.app_config.customer")


@router.get("/branding")
async def platform_branding_config(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Public, read-only brand identity consumed by every web surface.

    A short cache keeps page shells fast while still allowing an administrator
    to publish a correction without rebuilding or restarting any frontend.
    """
    branding, row = await read_platform_branding(db)
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    request_id = getattr(request.state, "request_id", "public")
    return ok(public_branding_payload(branding, row), request_id, "public.app_config.branding")
