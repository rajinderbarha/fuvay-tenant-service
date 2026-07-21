"""Pricing Engine — FastAPI Router (32 endpoints). Zero inline imports. Zero business logic."""
import uuid
from decimal import Decimal

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission, require_tenant_mutation_permission, require_mutation_access_scope
from app.core.security import get_client_ip
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.pricing.schemas import (
    CityTierCreateRequest, CityTierUpdateRequest,
    ServicePriceSetRequest, BrandAdjustmentRequest,
    ZoneCreateRequest, ZoneUpdateRequest,
    DynamicRuleCreateRequest, DynamicRuleUpdateRequest,
    PriceComputeRequest, PricePreviewRequest,
)
from app.engines.pricing.service import PricingService
from app.schemas.base import ApiResponse, Links, Link, ok

logger = structlog.get_logger("pricing.router")
router = APIRouter(prefix="/v1/pricing", tags=["Pricing Engine"])
ENGINE_ID = "pricing"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> PricingService:
    return PricingService(db=db, request_id=getattr(r.state, "request_id", "—"),
                           actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                           actor_role=u.role,
                           actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)

def _req_id(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/meta", summary="Pricing engine introspection", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Pricing Engine", "version": "4.0.0",
            "endpoint_count": 32, "status": "active",
            "pipeline_steps": ["city_tier_floor","tenant_type_price","brand_adjustment",
                               "zone_surcharge","dynamic_rule"],
            "capabilities": ["city_tier_management","service_type_pricing","brand_adjustment",
                             "zone_surcharges","dynamic_rules","price_snapshots",
                             "dispute_replay","cache_management"]}

# ── City Tier Config (5 endpoints) ────────────────────────────────────────────
@router.get("/city-tiers", summary="List city tier floor price configs", response_model=ApiResponse[dict])
async def list_city_tiers(r: Request,
                           tier: str | None = Query(None),
                           category: str | None = Query(None),
                           limit: int = Query(50, ge=1, le=200),
                           cursor: str | None = Query(None),
                           u: UserContext = Depends(get_current_user),
                           s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_city_tier_configs(tier, category, limit, cursor)
    return ok(data, _req_id(r), ENGINE_ID)

@router.get("/city-tiers/{config_id}", summary="Get single city tier config", response_model=ApiResponse[dict])
async def get_city_tier(config_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_city_tier_config(config_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.post("/city-tiers", summary="[Admin] Create city tier floor price",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_city_tier(body: CityTierCreateRequest, r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.create_city_tier_config(body.model_dump())
    return ok(data, _req_id(r), ENGINE_ID)

@router.put("/city-tiers/{config_id}", summary="[Admin] Update city tier floor price",
            response_model=ApiResponse[dict])
async def update_city_tier(config_id: uuid.UUID, body: CityTierUpdateRequest, r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.update_city_tier_config(config_id, body.model_dump(exclude_none=True))
    return ok(data, _req_id(r), ENGINE_ID)

@router.delete("/city-tiers/{config_id}", summary="[Admin] Deactivate city tier config",
               response_model=ApiResponse[dict])
async def delete_city_tier(config_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.delete_city_tier_config(config_id)
    return ok(data, _req_id(r), ENGINE_ID)

# ── Service Type Prices (4 endpoints) ────────────────────────────────────────
@router.get("/tenants/{tenant_id}/prices", summary="List tenant service prices (active only)",
            response_model=ApiResponse[dict])
async def list_tenant_prices(tenant_id: uuid.UUID, r: Request,
                              limit: int = Query(50, ge=1, le=200),
                              cursor: str | None = Query(None),
                              u: UserContext = Depends(get_current_user),
                              s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_tenant_prices(tenant_id, limit, cursor)
    return ok(data, _req_id(r), ENGINE_ID,
              links=Links(actions=[Link(href=f"/v1/pricing/tenants/{tenant_id}/prices/set",
                                        method="POST", rel="set_price")]))

@router.get("/tenants/{tenant_id}/prices/{service_type_id}",
            summary="Get active price for a service type", response_model=ApiResponse[dict])
async def get_tenant_price(tenant_id: uuid.UUID, service_type_id: str, r: Request,
                            u: UserContext = Depends(get_current_user),
                            s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_tenant_price(tenant_id, service_type_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/prices/set",
             summary="Set service type price — validates floor, versions old price",
             response_model=ApiResponse[dict])
async def set_tenant_price(tenant_id: uuid.UUID, body: ServicePriceSetRequest, r: Request,
                            u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                            s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.set_tenant_price(tenant_id, body.model_dump())
    return ok(data, _req_id(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/prices/{service_type_id}/history",
            summary="Full versioned price history for a service type",
            response_model=ApiResponse[dict])
async def get_price_history(tenant_id: uuid.UUID, service_type_id: str, r: Request,
                             limit: int = Query(20, ge=1, le=100),
                             cursor: str | None = Query(None),
                             u: UserContext = Depends(get_current_user),
                             s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_tenant_price_history(tenant_id, service_type_id, limit, cursor)
    return ok(data, _req_id(r), ENGINE_ID)

# ── Brand Adjustment (2 endpoints) ────────────────────────────────────────────
@router.get("/tenants/{tenant_id}/brand-adjustment",
            summary="Get current brand adjustment (markup/discount %)",
            response_model=ApiResponse[dict])
async def get_brand_adj(tenant_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_brand_adjustment(tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.put("/tenants/{tenant_id}/brand-adjustment",
            summary="Set brand adjustment — versioned, validates platform cap",
            response_model=ApiResponse[dict])
async def set_brand_adj(tenant_id: uuid.UUID, body: BrandAdjustmentRequest, r: Request,
                         u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                         s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.set_brand_adjustment(tenant_id, body.adjustment_pct, body.label, body.reason)
    return ok(data, _req_id(r), ENGINE_ID)

# ── Zone Surcharges (5 endpoints) ─────────────────────────────────────────────
@router.get("/tenants/{tenant_id}/zones", summary="List zone surcharges for tenant",
            response_model=ApiResponse[dict])
async def list_zones(tenant_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_zones(tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/zones", summary="Create zone surcharge",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_zone(tenant_id: uuid.UUID, body: ZoneCreateRequest, r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.create_zone(tenant_id, body.model_dump())
    return ok(data, _req_id(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/zones/{zone_id}", summary="Get zone detail",
            response_model=ApiResponse[dict])
async def get_zone(tenant_id: uuid.UUID, zone_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(get_current_user),
                    s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_zone(zone_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.put("/tenants/{tenant_id}/zones/{zone_id}", summary="Update zone surcharge",
            response_model=ApiResponse[dict])
async def update_zone(tenant_id: uuid.UUID, zone_id: uuid.UUID, body: ZoneUpdateRequest,
                       r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.update_zone(zone_id, body.model_dump(exclude_none=True), tenant_id=tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.delete("/tenants/{tenant_id}/zones/{zone_id}", summary="Delete zone surcharge",
               response_model=ApiResponse[dict])
async def delete_zone(tenant_id: uuid.UUID, zone_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.delete_zone(zone_id, tenant_id=tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

# ── Dynamic Pricing Rules (6 endpoints) ───────────────────────────────────────
@router.get("/tenants/{tenant_id}/rules", summary="List dynamic pricing rules",
            response_model=ApiResponse[dict])
async def list_rules(tenant_id: uuid.UUID, r: Request,
                      active_only: bool = Query(False),
                      u: UserContext = Depends(get_current_user),
                      s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_rules(tenant_id, active_only)
    return ok(data, _req_id(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/rules", summary="Create dynamic pricing rule",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_rule(tenant_id: uuid.UUID, body: DynamicRuleCreateRequest, r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.create_rule(tenant_id, body.model_dump())
    return ok(data, _req_id(r), ENGINE_ID,
              links=Links(actions=[Link(href=f"/v1/pricing/tenants/{tenant_id}/rules/{data['rule_id']}/activate",
                                        method="POST", rel="activate")]))

@router.get("/tenants/{tenant_id}/rules/{rule_id}", summary="Get rule detail",
            response_model=ApiResponse[dict])
async def get_rule(tenant_id: uuid.UUID, rule_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(get_current_user),
                    s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_rule(rule_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.put("/tenants/{tenant_id}/rules/{rule_id}", summary="Update rule",
            response_model=ApiResponse[dict])
async def update_rule(tenant_id: uuid.UUID, rule_id: uuid.UUID, body: DynamicRuleUpdateRequest,
                       r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.update_rule(rule_id, body.model_dump(exclude_none=True), tenant_id=tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/rules/{rule_id}/activate",
             summary="Activate a dynamic pricing rule", response_model=ApiResponse[dict])
async def activate_rule(tenant_id: uuid.UUID, rule_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                         s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-39A2R fix: was require_permission (read-only-scope
    # bypassable) with zero tenant_id passed to the service at all.
    data = await s.activate_rule(rule_id, tenant_id=tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/rules/{rule_id}/deactivate",
             summary="Deactivate a rule", response_model=ApiResponse[dict])
async def deactivate_rule(tenant_id: uuid.UUID, rule_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                           s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    # Slice 2F-39A2R fix: same as activate_rule above.
    data = await s.deactivate_rule(rule_id, tenant_id=tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.delete("/tenants/{tenant_id}/rules/{rule_id}",
               summary="Delete rule (must be inactive first)", response_model=ApiResponse[dict])
async def delete_rule(tenant_id: uuid.UUID, rule_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.delete_rule(rule_id, tenant_id=tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

# ── Price Computation (3 endpoints) ──────────────────────────────────────────
@router.post("/compute", summary="Compute price — runs full pipeline, stores immutable snapshot",
             response_model=ApiResponse[dict])
async def compute_price(body: PriceComputeRequest, r: Request,
                         u: UserContext = Depends(require_mutation_access_scope),
                         s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.compute_and_snapshot(
        body.tenant_id, body.service_type_id, body.service_category,
        body.city_name, body.pincode, body.booking_id, body.requested_at)
    return ok(data, _req_id(r), ENGINE_ID,
              links=Links(actions=[Link(href=f"/v1/pricing/snapshots/{data['snapshot_id']}",
                                        method="GET", rel="snapshot"),
                                    Link(href=f"/v1/pricing/snapshots/{data['snapshot_id']}/replay",
                                         method="POST", rel="replay")]))

@router.post("/tenants/{tenant_id}/price-preview",
             summary="Preview price without storing snapshot (read-only)",
             response_model=ApiResponse[dict])
async def preview_price(tenant_id: uuid.UUID, body: PricePreviewRequest, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.preview_price(tenant_id, body.service_type_id, body.service_category,
                                  body.city_name, body.pincode)
    return ok(data, _req_id(r), ENGINE_ID)

# ── Price Snapshots (4 endpoints) ─────────────────────────────────────────────
@router.get("/snapshots/{snapshot_id}", summary="Get price snapshot with full pipeline trace",
            response_model=ApiResponse[dict])
async def get_snapshot(snapshot_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_snapshot(snapshot_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.post("/snapshots/{snapshot_id}/replay",
             summary="Replay historical snapshot for dispute resolution",
             response_model=ApiResponse[dict])
async def replay_snapshot(snapshot_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.replay_snapshot(snapshot_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/snapshots",
            summary="List price computation history (cursor-paginated)",
            response_model=ApiResponse[dict])
async def list_snapshots(tenant_id: uuid.UUID, r: Request,
                          limit: int = Query(50, ge=1, le=200),
                          cursor: str | None = Query(None),
                          u: UserContext = Depends(get_current_user),
                          s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.list_snapshots(tenant_id, limit, cursor)
    return ok(data, _req_id(r), ENGINE_ID)

# ── Cache Management (2 endpoints) ────────────────────────────────────────────
@router.post("/tenants/{tenant_id}/cache/invalidate",
             summary="[Admin] Invalidate all pricing cache for a tenant",
             response_model=ApiResponse[dict])
async def invalidate_cache(tenant_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.invalidate_tenant_cache(tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/cache/status",
            summary="Check cached pricing keys for a tenant",
            response_model=ApiResponse[dict])
async def cache_status(tenant_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: PricingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_cache_status(tenant_id)
    return ok(data, _req_id(r), ENGINE_ID)
