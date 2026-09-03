from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.engines.settings_engine.models import PlatformSetting
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
    values = {row.key: row.value for row in rows}
    payload = {
        "minimum_supported_version": str(values.get("customer_min_supported_version") or "1.0.0"),
        "ios_store_url": str(values.get("customer_ios_store_url") or "") or None,
        "android_store_url": str(values.get("customer_android_store_url") or "") or None,
        "maintenance": bool(values.get("maintenance_mode_enabled", False)),
        "enabled_verticals": (["home_services"] if values.get("home_services_enabled", True) else []),
    }
    request_id = getattr(request.state, "request_id", "public")
    return ok(payload, request_id, "public.app_config.customer")
