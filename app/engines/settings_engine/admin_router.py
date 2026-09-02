"""Platform Settings Enterprise Upgrade — Admin Router.
All endpoints under /v1/admin/settings/*. All write endpoints are permission-guarded
via P.SETTINGS_*; super_admin holds P.ALL so this is additive, not a regression.
The pre-existing /v1/settings/* router (internal resolve() calls from other engines) is untouched.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.settings_engine.service import SettingsService
from app.exceptions import NotFoundException
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/settings", tags=["Platform Settings SOC"])
ENGINE_ID = "settings"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.SETTINGS_READ))) -> SettingsService:
    return SettingsService(db=db, request_id=_rid(r),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)


def _rid(r): return getattr(r.state, "request_id", "—")


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════

@router.get("/summary", summary="Settings summary cards")
async def summary(r: Request, s: SettingsService = Depends(_svc), u: UserContext = Depends(require_super_admin)):
    return ok(await s.get_summary(), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# SEED DEFAULTS
# ═══════════════════════════════════════════════════════════════

@router.post("/seed-defaults/preview", summary="Preview ServiceOS default settings")
async def seed_defaults_preview(r: Request,
                                 u: UserContext = Depends(require_permission(P.SETTINGS_SEED_DEFAULTS)),
                                 s: SettingsService = Depends(_svc)):
    return ok(await s.seed_defaults(preview=True), _rid(r), ENGINE_ID)


class SeedDefaultsBody(BaseModel):
    force: bool = False


@router.post("/seed-defaults", summary="Seed ServiceOS default settings")
async def seed_defaults(r: Request, body: SeedDefaultsBody = SeedDefaultsBody(),
                         u: UserContext = Depends(require_permission(P.SETTINGS_SEED_DEFAULTS)),
                         s: SettingsService = Depends(_svc)):
    return ok(await s.seed_defaults(preview=False, force=body.force), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# GLOBAL / PLATFORM SETTINGS
# ═══════════════════════════════════════════════════════════════

@router.get("", summary="List platform settings")
async def list_settings(r: Request,
                         category: Optional[str] = Query(None),
                         is_secret: Optional[bool] = Query(None),
                         status: Optional[str] = Query(None),
                         limit: int = Query(100, ge=1, le=500), cursor: Optional[str] = Query(None),
                         u: UserContext = Depends(require_permission(P.SETTINGS_READ)),
                         s: SettingsService = Depends(_svc)):
    return ok(await s.list_platform_settings(limit, cursor, category, is_secret, status), _rid(r), ENGINE_ID)


@router.get("/groups", summary="List settings categories with counts")
async def list_groups(r: Request,
                       u: UserContext = Depends(require_permission(P.SETTINGS_READ)),
                       s: SettingsService = Depends(_svc)):
    from app.engines.settings_engine.seed_data import ALL_CATEGORIES
    all_settings = await s.list_platform_settings(limit=500, cursor=None)
    counts: dict[str, int] = {c: 0 for c in ALL_CATEGORIES}
    for setting in all_settings["settings"]:
        counts[setting["category"]] = counts.get(setting["category"], 0) + 1
    return ok({"categories": [{"category": c, "setting_count": n} for c, n in counts.items()]}, _rid(r), ENGINE_ID)


class CreateSettingBody(BaseModel):
    key: str
    label: str
    value: object
    setting_type: str
    description: Optional[str] = None
    category: str = "general_platform"
    is_secret: bool = False
    risk_level: str = "low"
    requires_approval: bool = False
    requires_restart: bool = False
    is_runtime_editable: bool = True
    owner_module: Optional[str] = None
    allowed_values: Optional[list] = None


@router.post("", summary="Create platform setting")
async def create_setting(r: Request, body: CreateSettingBody,
                          u: UserContext = Depends(require_permission(P.SETTINGS_CREATE)),
                          s: SettingsService = Depends(_svc)):
    from app.engines.settings_engine.models import PlatformSetting
    from app.exceptions import ServiceOSException
    existing = await s.db.execute(select(PlatformSetting.id).where(PlatformSetting.key == body.key))
    if existing.scalar_one_or_none():
        raise ServiceOSException("CONFLICT", f"Setting key '{body.key}' already exists.")
    result = await s.set_platform_setting(
        body.key, body.value, body.setting_type, body.description,
        label=body.label, category=body.category, is_secret=body.is_secret,
        risk_level=body.risk_level, requires_approval=body.requires_approval,
        requires_restart=body.requires_restart, is_runtime_editable=body.is_runtime_editable,
        owner_module=body.owner_module, allowed_values=body.allowed_values,
    )
    return ok(result, _rid(r), ENGINE_ID)


class UpdateSettingBody(BaseModel):
    value: object
    setting_type: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    category: Optional[str] = None
    risk_level: Optional[str] = None
    reason: Optional[str] = None


@router.put("/{setting_key}", summary="Update platform setting")
async def update_setting(r: Request, setting_key: str, body: UpdateSettingBody,
                          u: UserContext = Depends(require_permission(P.SETTINGS_UPDATE)),
                          s: SettingsService = Depends(_svc)):
    result = await s.set_platform_setting(
        setting_key, body.value, body.setting_type, body.description,
        label=body.label, category=body.category, risk_level=body.risk_level, reason=body.reason,
    )
    return ok(result, _rid(r), ENGINE_ID)


class EnableDisableBody(BaseModel):
    reason: Optional[str] = None


@router.post("/{setting_key}/enable", summary="Enable setting")
async def enable_setting(r: Request, setting_key: str, body: EnableDisableBody = EnableDisableBody(),
                          u: UserContext = Depends(require_permission(P.SETTINGS_ENABLE)),
                          s: SettingsService = Depends(_svc)):
    from app.engines.settings_engine.models import PlatformSetting
    row = (await s.db.execute(select(PlatformSetting).where(PlatformSetting.key == setting_key))).scalar_one_or_none()
    if not row: raise NotFoundException("PlatformSetting", setting_key)
    row.status = "active"
    await s._audit("platform", setting_key, "disabled", "active", reason=body.reason, action_type="enabled")
    return ok({"key": setting_key, "status": "active"}, _rid(r), ENGINE_ID)


@router.post("/{setting_key}/disable", summary="Disable setting")
async def disable_setting(r: Request, setting_key: str, body: EnableDisableBody = EnableDisableBody(),
                           u: UserContext = Depends(require_permission(P.SETTINGS_DISABLE)),
                           s: SettingsService = Depends(_svc)):
    from app.engines.settings_engine.models import PlatformSetting
    row = (await s.db.execute(select(PlatformSetting).where(PlatformSetting.key == setting_key))).scalar_one_or_none()
    if not row: raise NotFoundException("PlatformSetting", setting_key)
    row.status = "disabled"
    await s._audit("platform", setting_key, "active", "disabled", reason=body.reason, action_type="disabled")
    return ok({"key": setting_key, "status": "disabled"}, _rid(r), ENGINE_ID)


class ImpactPreviewBody(BaseModel):
    new_value: object


@router.post("/{setting_key}/impact-preview", summary="Preview impact of a setting change")
async def impact_preview(r: Request, setting_key: str, body: ImpactPreviewBody,
                          u: UserContext = Depends(require_permission(P.SETTINGS_IMPACT_PREVIEW)),
                          s: SettingsService = Depends(_svc)):
    return ok(await s.check_impact(setting_key, body.new_value), _rid(r), ENGINE_ID)


class RollbackBody(BaseModel):
    log_id: uuid.UUID
    reason: str


@router.post("/{setting_key}/rollback", summary="Rollback a setting to a prior version")
async def rollback_setting(r: Request, setting_key: str, body: RollbackBody,
                            u: UserContext = Depends(require_permission(P.SETTINGS_ROLLBACK)),
                            s: SettingsService = Depends(_svc)):
    return ok(await s.rollback_setting(body.log_id, body.reason), _rid(r), ENGINE_ID)


@router.get("/{setting_key}/history", summary="Get version history for a setting")
async def setting_history(r: Request, setting_key: str,
                           u: UserContext = Depends(require_permission(P.SETTINGS_HISTORY_READ)),
                           s: SettingsService = Depends(_svc)):
    return ok(await s.get_setting_history(setting_key), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# EFFECTIVE VALUE RESOLVER
# ═══════════════════════════════════════════════════════════════

class ResolveBody(BaseModel):
    key: str
    tenant_id: Optional[uuid.UUID] = None
    plan_type: Optional[str] = None
    environment: Optional[str] = "production"


@router.post("/resolve-effective-value", summary="Resolve effective value for a setting")
async def resolve_effective_value(r: Request, body: ResolveBody,
                                   u: UserContext = Depends(require_permission(P.SETTINGS_READ)),
                                   s: SettingsService = Depends(_svc)):
    return ok(await s.resolve_effective_value(body.key, body.tenant_id, body.plan_type), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# PLAN / PACKAGE SETTINGS (reads/writes real ServicePackage rows)
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# CATEGORY SETTINGS (reads/writes real ServiceCategory rows)
# ═══════════════════════════════════════════════════════════════

def _category_to_dict(c) -> dict:
    return {
        "id": str(c.id), "name": c.name, "slug": c.slug, "vertical_type": c.vertical_type,
        "finance_model": c.finance_model, "provider_business_model": c.provider_business_model,
        "monetization_model": c.monetization_model, "is_active": c.is_active,
        "is_customer_visible": c.is_customer_visible, "pricing_supported": c.pricing_supported,
        # Derived Home-Services-style rule flags — computed from finance_model, not stored directly
        "payment_collection_enabled": c.finance_model not in
            ("credit_wallet_only", None),
        "tenant_payouts_enabled": c.finance_model not in
            ("credit_wallet_only", None),
    }


@router.get("/categories", summary="List category settings")
async def list_category_settings(r: Request,
                                  u: UserContext = Depends(require_permission(P.SETTINGS_CATEGORY_READ)),
                                  db: AsyncSession = Depends(get_db)):
    from app.engines.admin_catalog.models import ServiceCategory
    rows = (await db.execute(select(ServiceCategory).order_by(ServiceCategory.display_order))).scalars().all()
    return ok({"categories": [_category_to_dict(c) for c in rows]}, _rid(r), ENGINE_ID)


@router.get("/categories/{category_id}", summary="Get category settings")
async def get_category_settings(r: Request, category_id: uuid.UUID,
                                 u: UserContext = Depends(require_permission(P.SETTINGS_CATEGORY_READ)),
                                 db: AsyncSession = Depends(get_db)):
    from app.engines.admin_catalog.models import ServiceCategory
    c = (await db.execute(select(ServiceCategory).where(ServiceCategory.id == category_id))).scalar_one_or_none()
    if not c: raise NotFoundException("ServiceCategory", str(category_id))
    return ok(_category_to_dict(c), _rid(r), ENGINE_ID)


class UpdateCategorySettingsBody(BaseModel):
    finance_model: Optional[str] = None
    provider_business_model: Optional[str] = None
    monetization_model: Optional[str] = None
    is_active: Optional[bool] = None
    reason: Optional[str] = None


@router.put("/categories/{category_id}", summary="Update category settings")
async def update_category_settings(r: Request, category_id: uuid.UUID, body: UpdateCategorySettingsBody,
                                    u: UserContext = Depends(require_permission(P.SETTINGS_CATEGORY_UPDATE)),
                                    db: AsyncSession = Depends(get_db)):
    from app.engines.admin_catalog.models import ServiceCategory
    c = (await db.execute(select(ServiceCategory).where(ServiceCategory.id == category_id))).scalar_one_or_none()
    if not c: raise NotFoundException("ServiceCategory", str(category_id))
    for field in ("finance_model", "provider_business_model", "monetization_model", "is_active"):
        val = getattr(body, field)
        if val is not None:
            setattr(c, field, val)
    return ok(_category_to_dict(c), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# TENANT OVERRIDES
# ═══════════════════════════════════════════════════════════════

@router.get("/tenant-overrides", summary="List tenant setting overrides")
async def list_tenant_overrides(r: Request,
                                 u: UserContext = Depends(require_permission(P.SETTINGS_TENANT_OVERRIDES_READ)),
                                 s: SettingsService = Depends(_svc)):
    return ok(await s.list_all_tenant_overrides(), _rid(r), ENGINE_ID)


class CreateTenantOverrideBody(BaseModel):
    tenant_id: uuid.UUID
    key: str
    value: object
    setting_type: str = "boolean"
    reason: str
    expires_at: Optional[datetime] = None
    requires_approval: bool = False


@router.post("/tenant-overrides", summary="Create tenant setting override")
async def create_tenant_override(r: Request, body: CreateTenantOverrideBody,
                                  u: UserContext = Depends(require_permission(P.SETTINGS_TENANT_OVERRIDES_CREATE)),
                                  s: SettingsService = Depends(_svc)):
    result = await s.set_tenant_setting(body.tenant_id, body.key, body.value, body.setting_type,
                                         body.reason, body.expires_at, body.requires_approval)
    return ok(result, _rid(r), ENGINE_ID)


class UpdateTenantOverrideBody(BaseModel):
    value: object
    setting_type: str = "boolean"
    reason: str
    expires_at: Optional[datetime] = None


@router.put("/tenant-overrides/{override_id}", summary="Update tenant setting override")
async def update_tenant_override(r: Request, override_id: uuid.UUID, body: UpdateTenantOverrideBody,
                                  u: UserContext = Depends(require_permission(P.SETTINGS_TENANT_OVERRIDES_CREATE)),
                                  s: SettingsService = Depends(_svc)):
    from app.engines.settings_engine.models import TenantSetting
    row = (await s.db.execute(select(TenantSetting).where(TenantSetting.id == override_id))).scalar_one_or_none()
    if not row: raise NotFoundException("TenantSetting", str(override_id))
    result = await s.set_tenant_setting(row.tenant_id, row.key, body.value, body.setting_type,
                                         body.reason, body.expires_at)
    return ok(result, _rid(r), ENGINE_ID)


class RevokeTenantOverrideBody(BaseModel):
    reason: str


@router.post("/tenant-overrides/{override_id}/revoke", summary="Revoke tenant setting override")
async def revoke_tenant_override(r: Request, override_id: uuid.UUID, body: RevokeTenantOverrideBody,
                                  u: UserContext = Depends(require_permission(P.SETTINGS_TENANT_OVERRIDES_REVOKE)),
                                  s: SettingsService = Depends(_svc)):
    from app.engines.settings_engine.models import TenantSetting
    row = (await s.db.execute(select(TenantSetting).where(TenantSetting.id == override_id))).scalar_one_or_none()
    if not row: raise NotFoundException("TenantSetting", str(override_id))
    return ok(await s.delete_tenant_setting(row.tenant_id, row.key, body.reason), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# FEATURE FLAGS
# ═══════════════════════════════════════════════════════════════

@router.get("/feature-flags", summary="List feature flags")
async def list_feature_flags(r: Request,
                              u: UserContext = Depends(require_permission(P.SETTINGS_FEATURE_FLAGS_READ)),
                              s: SettingsService = Depends(_svc)):
    return ok(await s.list_feature_flags(), _rid(r), ENGINE_ID)


class CreateFeatureFlagBody(BaseModel):
    flag_key: str
    label: str
    description: Optional[str] = None
    status: str = "disabled"
    rollout_type: str = "global"
    rollout_percent: Optional[int] = None
    category_scope: Optional[str] = None
    tenant_scope: Optional[uuid.UUID] = None
    owner_module: Optional[str] = None


@router.post("/feature-flags", summary="Create feature flag")
async def create_feature_flag(r: Request, body: CreateFeatureFlagBody,
                               u: UserContext = Depends(require_permission(P.SETTINGS_FEATURE_FLAGS_UPDATE)),
                               s: SettingsService = Depends(_svc)):
    return ok(await s.create_feature_flag(body.model_dump()), _rid(r), ENGINE_ID)


class UpdateFeatureFlagBody(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    rollout_type: Optional[str] = None
    rollout_percent: Optional[int] = None
    category_scope: Optional[str] = None
    owner_module: Optional[str] = None


@router.put("/feature-flags/{flag_id}", summary="Update feature flag")
async def update_feature_flag(r: Request, flag_id: uuid.UUID, body: UpdateFeatureFlagBody,
                               u: UserContext = Depends(require_permission(P.SETTINGS_FEATURE_FLAGS_UPDATE)),
                               s: SettingsService = Depends(_svc)):
    return ok(await s.update_feature_flag(flag_id, body.model_dump(exclude_none=True)), _rid(r), ENGINE_ID)


@router.post("/feature-flags/{flag_id}/enable", summary="Enable feature flag")
async def enable_feature_flag(r: Request, flag_id: uuid.UUID,
                               u: UserContext = Depends(require_permission(P.SETTINGS_FEATURE_FLAGS_UPDATE)),
                               s: SettingsService = Depends(_svc)):
    return ok(await s.set_feature_flag_status(flag_id, "enabled"), _rid(r), ENGINE_ID)


@router.post("/feature-flags/{flag_id}/disable", summary="Disable feature flag")
async def disable_feature_flag(r: Request, flag_id: uuid.UUID,
                                u: UserContext = Depends(require_permission(P.SETTINGS_FEATURE_FLAGS_UPDATE)),
                                s: SettingsService = Depends(_svc)):
    return ok(await s.set_feature_flag_status(flag_id, "disabled"), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════

@router.get("/audit-logs", summary="List settings audit log")
async def audit_logs(r: Request,
                      key: Optional[str] = Query(None),
                      tenant_id: Optional[uuid.UUID] = Query(None),
                      limit: int = Query(50, ge=1, le=200), cursor: Optional[str] = Query(None),
                      u: UserContext = Depends(require_permission(P.SETTINGS_AUDIT_READ)),
                      s: SettingsService = Depends(_svc)):
    return ok(await s.get_audit_log(tenant_id, key, limit, cursor), _rid(r), ENGINE_ID)


# NOTE: this single-segment catch-all MUST be registered last — every literal-path
# GET above (/plans, /categories, /tenant-overrides, /feature-flags, /audit-logs,
# /groups) would otherwise be swallowed by {setting_key} since FastAPI matches
# routes in registration order.
@router.get("/{setting_key}", summary="Get platform setting")
async def get_setting(r: Request, setting_key: str,
                       u: UserContext = Depends(require_permission(P.SETTINGS_READ)),
                       s: SettingsService = Depends(_svc)):
    return ok(await s.get_platform_setting(setting_key), _rid(r), ENGINE_ID)
