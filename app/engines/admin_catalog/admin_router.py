"""Admin Catalog Engine — Super Admin Router.
All write endpoints require require_super_admin.
Read endpoints require authenticated user (for dropdown population in tenant portal).
"""
import uuid
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Body, Depends, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.exceptions import ServiceOSException

from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.service import AdminCatalogService
from app.engines.admin_catalog.service_option_service import ServiceOptionService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin", tags=["Admin Catalog"])
ENGINE_ID = "admin_catalog"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> AdminCatalogService:
    return AdminCatalogService(db=db, request_id=getattr(r.state, "request_id", "—"),
                               actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                               actor_role=u.role)


def _opt_svc(r: Request, db: AsyncSession = Depends(get_db),
             u: UserContext = Depends(get_current_user)) -> ServiceOptionService:
    return ServiceOptionService(db=db, request_id=getattr(r.state, "request_id", "—"),
                                actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                                actor_role=u.role)


def _rid(r): return getattr(r.state, "request_id", "—")


# ═══════════════════════════════════════════════════════════════
# PRICING MODEL REGISTRY (canonical, data-driven dropdown source)
# ═══════════════════════════════════════════════════════════════

@router.get("/pricing-models", response_model=ApiResponse[dict],
            summary="List canonical pricing models + their field requirements",
            tags=["Pricing Models"])
async def list_pricing_models(r: Request, u: UserContext = Depends(get_current_user)):
    """MODULE-L5-03: single source of truth for pricing models. Frontend/mobile
    pricing dropdowns should load from here instead of hardcoding a list. Any
    authenticated user (Super Admin catalog forms + tenant portal) may read this
    non-sensitive static metadata."""
    from app.engines.admin_catalog.service import PRICING_MODEL_REGISTRY
    models = [{"code": code, **meta} for code, meta in PRICING_MODEL_REGISTRY.items()]
    return ok({"pricing_models": models, "count": len(models)}, _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# PRICING TIERS
# ═══════════════════════════════════════════════════════════════

# Retired: admin pricing tiers are not part of the current provider-owned
# Home Services pricing model. Kept as an unregistered helper only until the
# historical service/model code is removed by a DB cleanup migration.
async def list_tiers(r: Request,
                     is_active: bool | None = Query(None),
                     q: str | None = Query(None),
                     used_in_rules: bool | None = Query(None),
                     has_city_mapping: bool | None = Query(None),
                     has_zipcode_mapping: bool | None = Query(None),
                     date_from: str | None = Query(None),
                     date_to: str | None = Query(None),
                     u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                     s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_tiers(is_active, q, used_in_rules, has_city_mapping,
                                  has_zipcode_mapping, date_from, date_to), _rid(r), ENGINE_ID)


# Retired route: /v1/admin/tiers/summary
async def tiers_summary(r: Request,
                        u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                        s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_tiers_summary(), _rid(r), ENGINE_ID)


# Retired route: /v1/admin/tiers/export
async def export_tiers(r: Request,
                       is_active: bool | None = Query(None),
                       u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                       s: AdminCatalogService = Depends(_svc)):
    rows = await s.export_tiers(is_active=is_active)
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tiers
async def create_tier(r: Request,
                      u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                      s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_tier(body), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/tiers/resolve-location
async def resolve_location_get(r: Request,
                                city: str | None = Query(None),
                                zipcode: str | None = Query(None),
                                state: str | None = Query(None),
                                district: str | None = Query(None),
                                zone: str | None = Query(None),
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    return ok(await s.resolve_location(city, zipcode, state, None, district, zone), _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tiers/resolve-location
async def resolve_location_post(r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.resolve_location(body.get("city"), body.get("zipcode"),
                                        body.get("state"), body.get("country")), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/tiers/{tier_id}/detail
async def get_tier_detail(tier_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                          s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_tier_detail(tier_id), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/tiers/{tier_id}
async def get_tier(tier_id: uuid.UUID, r: Request,
                   u: UserContext = Depends(require_super_admin),
                   s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_tier(tier_id), _rid(r), ENGINE_ID)


# Retired route: PUT /v1/admin/tiers/{tier_id}
async def update_tier(tier_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                      s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_tier(tier_id, body), _rid(r), ENGINE_ID)


# Retired route: DELETE /v1/admin/tiers/{tier_id}
async def delete_tier(tier_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                      s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_tier(tier_id), _rid(r), ENGINE_ID)


# Retired route: DELETE /v1/admin/tiers/{tier_id}/hard-delete
async def hard_delete_tier(tier_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                            s: AdminCatalogService = Depends(_svc)):
    return ok(await s.hard_delete_tier(tier_id), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# TIER LOCATIONS
# ═══════════════════════════════════════════════════════════════

# Retired route: GET /v1/admin/tier-locations
async def list_tier_locations(r: Request,
                               tier_id: uuid.UUID | None = Query(None),
                               q: str | None = Query(None),
                               state: str | None = Query(None),
                               district: str | None = Query(None),
                               city: str | None = Query(None),
                               zipcode: str | None = Query(None),
                               is_active: bool | None = Query(None),
                               has_conflict: bool | None = Query(None),
                               page: int = Query(1, ge=1),
                               page_size: int = Query(50, ge=1, le=500),
                               sort_by: str = Query("created_at"),
                               sort_dir: str = Query("desc"),
                               u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                               s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_tier_locations(
        tier_id, q, state, district, city, zipcode, is_active, has_conflict,
        page, page_size, sort_by, sort_dir,
    ), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/tier-locations/summary
async def tier_locations_summary(r: Request,
                                  u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_tier_location_summary(), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/tier-locations/export
async def export_tier_locations(r: Request,
                                 tier_id: uuid.UUID | None = Query(None),
                                 state: str | None = Query(None),
                                 district: str | None = Query(None),
                                 city: str | None = Query(None),
                                 is_active: bool | None = Query(None),
                                 has_conflict: bool | None = Query(None),
                                 u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                                 s: AdminCatalogService = Depends(_svc)):
    rows = await s.export_tier_locations(
        tier_id=tier_id, state=state, district=district, city=city,
        is_active=is_active, has_conflict=has_conflict,
    )
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tier-locations/import/preview
async def import_tier_locations_preview(r: Request,
                                         u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                         s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.import_tier_locations_preview(
        body.get("file_name") or "import.csv", body.get("csv_text") or "",
    ), _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tier-locations/import/confirm
async def import_tier_locations_confirm(r: Request,
                                         u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                         s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.import_tier_locations_confirm(
        uuid.UUID(str(body["batch_id"])), body.get("conflict_resolution", "skip"),
    ), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/tier-locations/imports
async def list_import_batches(r: Request,
                               page: int = Query(1, ge=1),
                               page_size: int = Query(20, ge=1, le=100),
                               u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                               s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_import_batches(page, page_size), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/tier-locations/imports/{batch_id}
async def get_import_batch(batch_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_permission(P.CATALOG_TIERS_READ)),
                            s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_import_batch(batch_id), _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tier-locations/bulk/change-tier
async def bulk_change_tier_locations(r: Request,
                                      u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                      s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.bulk_change_tier_locations(
        body.get("location_ids", []), str(body.get("new_tier_id", ""))
    ), _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tier-locations/bulk/deactivate
async def bulk_deactivate_tier_locations(r: Request,
                                          u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                          s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.bulk_deactivate_tier_locations(body.get("location_ids", [])), _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tier-locations
async def create_tier_location(r: Request,
                                u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_tier_location(body), _rid(r), ENGINE_ID)


# Retired route: PUT /v1/admin/tier-locations/{location_id}
async def update_tier_location(location_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_tier_location(location_id, body), _rid(r), ENGINE_ID)


# Retired route: DELETE /v1/admin/tier-locations/{location_id}
async def delete_tier_location(location_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_tier_location(location_id), _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/tier-locations/{location_id}/resolve-conflict
async def resolve_conflict_location(location_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_permission(P.CATALOG_TIERS_WRITE)),
                                     s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.resolve_conflict_location(
        location_id, body.get("resolution_type", "keep_this"),
        body.get("override_tier_id"),
    ), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# SERVICE CATEGORIES
# ═══════════════════════════════════════════════════════════════

@router.get("/service-categories", response_model=ApiResponse[dict], summary="List service categories",
            tags=["Service Categories"])
async def list_categories(r: Request,
                           is_active: bool | None = Query(None),
                           u: UserContext = Depends(require_super_admin),
                           s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_categories(is_active), _rid(r), ENGINE_ID)


# ── MODULE-L5-10: per-category commission rate ────────────────────────────────
@router.get("/category-commission-rates", response_model=ApiResponse[list],
            summary="List categories with their commission rate", tags=["Commission"])
async def list_category_commission_rates(
    r: Request,
    vertical_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_permission(P.FINANCE_READ)),
):
    from sqlalchemy import select
    from app.engines.admin_catalog.models import ServiceCategory
    from app.engines.invoice_payment.constants import DEFAULT_COMMISSION_RATE
    from app.engines.vertical_catalog.models import Vertical
    from app.engines.vertical_monetization.models import VerticalMonetizationPolicy
    stmt = select(ServiceCategory)
    if vertical_type:
        stmt = stmt.where(ServiceCategory.vertical_type == vertical_type)
    rows = (await db.execute(
        stmt.order_by(ServiceCategory.display_order, ServiceCategory.name)
    )).scalars().all()
    default = float(DEFAULT_COMMISSION_RATE)
    vertical_keys = {c.vertical_type for c in rows if c.vertical_type}
    policy_by_key = {}
    if vertical_keys:
        policy_rows = (await db.execute(
            select(Vertical.key, VerticalMonetizationPolicy)
            .join(VerticalMonetizationPolicy, VerticalMonetizationPolicy.vertical_id == Vertical.id)
            .where(
                Vertical.key.in_(vertical_keys),
                VerticalMonetizationPolicy.is_current.is_(True),
                VerticalMonetizationPolicy.status == "published",
            )
        )).all()
        policy_by_key = {key: policy for key, policy in policy_rows}

    def _resolution(c):
        policy = policy_by_key.get(c.vertical_type)
        if c.vertical_type == "home_services":
            if policy is None:
                return None, "policy_not_published", False
            if policy.provider_model != "PERCENTAGE_COMMISSION":
                return None, "model_not_percentage", False
            if policy.provider_percentage is not None:
                return float(policy.provider_percentage), "vertical_default", True
            return None, "percentage_default_missing", False
        own = float(c.commission_pct) if c.commission_pct is not None else None
        if policy is not None and policy.provider_model != "PERCENTAGE_COMMISSION":
            return None, "model_not_percentage", False
        if own is not None:
            return own, "category_override", True
        if policy is not None and policy.provider_percentage is not None:
            return float(policy.provider_percentage), "vertical_default", True
        if policy is None:
            return default, "platform_legacy_default", True
        return None, "percentage_default_missing", False

    return ok([{
        "id":               str(c.id),
        "name":             c.name,
        "slug":             c.slug,
        "vertical_type":    c.vertical_type,
        "is_active":        c.is_active,
        # provider commission (migration 139)
        "commission_pct":   (None if c.vertical_type == "home_services" else
                              float(c.commission_pct) if c.commission_pct is not None else None),
        "effective_pct":    _resolution(c)[0],
        "effective_source": _resolution(c)[1],
        "is_percentage_commission_live": _resolution(c)[2],
        "using_default":    c.vertical_type == "home_services" or c.commission_pct is None,
        "default_pct":      default,
        "provider_model":   policy_by_key[c.vertical_type].provider_model if c.vertical_type in policy_by_key else None,
        "vertical_default_pct": (
            float(policy_by_key[c.vertical_type].provider_percentage)
            if c.vertical_type in policy_by_key and policy_by_key[c.vertical_type].provider_percentage is not None
            else None
        ),
        # customer charge / platform fee (migration 140) — NULL = 0%
        "customer_charge_pct": (None if c.vertical_type == "home_services" else
                                float(c.customer_charge_pct) if c.customer_charge_pct is not None else None),
    } for c in rows], _rid(r), ENGINE_ID)


class CategoryCommissionIn(BaseModel):
    commission_pct: Optional[Decimal] = None       # None clears -> falls back to default
    customer_charge_pct: Optional[Decimal] = None  # the customer-side platform fee


@router.get("/category-commission-rates/{category_id}", response_model=ApiResponse[dict],
            summary="Get the authoritative commission resolution for one category", tags=["Commission"])
async def get_category_commission_authority(
    category_id: uuid.UUID,
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_permission(P.FINANCE_READ)),
):
    """Read-only explanation of the rate the runtime will use.

    Category Detail deliberately consumes this endpoint instead of exposing
    another editor. Home Services has exactly one finance authority: its
    published Monetization policy. Legacy category overrides remain available
    only for other verticals that have not migrated to dedicated finance.
    """
    from app.engines.admin_catalog.models import ServiceCategory
    from app.engines.invoice_payment.constants import DEFAULT_COMMISSION_RATE
    from app.engines.vertical_catalog.models import Vertical
    from app.engines.vertical_monetization.models import VerticalMonetizationPolicy
    from sqlalchemy import select

    cat = await db.get(ServiceCategory, category_id)
    if not cat:
        raise ServiceOSException("NOT_FOUND", "Category not found.", status_code=404)

    policy = None
    if cat.vertical_type:
        vertical = (await db.execute(
            select(Vertical).where(Vertical.key == cat.vertical_type)
        )).scalar_one_or_none()
        if vertical:
            policy = (await db.execute(select(VerticalMonetizationPolicy).where(
                VerticalMonetizationPolicy.vertical_id == vertical.id,
                VerticalMonetizationPolicy.is_current.is_(True),
                VerticalMonetizationPolicy.status == "published",
            ))).scalar_one_or_none()

    is_hs = cat.vertical_type == "home_services"
    own = None if is_hs else (Decimal(str(cat.commission_pct)) if cat.commission_pct is not None else None)
    default = Decimal(str(policy.provider_percentage)) if (
        policy is not None and policy.provider_percentage is not None
    ) else None
    if policy is not None and policy.provider_model != "PERCENTAGE_COMMISSION":
        effective, source, live = None, "model_not_percentage", False
    elif is_hs and policy is None:
        effective, source, live = None, "policy_not_published", False
    elif own is not None:
        effective, source, live = own, "category_override", True
    elif default is not None:
        effective, source, live = default, "vertical_default", True
    elif policy is None:
        effective, source, live = Decimal(str(DEFAULT_COMMISSION_RATE)), "platform_legacy_default", True
    else:
        effective, source, live = None, "percentage_default_missing", False

    return ok({
        "category_id": str(cat.id),
        "category_name": cat.name,
        "vertical_key": cat.vertical_type,
        "provider_model": policy.provider_model if policy else None,
        "policy_version": policy.version_number if policy else None,
        "policy_published_at": policy.published_at.isoformat() if policy and policy.published_at else None,
        "category_override_pct": float(own) if own is not None else None,
        "vertical_default_pct": float(default) if default is not None else None,
        "effective_pct": float(effective) if effective is not None else None,
        "effective_source": source,
        "is_percentage_commission_live": live,
        "default_editor_path": (
            "/admin/home-services/finance?tab=monetization" if is_hs
            else "/admin/finance/vertical-monetization"
        ),
        "override_editor_path": None,
    }, _rid(r), ENGINE_ID)


@router.put("/category-commission-rates/{category_id}", response_model=ApiResponse[dict],
            summary="Set a category's commission rate and/or customer charge", tags=["Commission"])
async def set_category_commission_rate(
    category_id: uuid.UUID,
    body: CategoryCommissionIn,
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_permission(P.FINANCE_MONETIZATION_DRAFT)),
):
    from sqlalchemy import select
    from app.engines.admin_catalog.models import ServiceCategory
    from app.engines.vertical_catalog.models import Vertical, VerticalAuditLog
    fields = body.model_dump(exclude_unset=True)
    for key in ("commission_pct", "customer_charge_pct"):
        v = fields.get(key)
        if v is not None and not (Decimal("0") <= v <= Decimal("100")):
            raise ServiceOSException("VALIDATION_ERROR",
                f"{key} must be between 0 and 100.", status_code=422)
    cat = (await db.execute(
        select(ServiceCategory).where(ServiceCategory.id == category_id)
    )).scalar_one_or_none()
    if not cat:
        raise ServiceOSException("NOT_FOUND", "Category not found.", status_code=404)
    if cat.vertical_type == "home_services" and fields.keys() & {"commission_pct", "customer_charge_pct"}:
        raise ServiceOSException(
            "HOME_SERVICES_MONETIZATION_SINGLE_AUTHORITY",
            "Home Services provider and customer charges are configured only in Home Services Finance > Monetization.",
            status_code=409,
        )
    before = {
        "commission_pct": str(cat.commission_pct) if cat.commission_pct is not None else None,
        "customer_charge_pct": str(cat.customer_charge_pct) if cat.customer_charge_pct is not None else None,
    }
    # only touch the fields the caller actually sent (so setting one does not
    # clear the other)
    if "commission_pct" in fields:
        cat.commission_pct = fields["commission_pct"]
    if "customer_charge_pct" in fields:
        cat.customer_charge_pct = fields["customer_charge_pct"]
    vertical_id = None
    if cat.vertical_type:
        vertical_id = (await db.execute(
            select(Vertical.id).where(Vertical.key == cat.vertical_type)
        )).scalar_one_or_none()
    after = {
        "commission_pct": str(cat.commission_pct) if cat.commission_pct is not None else None,
        "customer_charge_pct": str(cat.customer_charge_pct) if cat.customer_charge_pct is not None else None,
    }
    db.add(VerticalAuditLog(
        vertical_id=vertical_id,
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        action_type="monetization.category_override.update",
        before_state={"category_id": str(cat.id), **before},
        after_state={"category_id": str(cat.id), **after},
        notes=f"Category monetization override updated for {cat.name}.",
    ))
    await db.commit()
    return ok({"id": str(category_id),
               "commission_pct": float(cat.commission_pct) if cat.commission_pct is not None else None,
               "customer_charge_pct": float(cat.customer_charge_pct) if cat.customer_charge_pct is not None else None,
               "using_default": cat.commission_pct is None}, _rid(r), ENGINE_ID)


@router.get("/catalog/categories/options", response_model=ApiResponse[list],
            summary="Searchable category options for dropdowns", tags=["Service Categories"])
async def category_options(r: Request,
                            q: str | None = Query(None),
                            vertical_type: str | None = Query(None),
                            status: str | None = Query(None),
                            db: AsyncSession = Depends(get_db),
                            u: UserContext = Depends(require_super_admin)):
    from sqlalchemy import select, or_
    from app.engines.admin_catalog.models import ServiceCategory
    stmt = select(ServiceCategory)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(
            ServiceCategory.name.ilike(like),
            ServiceCategory.slug.ilike(like),
            ServiceCategory.vertical_type.ilike(like),
        ))
    if vertical_type:
        stmt = stmt.where(ServiceCategory.vertical_type == vertical_type)
    if status == "active":
        stmt = stmt.where(ServiceCategory.is_active == True)
    elif status == "inactive":
        stmt = stmt.where(ServiceCategory.is_active == False)
    stmt = stmt.order_by(ServiceCategory.display_order, ServiceCategory.name).limit(200)
    rows = (await db.execute(stmt)).scalars().all()
    options = [{
        "id": str(c.id),
        "name": c.name,
        "slug": c.slug,
        "vertical_type": c.vertical_type,
        "status": "active" if c.is_active else "inactive",
    } for c in rows]
    return ok(options, _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/pricing-rules.
# Provider service prices live in tenant catalog setup; Home Services platform
# charges live in Home Services Finance.
async def list_pricing_rules(r: Request,
                              master_service_id: uuid.UUID | None = Query(None),
                              is_active: bool | None = Query(None),
                              q: str | None = Query(None),
                              brand_id: uuid.UUID | None = Query(None),
                              service_type_id: uuid.UUID | None = Query(None),
                              tier_id: uuid.UUID | None = Query(None),
                              city: str | None = Query(None),
                              zipcode: str | None = Query(None),
                              pricing_model: str | None = Query(None),
                              expiring_within_days: int | None = Query(None),
                              rule_status: str | None = Query(None),
                              page: int = Query(1, ge=1),
                              page_size: int = Query(50, ge=1, le=200),
                              sort_by: str = Query("priority"),
                              sort_dir: str = Query("desc"),
                              u: UserContext = Depends(require_super_admin),
                              s: AdminCatalogService = Depends(_svc)):
    """Real bug fixed: AdminCatalogService.list_pricing_rules() existed and was
    fully implemented, but NO router ever exposed it -- so GET
    /v1/admin/pricing-rules 404'd. Three super-admin surfaces call it via
    catalogApi.listPricingRules and therefore always rendered empty despite
    real rows existing in service_pricing_rules:
      * /admin/pricing-rules            (the Pricing Rules workspace itself)
      * /admin/home-services/completed-job-deduction
      * /admin/tenants/{id}             (Pricing tab)
    Signature mirrors the frontend client's query params exactly, so no
    frontend change is needed."""
    return ok(await s.list_pricing_rules(
        master_service_id=master_service_id, is_active=is_active, q=q,
        brand_id=brand_id, service_type_id=service_type_id, tier_id=tier_id,
        city=city, zipcode=zipcode, pricing_model=pricing_model,
        expiring_within_days=expiring_within_days, rule_status=rule_status,
        page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir,
    ), _rid(r), ENGINE_ID)


# ── Service Pricing Rules: the rest of the workspace ────────────────────────
# The GET above was exposed on its own; every other operation the Pricing Rules
# workspace performs stayed unrouted even though AdminCatalogService implements
# all of them. So the page could LIST rules and nothing else — create, edit,
# delete, preview, summary, export and conflict-check every 404'd. Same class of
# bug the docstring above describes, just left half-finished.

# Retired route: GET /v1/admin/pricing-rules/summary
async def pricing_rules_summary(r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_pricing_rules_summary(), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/pricing-rules/export
async def export_pricing_rules(r: Request,
                                master_service_id: uuid.UUID | None = Query(None),
                                is_active: bool | None = Query(None),
                                q: str | None = Query(None),
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    rows = await s.export_pricing_rules(
        master_service_id=master_service_id, is_active=is_active, q=q)
    return ok({"rows": rows, "count": len(rows)}, _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/pricing-rules/preview
async def preview_pricing(r: Request, payload: dict = Body(...),
                          u: UserContext = Depends(require_super_admin),
                          s: AdminCatalogService = Depends(_svc)):
    return ok(await s.preview_pricing(payload), _rid(r), ENGINE_ID)


# Retired route: POST /v1/admin/pricing-rules
async def create_pricing_rule(r: Request, payload: dict = Body(...),
                              u: UserContext = Depends(require_super_admin),
                              s: AdminCatalogService = Depends(_svc)):
    return ok(await s.create_pricing_rule(payload), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/pricing-rules/{rule_id}
async def get_pricing_rule(rule_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_pricing_rule(rule_id), _rid(r), ENGINE_ID)


# Retired route: PUT /v1/admin/pricing-rules/{rule_id}
async def update_pricing_rule(rule_id: uuid.UUID, r: Request, payload: dict = Body(...),
                              u: UserContext = Depends(require_super_admin),
                              s: AdminCatalogService = Depends(_svc)):
    return ok(await s.update_pricing_rule(rule_id, payload), _rid(r), ENGINE_ID)


# Retired route: DELETE /v1/admin/pricing-rules/{rule_id}
async def delete_pricing_rule(rule_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_pricing_rule(rule_id), _rid(r), ENGINE_ID)


# Retired route: DELETE /v1/admin/pricing-rules/{rule_id}/hard-delete
async def hard_delete_pricing_rule(rule_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    return ok(await s.hard_delete_pricing_rule(rule_id), _rid(r), ENGINE_ID)


# Retired route: GET /v1/admin/pricing-rules/{rule_id}/conflicts
async def pricing_rule_conflicts(rule_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_pricing_rule_conflicts(rule_id), _rid(r), ENGINE_ID)


@router.post("/service-categories", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create service category (DEPRECATED -- accepts legacy Brand/Type/pricing "
                      "fields for backward compatibility; use /business-verticals for new callers)",
             tags=["Service Categories"])
async def create_category(r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_category(body), _rid(r), ENGINE_ID)


@router.post("/business-verticals", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create a Business Vertical (canonical -- migration 160; rejects "
                      "Brand/Type/Schedule/Address/pricing fields, which belong to the "
                      "Job-Type Blueprint)",
             tags=["Service Categories"])
async def create_business_vertical(r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_category_canonical(body), _rid(r), ENGINE_ID)


@router.get("/service-categories/{category_id}", response_model=ApiResponse[dict],
            summary="Get service category", tags=["Service Categories"])
async def get_category(category_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_super_admin),
                       s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_category(category_id), _rid(r), ENGINE_ID)


@router.put("/service-categories/{category_id}", response_model=ApiResponse[dict],
            summary="Update service category", tags=["Service Categories"])
async def update_category(category_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_category(category_id, body), _rid(r), ENGINE_ID)


@router.delete("/service-categories/{category_id}", response_model=ApiResponse[dict],
               summary="Deactivate / delete service category", tags=["Service Categories"])
async def delete_category(category_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_category(category_id), _rid(r), ENGINE_ID)


@router.delete("/service-categories/{category_id}/hard-delete", response_model=ApiResponse[dict],
               summary="Permanently delete a category (only if no master services reference it)",
               tags=["Service Categories"])
async def hard_delete_category(category_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    return ok(await s.hard_delete_category(category_id), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# MASTER SERVICES
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# SERVICE GROUPS (Sprint 38)
# ═══════════════════════════════════════════════════════════════

@router.get("/service-groups/summary", response_model=ApiResponse[dict],
            summary="Service groups summary cards", tags=["Service Groups"])
async def service_groups_summary(r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_service_groups_summary(), _rid(r), ENGINE_ID)


@router.get("/service-groups/export", response_model=ApiResponse[dict],
            summary="Export service groups", tags=["Service Groups"])
async def export_service_groups(r: Request,
                                 category_id: uuid.UUID | None = Query(None),
                                 status: str | None = Query(None),
                                 retired: bool = Query(False),
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    rows = await s.export_service_groups(category_id=category_id, status=status, retired=retired)
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), ENGINE_ID)


@router.get("/service-groups", response_model=ApiResponse[dict], summary="List service groups",
            tags=["Service Groups"])
async def list_service_groups(r: Request,
                               q: str | None = Query(None),
                               category_id: uuid.UUID | None = Query(None),
                               status: str | None = Query(None),
                               has_services: bool | None = Query(None),
                               retired: bool = Query(False),
                               sort_by: str = Query("display_order"),
                               sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
                               limit: int = Query(50, ge=1, le=100),
                               offset: int = Query(0, ge=0),
                               u: UserContext = Depends(require_super_admin),
                               s: AdminCatalogService = Depends(_svc)):
    return ok(
        await s.list_service_groups_enterprise(
            q=q, category_id=category_id, status=status,
            has_services=has_services, retired=retired, sort_by=sort_by,
            sort_dir=sort_dir, limit=limit, offset=offset,
        ),
        _rid(r), ENGINE_ID,
    )


@router.post("/service-groups", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create service group", tags=["Service Groups"])
async def create_service_group(r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_service_group(body), _rid(r), ENGINE_ID)


@router.post("/service-groups/bulk-status", response_model=ApiResponse[dict],
             summary="Bulk activate or deactivate service groups", tags=["Service Groups"])
async def bulk_service_group_status(r: Request,
                                     u: UserContext = Depends(require_super_admin),
                                     s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    ids = [uuid.UUID(str(value)) for value in body.get("ids", [])]
    return ok(await s.bulk_service_group_status(ids, body.get("action", ""), body.get("reason")), _rid(r), ENGINE_ID)


@router.get("/service-groups/{group_id}", response_model=ApiResponse[dict],
            summary="Get service group", tags=["Service Groups"])
async def get_service_group(group_id: uuid.UUID, r: Request,
                             include_retired: bool = Query(False),
                             u: UserContext = Depends(require_super_admin),
                             s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_service_group_enterprise(group_id, include_retired=include_retired), _rid(r), ENGINE_ID)


@router.get("/service-groups/{group_id}/audit", response_model=ApiResponse[dict],
            summary="Service group audit trail", tags=["Service Groups"])
async def get_service_group_audit(group_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_service_group_audit(group_id), _rid(r), ENGINE_ID)


@router.put("/service-groups/{group_id}", response_model=ApiResponse[dict],
            summary="Update service group", tags=["Service Groups"])
async def update_service_group(group_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_service_group(group_id, body), _rid(r), ENGINE_ID)


@router.delete("/service-groups/{group_id}", response_model=ApiResponse[dict],
               summary="Deprecated: use the audited retire endpoint", deprecated=True,
               tags=["Service Groups"])
async def delete_service_group(group_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    raise ServiceOSException(
        "AUDITED_RETIRE_REQUIRED",
        "Use POST /service-groups/{id}/archive with a retirement reason.",
        status_code=409,
    )


@router.post("/service-groups/{group_id}/activate", response_model=ApiResponse[dict],
             summary="Activate service group", tags=["Service Groups"])
async def activate_service_group(group_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.activate_service_group(group_id), _rid(r), ENGINE_ID)


@router.post("/service-groups/{group_id}/deactivate", response_model=ApiResponse[dict],
             summary="Deactivate service group", tags=["Service Groups"])
async def deactivate_service_group(group_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    return ok(await s.deactivate_service_group(group_id), _rid(r), ENGINE_ID)


@router.post("/service-groups/{group_id}/archive", response_model=ApiResponse[dict],
             summary="Archive service group", tags=["Service Groups"])
async def archive_service_group(group_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.archive_service_group(group_id, body.get("reason", "")), _rid(r), ENGINE_ID)


@router.post("/service-groups/{group_id}/restore", response_model=ApiResponse[dict],
             summary="Restore retired service group as inactive", tags=["Service Groups"])
async def restore_service_group(group_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.restore_service_group(group_id, body.get("reason", "")), _rid(r), ENGINE_ID)


@router.get("/master-services/summary", response_model=ApiResponse[dict],
            summary="Master services summary cards", tags=["Master Services"])
async def master_services_summary(r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_master_services_summary(), _rid(r), ENGINE_ID)


@router.get("/master-services/export", response_model=ApiResponse[dict],
            summary="Export master services", tags=["Master Services"])
async def export_master_services(r: Request,
                                  category_id: uuid.UUID | None = Query(None),
                                  service_group_id: uuid.UUID | None = Query(None),
                                  job_type: str | None = Query(None),
                                  is_active: bool | None = Query(None),
                                  retired: bool = Query(False),
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    rows = await s.export_master_services(
        category_id=category_id, service_group_id=service_group_id,
        job_type=job_type, is_active=is_active, retired=retired,
    )
    return ok({"rows": rows, "count": len(rows), "format": "json"}, _rid(r), ENGINE_ID)


@router.get("/master-services", response_model=ApiResponse[dict], summary="List master services",
            tags=["Master Services"])
async def list_master_services(r: Request,
                                q: str | None = Query(None),
                                category_id: uuid.UUID | None = Query(None),
                                service_group_id: uuid.UUID | None = Query(None),
                                job_type: str | None = Query(None),
                                pricing_model: str | None = Query(None),
                                is_active: bool | None = Query(None),
                                retired: bool = Query(False),
                                readiness: str | None = Query(None),
                                has_providers: bool | None = Query(None),
                                sort_by: str = Query("display_order"),
                                sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
                                limit: int = Query(50, ge=1, le=100),
                                offset: int = Query(0, ge=0),
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    return ok(
        await s.list_master_services_enterprise(
            q=q, category_id=category_id, service_group_id=service_group_id,
            job_type=job_type, pricing_model=pricing_model,
            is_active=is_active, retired=retired, readiness=readiness,
            has_providers=has_providers, sort_by=sort_by, sort_dir=sort_dir,
            limit=limit, offset=offset,
        ),
        _rid(r), ENGINE_ID,
    )


@router.post("/master-services", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create master service (DEPRECATED -- accepts a legacy scalar job_type/"
                      "pricing_model/prices/requirement flags for backward compatibility; use "
                      "/master-services-v2 for new callers)",
             tags=["Master Services"])
async def create_master_service(r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_master_service(body), _rid(r), ENGINE_ID)


@router.post("/master-services-v2", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create a Master Service (canonical -- migration 160; job-type-agnostic, "
                      "rejects job_type/pricing_model/prices/Brand/Type/workflow requirement "
                      "fields, which belong to the Job-Type Blueprint added afterward)",
             tags=["Master Services"])
async def create_master_service_v2(r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_master_service_canonical(body), _rid(r), ENGINE_ID)


@router.post("/master-services/bulk-status", response_model=ApiResponse[dict],
             summary="Bulk activate or deactivate master services", tags=["Master Services"])
async def bulk_master_service_status(r: Request,
                                     u: UserContext = Depends(require_super_admin),
                                     s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    ids = [uuid.UUID(str(value)) for value in body.get("ids", [])]
    return ok(await s.bulk_master_service_status(ids, body.get("action", "")), _rid(r), ENGINE_ID)


@router.get("/master-services/{service_id}", response_model=ApiResponse[dict],
            summary="Get master service", tags=["Master Services"])
async def get_master_service(service_id: uuid.UUID, r: Request,
                              include_retired: bool = Query(False),
                              u: UserContext = Depends(require_super_admin),
                              s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_master_service_enterprise(service_id, include_retired), _rid(r), ENGINE_ID)


@router.get("/master-services/{service_id}/audit", response_model=ApiResponse[dict],
            summary="Master service audit history", tags=["Master Services"])
async def master_service_audit(service_id: uuid.UUID, r: Request,
                               limit: int = Query(100, ge=1, le=200),
                               u: UserContext = Depends(require_super_admin),
                               s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_master_service_audit(service_id, limit), _rid(r), ENGINE_ID)


@router.put("/master-services/{service_id}", response_model=ApiResponse[dict],
            summary="Update master service", tags=["Master Services"])
async def update_master_service(service_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    actor_id = uuid.UUID(u.user_id) if u.user_id else None
    return ok(await s.update_master_service(service_id, body, actor_id), _rid(r), ENGINE_ID)


@router.delete("/master-services/{service_id}", response_model=ApiResponse[dict],
               summary="Deprecated: use audited retire endpoint", tags=["Master Services"])
async def delete_master_service(service_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    raise ServiceOSException(
        "AUDITED_RETIRE_REQUIRED",
        "Use POST /master-services/{id}/archive with a retirement reason.",
        status_code=410,
    )


@router.delete("/master-services/{service_id}/hard-delete", response_model=ApiResponse[dict],
               summary="Permanently delete a master service (only if no pricing rules reference it)",
               tags=["Master Services"])
async def hard_delete_master_service(service_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: AdminCatalogService = Depends(_svc)):
    raise ServiceOSException(
        "PERMANENT_DELETE_DISABLED",
        "Permanent deletion is disabled. Retire the master service to preserve catalog and booking history.",
        status_code=410,
    )


@router.post("/master-services/{service_id}/activate", response_model=ApiResponse[dict],
             summary="Activate master service", tags=["Master Services"])
async def activate_master_service(service_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    return ok(await s.activate_master_service(service_id), _rid(r), ENGINE_ID)


@router.post("/master-services/{service_id}/deactivate", response_model=ApiResponse[dict],
             summary="Deactivate master service", tags=["Master Services"])
async def deactivate_master_service(service_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_super_admin),
                                     s: AdminCatalogService = Depends(_svc)):
    return ok(await s.deactivate_master_service(service_id), _rid(r), ENGINE_ID)


@router.post("/master-services/{service_id}/archive", response_model=ApiResponse[dict],
             summary="Archive master service", tags=["Master Services"])
async def archive_master_service(service_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.archive_master_service(service_id, body.get("reason", "")), _rid(r), ENGINE_ID)


@router.post("/master-services/{service_id}/restore", response_model=ApiResponse[dict],
             summary="Restore retired master service as inactive", tags=["Master Services"])
async def restore_master_service(service_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.restore_master_service(service_id, body.get("reason", "")), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# SERVICE TYPES
# ═══════════════════════════════════════════════════════════════

@router.get("/service-types", response_model=ApiResponse[dict], summary="List service types",
            tags=["Service Types"])
async def list_service_types(r: Request,
                              category_id: uuid.UUID | None = Query(None),
                              is_active: bool | None = Query(None),
                              master_service_id: uuid.UUID | None = Query(None,
                                  description="Exclude Types already attached to a different service"),
                              u: UserContext = Depends(require_super_admin),
                              s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_service_types(category_id, is_active, master_service_id), _rid(r), ENGINE_ID)


@router.post("/service-types", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create service type", tags=["Service Types"])
async def create_service_type(r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_service_type(body), _rid(r), ENGINE_ID)


@router.put("/service-types/{type_id}", response_model=ApiResponse[dict],
            summary="Update service type", tags=["Service Types"])
async def update_service_type(type_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_service_type(type_id, body), _rid(r), ENGINE_ID)


@router.delete("/service-types/{type_id}", response_model=ApiResponse[dict],
               summary="Deactivate service type", tags=["Service Types"])
async def delete_service_type(type_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_service_type(type_id), _rid(r), ENGINE_ID)


@router.delete("/service-types/{type_id}/hard-delete", response_model=ApiResponse[dict],
               summary="Permanently delete a service type", tags=["Service Types"])
async def hard_delete_service_type(type_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    return ok(await s.hard_delete_service_type(type_id), _rid(r), ENGINE_ID)


# NOTE: /v1/admin/brands GET/POST/DELETE are handled by brand_admin_router (Sprint 34D)
# to support full pagination, merge, normalise, and template features.
# The Sprint 3 stubs below were removed to avoid duplicate route conflict.

# ═══════════════════════════════════════════════════════════════
# TYPE / BRAND MAPPINGS
# ═══════════════════════════════════════════════════════════════

@router.get("/master-services/{service_id}/types", response_model=ApiResponse[dict],
            summary="List type mappings for service", tags=["Service Type Mapping"])
async def list_service_type_mappings(service_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_service_type_mappings(service_id), _rid(r), ENGINE_ID)


@router.post("/master-services/{service_id}/types", response_model=ApiResponse[dict],
             status_code=status.HTTP_201_CREATED,
             summary="Map service type to master service", tags=["Service Type Mapping"])
async def map_service_type(service_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.map_service_type(service_id, body), _rid(r), ENGINE_ID)


@router.delete("/master-services/{service_id}/types/{mapping_id}", response_model=ApiResponse[dict],
               summary="Remove type mapping from service", tags=["Service Type Mapping"])
async def remove_service_type_mapping(service_id: uuid.UUID, mapping_id: uuid.UUID, r: Request,
                                       u: UserContext = Depends(require_super_admin),
                                       s: AdminCatalogService = Depends(_svc)):
    return ok(await s.remove_service_type_mapping(service_id, mapping_id), _rid(r), ENGINE_ID)


@router.get("/master-services/{service_id}/brands", response_model=ApiResponse[dict],
            summary="List brand mappings for service", tags=["Brand Mapping"])
async def list_service_brand_mappings(service_id: uuid.UUID, r: Request,
                                       u: UserContext = Depends(require_super_admin),
                                       s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_service_brand_mappings(service_id), _rid(r), ENGINE_ID)


@router.get("/master-services/{service_id}/issues", response_model=ApiResponse[dict],
            summary="List issue-type mappings for service", tags=["Issue Type Mapping"])
async def list_service_issue_mappings(service_id: uuid.UUID, r: Request,
                                       job_type_id: uuid.UUID | None = Query(None),
                                       u: UserContext = Depends(require_super_admin),
                                       s: ServiceOptionService = Depends(_opt_svc)):
    # The workspace contract is an object so it can evolve with pagination and
    # summary metadata. Returning the service's raw list here contradicted the
    # declared ApiResponse[dict] and caused FastAPI response validation to turn
    # otherwise valid problem rows into an HTTP 500.
    return ok({"issues": await s.list_service_issue_mappings(service_id, job_type_id)},
              _rid(r), ENGINE_ID)


@router.post("/master-services/{service_id}/brands", response_model=ApiResponse[dict],
             status_code=status.HTTP_201_CREATED,
             summary="Map brand to master service", tags=["Brand Mapping"])
async def map_service_brand(service_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.map_service_brand(service_id, body), _rid(r), ENGINE_ID)


@router.delete("/master-services/{service_id}/brands/{mapping_id}", response_model=ApiResponse[dict],
               summary="Remove brand mapping from service", tags=["Brand Mapping"])
async def remove_service_brand_mapping(service_id: uuid.UUID, mapping_id: uuid.UUID, r: Request,
                                        u: UserContext = Depends(require_super_admin),
                                        s: AdminCatalogService = Depends(_svc)):
    return ok(await s.remove_service_brand_mapping(service_id, mapping_id), _rid(r), ENGINE_ID)


# Pricing Rules endpoints removed (2026-07) -- this platform is provider-set-
# price; admin no longer defines min/max/base price boundaries or previews
# them. The ServicePricingRule model/table and its service methods
# (admin_catalog/service.py) remain in place (no destructive migration),
# only the API surface reachable by any client was removed.


# ═══════════════════════════════════════════════════════════════
# MASTER ISSUE TYPES  (Sprint 34C)
# ═══════════════════════════════════════════════════════════════

@router.get("/issue-types", response_model=ApiResponse[dict],
            summary="List master issue types", tags=["Master Issue Types"])
async def list_issue_types(r: Request,
                            category_id: uuid.UUID | None = Query(None),
                            master_service_id: uuid.UUID | None = Query(None),
                            is_active: bool | None = Query(None),
                            u: UserContext = Depends(require_super_admin),
                            s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_issue_types(category_id, master_service_id, is_active), _rid(r), ENGINE_ID)


@router.post("/issue-types", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create master issue type", tags=["Master Issue Types"])
async def create_issue_type(r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_issue_type(body), _rid(r), ENGINE_ID)


@router.get("/issue-types/{issue_type_id}", response_model=ApiResponse[dict],
            summary="Get master issue type", tags=["Master Issue Types"])
async def get_issue_type(issue_type_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_issue_type(issue_type_id), _rid(r), ENGINE_ID)


@router.put("/issue-types/{issue_type_id}", response_model=ApiResponse[dict],
            summary="Update master issue type", tags=["Master Issue Types"])
async def update_issue_type(issue_type_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_issue_type(issue_type_id, body), _rid(r), ENGINE_ID)


@router.delete("/issue-types/{issue_type_id}", response_model=ApiResponse[dict],
               summary="Deactivate master issue type", tags=["Master Issue Types"])
async def delete_issue_type(issue_type_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_issue_type(issue_type_id), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# MASTER SERVICE OPTIONS  (Sprint 34C)
# ═══════════════════════════════════════════════════════════════

@router.get("/service-options", response_model=ApiResponse[dict],
            summary="List master service options", tags=["Master Service Options"])
async def list_service_options(r: Request,
                                status_filter: str | None = Query(None, alias="status"),
                                category_id: uuid.UUID | None = Query(None),
                                master_service_id: uuid.UUID | None = Query(None),
                                option_group_id: uuid.UUID | None = Query(None),
                                option_type: str | None = Query(None),
                                mapped: bool | None = Query(None),
                                is_active: bool | None = Query(None),
                                search: str | None = Query(None),
                                page: int = Query(1, ge=1),
                                page_size: int = Query(50, ge=1, le=200),
                                u: UserContext = Depends(require_super_admin),
                                s: ServiceOptionService = Depends(_opt_svc)):
    if is_active is not None and status_filter is None:
        status_filter = "active" if is_active else "inactive"
    return ok(await s.list_service_options(
        status_filter, category_id, master_service_id, option_group_id,
        option_type, mapped, search, page, page_size), _rid(r))


@router.post("/service-options", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create master service option", tags=["Master Service Options"])
async def create_service_option(r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_opt_svc)):
    return ok(await s.create_service_option(await r.json()), _rid(r))


@router.get("/service-options/summary", response_model=ApiResponse[dict],
            summary="Service options summary counts", tags=["Master Service Options"])
async def get_service_options_summary(r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: ServiceOptionService = Depends(_opt_svc)):
    return ok(await s.list_service_options_summary(), _rid(r))


@router.get("/service-options/{option_id}", response_model=ApiResponse[dict],
            summary="Get master service option", tags=["Master Service Options"])
async def get_service_option(option_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: ServiceOptionService = Depends(_opt_svc)):
    return ok(await s.get_service_option(option_id), _rid(r))


@router.put("/service-options/{option_id}", response_model=ApiResponse[dict],
            summary="Update master service option", tags=["Master Service Options"])
async def update_service_option(option_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_opt_svc)):
    return ok(await s.update_service_option(option_id, await r.json()), _rid(r))


@router.delete("/service-options/{option_id}", response_model=ApiResponse[dict],
               summary="Deactivate master service option", tags=["Master Service Options"])
async def delete_service_option(option_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_service_option(option_id), _rid(r), ENGINE_ID)


# Canonical lifecycle routes live on this router too.  The separate Sprint 34E
# option router used to be mounted beside these CRUD routes with the exact same
# paths, leaving two handlers for every list/get/write and duplicate OpenAPI
# operation IDs.  Keep one public route owner while preserving the explicit
# lifecycle actions used by the enterprise setup UI.
@router.post("/service-options/{option_id}/activate", response_model=ApiResponse[dict],
             summary="Activate master service option", tags=["Master Service Options"])
async def activate_service_option(option_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: ServiceOptionService = Depends(_opt_svc)):
    return ok(await s.activate_service_option(option_id), _rid(r), ENGINE_ID)


@router.post("/service-options/{option_id}/deactivate", response_model=ApiResponse[dict],
             summary="Deactivate master service option", tags=["Master Service Options"])
async def deactivate_service_option(option_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: ServiceOptionService = Depends(_opt_svc)):
    return ok(await s.deactivate_service_option(option_id), _rid(r), ENGINE_ID)


@router.post("/service-options/{option_id}/archive", response_model=ApiResponse[dict],
             summary="Archive master service option", tags=["Master Service Options"])
async def archive_service_option(option_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: ServiceOptionService = Depends(_opt_svc)):
    return ok(await s.archive_service_option(option_id), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# MASTER WORKFLOW TEMPLATES  (Sprint 34C, upgraded — P0 Enterprise Workflow Engine)
# ═══════════════════════════════════════════════════════════════

@router.api_route("/workflow-templates", methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                  response_model=ApiResponse[dict], include_in_schema=False)
@router.api_route("/workflow-templates/{retired_path:path}",
                  methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                  response_model=ApiResponse[dict], include_in_schema=False)
async def retired_workflow_templates_api(retired_path: str = "",
                                         u: UserContext = Depends(require_super_admin)):
    _ = (retired_path, u)
    raise ServiceOSException(
        "WORKFLOW_TEMPLATES_RETIRED",
        "Workflow templates are retired. Configure the runtime job workflow in "
        "Home Services -> Service Catalog -> Catalog Workspace -> Workflow "
        "(service_job_workflow).",
        status_code=410,
    )


@router.get("/workflow-templates/summary", response_model=ApiResponse[dict],
            summary="Workflow templates summary cards", tags=["Master Workflow Templates"])
async def get_workflow_templates_summary(r: Request,
                                          u: UserContext = Depends(require_super_admin),
                                          s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_workflow_templates_summary(), _rid(r), ENGINE_ID)


@router.get("/workflow-templates/export", response_model=ApiResponse[dict],
            summary="Export workflow templates", tags=["Master Workflow Templates"])
async def export_workflow_templates(r: Request,
                                     u: UserContext = Depends(require_super_admin),
                                     s: AdminCatalogService = Depends(_svc)):
    data = await s.list_workflow_templates(limit=10000)
    return ok({"rows": data["workflow_templates"], "count": len(data["workflow_templates"]), "format": "json"}, _rid(r), ENGINE_ID)


@router.post("/workflow-templates/seed-defaults/preview", response_model=ApiResponse[dict],
             summary="Preview Home Services default workflow seed", tags=["Master Workflow Templates"])
async def seed_workflow_defaults_preview(r: Request,
                                          u: UserContext = Depends(require_super_admin),
                                          s: AdminCatalogService = Depends(_svc)):
    return ok(await s.seed_workflow_defaults_preview(), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/seed-defaults", response_model=ApiResponse[dict],
             summary="Seed Home Services default workflows", tags=["Master Workflow Templates"])
async def seed_workflow_defaults(r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.seed_workflow_defaults(), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/preview-runtime", response_model=ApiResponse[dict],
             summary="Preview resolved runtime workflow for a service scope", tags=["Master Workflow Templates"])
async def preview_workflow_runtime(r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.preview_workflow_runtime(
        category_id=uuid.UUID(str(body["category_id"])) if body.get("category_id") else None,
        master_service_id=uuid.UUID(str(body["master_service_id"])) if body.get("master_service_id") else None,
        service_type_id=uuid.UUID(str(body["service_type_id"])) if body.get("service_type_id") else None,
        tenant_id=uuid.UUID(str(body["tenant_id"])) if body.get("tenant_id") else None,
    ), _rid(r), ENGINE_ID)


async def list_workflow_templates(r: Request,
                                   category_id: uuid.UUID | None = Query(None),
                                   master_service_id: uuid.UUID | None = Query(None),
                                   workflow_type: str | None = Query(None),
                                   is_active: bool | None = Query(None),
                                   status_: str | None = Query(None, alias="status"),
                                   q: str | None = Query(None),
                                   readiness: str | None = Query(None),
                                   page: int = Query(1, ge=1),
                                   limit: int = Query(50, ge=1, le=200),
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_workflow_templates(category_id, master_service_id, workflow_type, is_active,
                                              status_, q, readiness, page, limit), _rid(r), ENGINE_ID)


async def create_workflow_template(r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_workflow_template(body), _rid(r), ENGINE_ID)


@router.get("/workflow-templates/{template_id}", response_model=ApiResponse[dict],
            summary="Get master workflow template", tags=["Master Workflow Templates"])
async def get_workflow_template(template_id: uuid.UUID, r: Request,
                                 u: UserContext = Depends(require_super_admin),
                                 s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_workflow_template(template_id), _rid(r), ENGINE_ID)


@router.put("/workflow-templates/{template_id}", response_model=ApiResponse[dict],
            summary="Update master workflow template", tags=["Master Workflow Templates"])
async def update_workflow_template(template_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_workflow_template(template_id, body), _rid(r), ENGINE_ID)


@router.delete("/workflow-templates/{template_id}", response_model=ApiResponse[dict],
               summary="Deactivate master workflow template", tags=["Master Workflow Templates"])
async def delete_workflow_template(template_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_workflow_template(template_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/clone", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Clone workflow template as new draft", tags=["Master Workflow Templates"])
async def clone_workflow_template(template_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    return ok(await s.clone_workflow_template(template_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/new-version", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create new draft version of an existing workflow template", tags=["Master Workflow Templates"])
async def create_workflow_new_version(template_id: uuid.UUID, r: Request,
                                       u: UserContext = Depends(require_super_admin),
                                       s: AdminCatalogService = Depends(_svc)):
    return ok(await s.create_new_version(template_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/activate", response_model=ApiResponse[dict],
             summary="Activate workflow template (blocked unless valid)", tags=["Master Workflow Templates"])
async def activate_workflow_template(template_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: AdminCatalogService = Depends(_svc)):
    return ok(await s.activate_workflow_template(template_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/deactivate", response_model=ApiResponse[dict],
             summary="Deactivate workflow template", tags=["Master Workflow Templates"])
async def deactivate_workflow_template(template_id: uuid.UUID, r: Request,
                                        u: UserContext = Depends(require_super_admin),
                                        s: AdminCatalogService = Depends(_svc)):
    return ok(await s.deactivate_workflow_template(template_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/validate", response_model=ApiResponse[dict],
             summary="Validate workflow template structure", tags=["Master Workflow Templates"])
async def validate_workflow_template(template_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: AdminCatalogService = Depends(_svc)):
    return ok(await s.validate_workflow_template(template_id), _rid(r), ENGINE_ID)


@router.get("/workflow-templates/{template_id}/readiness", response_model=ApiResponse[dict],
            summary="Get runtime readiness of workflow template", tags=["Master Workflow Templates"])
async def get_workflow_readiness(template_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_workflow_readiness(template_id), _rid(r), ENGINE_ID)


# ── Steps ──────────────────────────────────────────────────────────────────────

@router.get("/workflow-templates/{template_id}/steps", response_model=ApiResponse[dict],
            summary="List workflow steps", tags=["Master Workflow Templates"])
async def list_workflow_steps(template_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: AdminCatalogService = Depends(_svc)):
    row = await s.get_workflow_template(template_id)
    return ok({"steps": row["steps"], "total": len(row["steps"])}, _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/steps", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Add workflow step", tags=["Master Workflow Templates"])
async def add_workflow_step(template_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.add_step(template_id, body), _rid(r), ENGINE_ID)


@router.put("/workflow-templates/{template_id}/steps/{step_id}", response_model=ApiResponse[dict],
            summary="Update workflow step", tags=["Master Workflow Templates"])
async def update_workflow_step(template_id: uuid.UUID, step_id: str, r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_step(template_id, step_id, body), _rid(r), ENGINE_ID)


@router.delete("/workflow-templates/{template_id}/steps/{step_id}", response_model=ApiResponse[dict],
               summary="Delete workflow step", tags=["Master Workflow Templates"])
async def delete_workflow_step(template_id: uuid.UUID, step_id: str, r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_step(template_id, step_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/steps/reorder", response_model=ApiResponse[dict],
             summary="Reorder workflow steps", tags=["Master Workflow Templates"])
async def reorder_workflow_steps(template_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.reorder_steps(template_id, body.get("step_ids", [])), _rid(r), ENGINE_ID)


# ── Transitions ─────────────────────────────────────────────────────────────────

@router.get("/workflow-templates/{template_id}/transitions", response_model=ApiResponse[dict],
            summary="List workflow transitions", tags=["Master Workflow Templates"])
async def list_workflow_transitions(template_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_super_admin),
                                     s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_transitions(template_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/transitions", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Add workflow transition", tags=["Master Workflow Templates"])
async def add_workflow_transition(template_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.add_transition(template_id, body), _rid(r), ENGINE_ID)


@router.put("/workflow-templates/{template_id}/transitions/{transition_id}", response_model=ApiResponse[dict],
            summary="Update workflow transition", tags=["Master Workflow Templates"])
async def update_workflow_transition(template_id: uuid.UUID, transition_id: str, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.update_transition(template_id, transition_id, body), _rid(r), ENGINE_ID)


@router.delete("/workflow-templates/{template_id}/transitions/{transition_id}", response_model=ApiResponse[dict],
               summary="Delete workflow transition", tags=["Master Workflow Templates"])
async def delete_workflow_transition(template_id: uuid.UUID, transition_id: str, r: Request,
                                      u: UserContext = Depends(require_super_admin),
                                      s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_transition(template_id, transition_id), _rid(r), ENGINE_ID)


# ── Service mappings ────────────────────────────────────────────────────────────

@router.get("/workflow-templates/{template_id}/mappings", response_model=ApiResponse[dict],
            summary="List workflow service mappings", tags=["Master Workflow Templates"])
async def list_workflow_mappings(template_id: uuid.UUID, r: Request,
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_workflow_mappings(template_id), _rid(r), ENGINE_ID)


@router.post("/workflow-templates/{template_id}/mappings", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create workflow service mapping", tags=["Master Workflow Templates"])
async def create_workflow_mapping(template_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.create_workflow_mapping(template_id, body), _rid(r), ENGINE_ID)


@router.delete("/workflow-templates/{template_id}/mappings/{mapping_id}", response_model=ApiResponse[dict],
               summary="Delete workflow service mapping", tags=["Master Workflow Templates"])
async def delete_workflow_mapping(template_id: uuid.UUID, mapping_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_super_admin),
                                   s: AdminCatalogService = Depends(_svc)):
    return ok(await s.delete_workflow_mapping(template_id, mapping_id), _rid(r), ENGINE_ID)


# ── Audit (reuses Sprint 34C master_data_audit_log) ─────────────────────────────

@router.get("/workflow-templates/{template_id}/audit-logs", response_model=ApiResponse[dict],
            summary="Workflow template audit logs", tags=["Master Workflow Templates"])
async def get_workflow_template_audit_logs(template_id: uuid.UUID, r: Request,
                                            u: UserContext = Depends(require_super_admin),
                                            s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_master_data_audit(entity_type="master_workflow_template", entity_id=template_id),
              _rid(r), ENGINE_ID)


@router.get("/workflows/audit-logs", response_model=ApiResponse[dict],
            summary="All workflow-related audit logs", tags=["Master Workflow Templates"])
async def get_workflows_audit_logs(r: Request,
                                    u: UserContext = Depends(require_super_admin),
                                    s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_master_data_audit(entity_type="master_workflow_template"), _rid(r), ENGINE_ID)


# ═══════════════════════════════════════════════════════════════
# MASTER DATA AUDIT LOG  (Sprint 34C)
# ═══════════════════════════════════════════════════════════════

@router.get("/master-data-audit", response_model=ApiResponse[dict],
            summary="List master data audit log", tags=["Master Data Audit"])
async def list_master_data_audit(r: Request,
                                  entity_type: str | None = Query(None),
                                  entity_id: uuid.UUID | None = Query(None),
                                  limit: int = Query(50, ge=1, le=200),
                                  u: UserContext = Depends(require_super_admin),
                                  s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_master_data_audit(entity_type, entity_id, limit), _rid(r), ENGINE_ID)


# The retired master_workflow_templates handlers remain below the 410 guard for
# migration/audit compatibility, but should not appear as production API
# surface area. Runtime workflow authoring is the Job-Type Blueprint router.
for _route in router.routes:
    _path = getattr(_route, "path", "")
    if (
        (_path.startswith("/v1/admin/workflow-templates") or _path.startswith("/workflow-templates"))
        and getattr(_route, "name", "") != "retired_workflow_templates_api"
    ):
        _route.include_in_schema = False
