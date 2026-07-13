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


# ── Admin: Customer Price Experience preview ────────────────────────────────

@admin_router.post("/price-experience/preview", response_model=ApiResponse[dict],
                    summary="Preview automatic Low/Mid/High price options from raw parameters (admin testing tool)")
async def admin_price_experience_preview(
    r: Request,
    u: UserContext = Depends(require_permission(P.PRICING_BARGAIN_EVALUATE_PREVIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Platform fee must be applied to BOTH ends of the selected range, not
    just the minimum — see CUSTOMER_PRICE_EXPERIENCE_CALCULATION_FIX_REPORT.md.
    Uses compute_symmetric_customer_price_tiers (same formula as the Admin
    Home Services Catalog Console and Tenant Setup Wizard), with
    rounding_increment=5 per this tool's own ticket example."""
    body = await r.json()

    admin_min = body.get("admin_min_price")
    admin_max = body.get("admin_max_price")
    selected_min = body.get("selected_min_price", body.get("customer_min_price"))
    selected_max = body.get("selected_max_price", body.get("customer_max_price"))
    fee_pct = body.get("platform_fee_percent", 0) or 0

    if admin_min is not None and admin_max is not None and admin_min > admin_max:
        raise ServiceOSException("INVALID_ADMIN_RANGE", "Admin Min must be <= Admin Max.", status_code=422)
    if admin_min is not None and selected_min is not None and selected_min < admin_min:
        raise ServiceOSException("SELECTED_RANGE_BELOW_ADMIN_MIN",
            f"Selected Range Min cannot be below Admin Min ({admin_min}).", status_code=422)
    if admin_max is not None and selected_max is not None and selected_max > admin_max:
        raise ServiceOSException("SELECTED_RANGE_ABOVE_ADMIN_MAX",
            f"Selected Range Max cannot exceed Admin Max ({admin_max}).", status_code=422)

    try:
        tiers = compute_symmetric_customer_price_tiers(
            provider_min_price=selected_min,
            provider_max_price=selected_max,
            platform_fee_percent=fee_pct,
            platform_fee_fixed_amount=body.get("platform_fee_fixed_amount", 0),
            rounding_increment=5,
        )
    except BargainValidationError as e:
        raise ServiceOSException(e.code, e.message, status_code=422) from e

    fee_on_min = round(selected_min * fee_pct / 100, 2) if selected_min is not None else None
    fee_on_max = round(selected_max * fee_pct / 100, 2) if selected_max is not None else None

    result = {
        "service_name": body.get("service_name"),
        "admin_min_price": admin_min,
        "admin_max_price": admin_max,
        "admin_base_price": body.get("admin_base_price"),
        "selected_min_price": selected_min,
        "selected_max_price": selected_max,
        "platform_fee_percent": tiers["platform_fee_percent"],
        "platform_fee_on_min": fee_on_min,
        "platform_fee_on_max": fee_on_max,
        "customer_low_price": tiers["low_price"],
        "customer_mid_price": tiers["mid_price"],
        "customer_high_price": tiers["high_price"],
        "allowed_offer_min": tiers["low_price"],
        "allowed_offer_max": tiers["high_price"],
        "payment_mode": tiers["payment_mode"],
        # Backward-compatible aliases for any existing consumer of the old shape.
        "customer_min_price": selected_min,
        "customer_max_price": selected_max,
        "low_price": tiers["low_price"],
        "mid_price": tiers["mid_price"],
        "high_price": tiers["high_price"],
    }
    return ok(result, _rid(r), ENGINE_ID)


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
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _tenant_id(u)

    bargain_rule = await db.scalar(
        select(BargainRule).where(
            BargainRule.master_service_id == master_service_id,
            BargainRule.status == "active", BargainRule.deleted_at.is_(None),
        ).order_by(BargainRule.created_at.desc()).limit(1)
    )
    svc = await db.get(MasterService, master_service_id)
    if not bargain_rule or bargain_rule.customer_min_price is None or bargain_rule.customer_max_price is None:
        return ok({
            "service_name": svc.service_name if svc else None,
            "available": False,
            "message": "Customer price options are not available yet for this service — "
                       "the platform has not configured a customer price range.",
        }, _rid(r), ENGINE_ID)

    pricing_rule = await db.get(ServicePricingRule, bargain_rule.pricing_rule_id) if bargain_rule.pricing_rule_id else None
    try:
        tiers = compute_price_tiers(
            admin_min_price=pricing_rule.min_price if pricing_rule else None,
            admin_max_price=pricing_rule.max_price if pricing_rule else None,
            admin_base_price=pricing_rule.base_price if pricing_rule else None,
            customer_min_price=bargain_rule.customer_min_price,
            customer_max_price=bargain_rule.customer_max_price,
            platform_fee_percent=bargain_rule.platform_fee_percent or (pricing_rule.platform_fee_percent if pricing_rule else 0),
            platform_fee_fixed_amount=bargain_rule.platform_fee_fixed_amount,
        )
    except BargainValidationError as e:
        raise ServiceOSException(e.code, e.message, status_code=422) from e

    completed_job_deduction_credits = getattr(pricing_rule, "completed_job_deduction_credits", 0) if pricing_rule else 0

    result = {
        "service_name": svc.service_name if svc else None,
        "available": True,
        **tiers,
        "completed_job_deduction_credits": completed_job_deduction_credits,
        "explanation": (
            "ServiceOS automatically creates customer price options from platform pricing "
            "and platform fee. You do not need to set up bargaining manually."
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
