"""Automatic Customer Price Options — admin + tenant endpoints.

Replaces manual Bargain Rule setup for Home Services. Admin configures
platform pricing + platform fee; the backend automatically derives
Low/Mid/High customer price options (no manual "bargain rule" authoring
required). Reuses the certified pure engines built in prior sprints:
  - app.engines.admin_catalog.bargain_engine (floor formula, validation)
  - app.engines.home_service_booking.matching_engine (Low/Mid/High tiers,
    provider-first matching, area comparison)

Feature flags (see app/core/feature_flags.py):
  - manual_bargain_rules_enabled   (default False)
  - auto_price_options_enabled     (default True)
  - provider_first_matching_enabled (default True)
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import get_home_services_pricing_flags
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.bargain_engine import (
    BargainValidationError, compute_symmetric_customer_price_tiers,
)
from app.engines.admin_catalog.models import BargainRule, ServicePricingRule, MasterService
from app.engines.home_service_booking.matching_engine import (
    compute_price_tiers, select_best_provider, get_area_market_comparison,
    build_customer_safe_provider, build_admin_provider,
    assert_home_services_vertical, VerticalFlowNotSupported,
)
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

admin_router = APIRouter(prefix="/v1/admin/home-services", tags=["Home Services Price Experience"])
tenant_router = APIRouter(prefix="/v1/tenant/home-services", tags=["Home Services Customer Price Preview"])

ENGINE_ID = "auto_price_options"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@admin_router.get("/config", response_model=ApiResponse[dict],
                   summary="Get Home Services pricing feature-flag status (manual bargain vs. automatic price options)")
async def get_home_services_config(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    flags = await get_home_services_pricing_flags(db)
    return ok(flags, _rid(r), ENGINE_ID)


# Customer Price Experience preview endpoint removed (2026-07) -- it was an
# admin testing tool built entirely around admin_min_price/admin_max_price/
# admin_base_price, the same deprecated "admin sets price boundaries" model
# as Pricing Rules. This platform is provider-set-price.


# ── Admin: Matching Diagnostics ──────────────────────────────────────────────

@admin_router.post("/matching/diagnostics", response_model=ApiResponse[dict],
                    summary="Run provider-first matching for given parameters and show full diagnostics (admin-only score breakdown)")
async def admin_matching_diagnostics(
    r: Request,
    u: UserContext = Depends(require_permission(P.PRICING_BARGAIN_EVALUATE_PREVIEW)),
    db: AsyncSession = Depends(get_db),
):
    body = await r.json()
    category_id = uuid.UUID(str(body["category_id"]))
    master_service_id = uuid.UUID(str(body["master_service_id"]))
    city = body["city"]
    zipcode = body.get("zipcode")
    offering_type_id = uuid.UUID(str(body["offering_type_id"])) if body.get("offering_type_id") else None
    brand_id = uuid.UUID(str(body["brand_id"])) if body.get("brand_id") else None
    requested_at = body.get("requested_at")  # HS6B — optional; enables break/holiday/booking-window checks

    match = await select_best_provider(
        db, category_id=category_id, offering_id=master_service_id,
        city=city, zipcode=zipcode, offering_type_id=offering_type_id, brand_id=brand_id,
        requested_at=requested_at,
    )

    result = {
        "eligible_provider_count": len(match.get("all_scored", [])) if match.get("signals") else 0,
        "candidate_provider_count": match.get("candidate_count", 0),
        "excluded_provider_count": match.get("excluded_count", 0),
        "excluded_providers": match.get("excluded_providers", []),
        "selected_provider": None,
        "top_candidates": [],
        "price_options": None,
        "area_market_comparison": None,
        # HS6B — canonical sources this diagnostic run actually used, so
        # admins can see which model is authoritative (not the old,
        # disconnected provider_enabled_offerings/tenant_wallets/
        # security_deposits/tenant_package_assignments reads).
        "bookability_source": "canonical_provider_status",
        "area_coverage_source": "normalized_service_area_coverage",
        "availability_source": "tenant_availability_rules",
        "pricing_source": "tenant_type_brand_pricing",
    }

    if match.get("signals"):
        signals, score = match["signals"], match["score"]
        result["selected_provider"] = build_admin_provider(signals, score)
        result["top_candidates"] = [
            build_admin_provider(s, sc) for s, sc in match.get("all_scored", [])[:5]
        ]

        bargain_rule = await db.scalar(
            select(BargainRule).where(
                BargainRule.master_service_id == master_service_id,
                BargainRule.status == "active", BargainRule.deleted_at.is_(None),
            ).order_by(BargainRule.created_at.desc()).limit(1)
        )
        if bargain_rule and bargain_rule.customer_min_price is not None and bargain_rule.customer_max_price is not None:
            pricing_rule = await db.get(ServicePricingRule, bargain_rule.pricing_rule_id) if bargain_rule.pricing_rule_id else None
            try:
                result["price_options"] = compute_price_tiers(
                    admin_min_price=pricing_rule.min_price if pricing_rule else None,
                    admin_max_price=pricing_rule.max_price if pricing_rule else None,
                    admin_base_price=pricing_rule.base_price if pricing_rule else None,
                    customer_min_price=bargain_rule.customer_min_price,
                    customer_max_price=bargain_rule.customer_max_price,
                    platform_fee_percent=bargain_rule.platform_fee_percent or (pricing_rule.platform_fee_percent if pricing_rule else 0),
                    platform_fee_fixed_amount=bargain_rule.platform_fee_fixed_amount,
                )
            except BargainValidationError:
                result["price_options"] = None

        result["area_market_comparison"] = await get_area_market_comparison(
            db, category_id=category_id, offering_id=master_service_id,
            city=city, zipcode=zipcode,
            exclude_tenant_id=uuid.UUID(signals.tenant_id),
        )

    return ok(result, _rid(r), ENGINE_ID)


# ── Tenant: Customer Price Preview (read-only) ───────────────────────────────

def _tenant_id(u: UserContext) -> uuid.UUID:
    if not u.tenant_id:
        raise ServiceOSException("TENANT_ACCESS_DENIED", "No tenant context in token.", status_code=403)
    return uuid.UUID(u.tenant_id)


@tenant_router.get("/customer-price-preview", response_model=ApiResponse[dict],
                    summary="See what customers will see: Low/Mid/High for this tenant's own service (read-only)")
async def tenant_customer_price_preview(
    r: Request,
    master_service_id: uuid.UUID,
    service_type_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """MODULE-L5-57: rewired off the legacy BargainRule/ServicePricingRule
    path (both admin-owned, not tenant-scoped -- the master_service_id-only
    query previously returned the SAME range to every tenant offering that
    service, never this tenant's own configured price). Now resolves through
    TenantCatalogService.resolve_tenant_price -- the exact same tenant-owned,
    type/brand-precedence resolver real customer bookings use
    (home_service_booking/service.py::_resolve_selected_tenant_price) -- so
    tenant preview and customer runtime share one calculation, per the
    Customer Price Experience consolidation."""
    from app.engines.admin_catalog.models import TenantService, ServiceCategory
    from app.engines.admin_catalog.tenant_service import TenantCatalogService

    tid = _tenant_id(u)
    svc = await db.get(MasterService, master_service_id)
    if not svc:
        raise ServiceOSException("MASTER_SERVICE_NOT_FOUND", "Master service not found.", status_code=404)

    ts = await db.scalar(
        select(TenantService).where(
            TenantService.tenant_id == tid,
            TenantService.master_service_id == master_service_id,
            TenantService.is_active.is_(True),
        )
    )
    if ts is None:
        return ok({
            "service_name": svc.service_name,
            "available": False,
            "message": "You have not enabled this service yet, so there is no customer price to preview.",
        }, _rid(r), ENGINE_ID)

    tenant_svc = TenantCatalogService(db=db)
    resolved = await tenant_svc.resolve_tenant_price(ts.id, service_type_id=service_type_id, brand_id=brand_id)
    if not resolved.get("resolved"):
        return ok({
            "service_name": svc.service_name,
            "tenant_service_id": str(ts.id),
            "available": False,
            "message": "Customer price options are not available yet for this service — "
                       "you have not configured a price range for this combination.",
        }, _rid(r), ENGINE_ID)

    cat = await db.get(ServiceCategory, svc.category_id) if svc.category_id else None
    fee_pct = float(cat.customer_charge_pct) if (cat and cat.customer_charge_pct is not None) else 0.0

    try:
        tiers = compute_price_tiers(
            admin_min_price=None, admin_max_price=None, admin_base_price=None,
            customer_min_price=resolved["minimum_price"], customer_max_price=resolved["maximum_price"],
            platform_fee_percent=fee_pct, platform_fee_fixed_amount=0,
        )
    except BargainValidationError as e:
        raise ServiceOSException(e.code, e.message, status_code=422) from e

    result = {
        "service_name": svc.service_name,
        "tenant_service_id": str(ts.id),
        "master_service_id": str(master_service_id),
        "job_type_id": str(ts.job_type_id) if ts.job_type_id else None,
        "pricing_model": "range",
        "available": True,
        **tiers,
        "currency": tiers.get("currency", "INR"),
        "calculation_source": resolved["source"],
        "calculation_source_rule_id": resolved.get("source_rule_id"),
        "unit": None,
        "effective_date": None,
        "explanation": (
            "These are the price options your customers see, derived from your own configured "
            "price plus the platform's customer-facing fee. Admin does not set or own this amount."
        ),
    }
    return ok(result, _rid(r), ENGINE_ID)


@tenant_router.get("/matching-readiness", response_model=ApiResponse[dict],
                    summary="Check whether this tenant currently passes provider-first matching eligibility (read-only)")
async def tenant_matching_readiness(
    r: Request,
    master_service_id: uuid.UUID,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.home_service_booking.matching_engine import _passes_full_eligibility_gate

    tid = _tenant_id(u)
    passes = await _passes_full_eligibility_gate(
        db, tenant_id=tid, offering_id=master_service_id, offering_type_id=None, brand_id=None,
    )
    return ok({
        "matching_ready": passes,
        "message": (
            "Your business currently satisfies provider-matching eligibility for this service."
            if passes else
            "Your business does not currently satisfy all provider-matching eligibility checks "
            "(coverage, technician, availability, pricing, package, credits, or deposit). "
            "See Setup Checklist for details."
        ),
    }, _rid(r), ENGINE_ID)
