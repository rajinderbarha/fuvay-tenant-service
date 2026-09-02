"""Home Services provider matching diagnostics and tenant readiness endpoints.

Pricing is provider-owned. Customer-facing charges are resolved by Home
Services Finance during booking. The retired Low/Mid/High price-option model
is intentionally not exposed here.
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
from app.engines.home_service_booking.matching_engine import (
    select_best_provider, get_area_market_comparison,
    build_admin_provider,
)
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

admin_router = APIRouter(prefix="/v1/admin/home-services", tags=["Home Services Matching"])
tenant_router = APIRouter(prefix="/v1/tenant/home-services", tags=["Home Services Matching Readiness"])

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


@admin_router.get("/matching/policy", response_model=ApiResponse[dict],
                   summary="Read-only, code-controlled provider-matching policy manifest -- no admin edit path exists")
async def get_matching_policy(
    r: Request,
    u: UserContext = Depends(require_permission(P.PRICING_BARGAIN_EVALUATE_PREVIEW)),
):
    from app.engines.home_service_booking.matching_engine import get_policy_manifest
    return ok(get_policy_manifest(), _rid(r), ENGINE_ID)


# Admin price preview endpoint removed -- it was an
# admin testing tool built entirely around admin_min_price/admin_max_price/
# admin_base_price, the same deprecated "admin sets price boundaries" model
# as Pricing Rules. This platform is provider-set-price.


# Single overall provider LEVEL for Matching Diagnostics only (explicit user
# request, 2026-08-06). Previously this admin tool showed the shared,
# customer-facing `public_badges` list (0-3 independent achievement badges:
# Verified/Highly Rated/High Completion) -- the request is a single tier
# badge instead, so admins can see "which of 4 levels is this provider" at a
# glance. Deliberately scoped to this endpoint's response only: does not
# touch matching_engine.build_customer_safe_provider/_public_badges, which
# other real surfaces (customer_router.py, trust_quality/public_router.py)
# still read unchanged.
PROVIDER_LEVELS = [
    # Highest precedence first -- a provider gets exactly ONE, the best they qualify for.
    {"name": "Elite Pro",     "icon": "award",       "color": "#7c3aed"},  # best of the best: top-rated AND high completion
    {"name": "Top Rated Pro", "icon": "star",        "color": "#f59e0b"},  # customers rate them highly
    {"name": "Verified Pro",  "icon": "shield-check","color": "#3b82f6"},  # platform-vetted, reliable completion history
    {"name": "New Partner",   "icon": "user-plus",   "color": "#64748b"},  # just joined / not enough signal yet
]


def _resolve_provider_level(rating: float | None, health_score: float | None) -> dict:
    rating = float(rating) if rating is not None else None
    health_score = float(health_score) if health_score is not None else None
    is_top_rated = rating is not None and rating >= 4.5
    is_high_completion = health_score is not None and health_score >= 90
    if is_top_rated and is_high_completion:
        return PROVIDER_LEVELS[0]  # Elite Pro
    if is_top_rated:
        return PROVIDER_LEVELS[1]  # Top Rated Pro
    if is_high_completion:
        return PROVIDER_LEVELS[2]  # Verified Pro
    return PROVIDER_LEVELS[3]  # New Partner


def _attach_provider_level(provider: dict | None) -> dict | None:
    if not provider:
        return provider
    health_score = (provider.get("internal_score_breakdown") or {}).get("health_score")
    provider["provider_level"] = _resolve_provider_level(provider.get("rating"), health_score)
    return provider


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
    job_type_id = uuid.UUID(str(body["job_type_id"])) if body.get("job_type_id") else None
    requested_at = body.get("requested_at")  # HS6B — optional; enables break/holiday/booking-window checks

    match = await select_best_provider(
        db, category_id=category_id, offering_id=master_service_id,
        city=city, zipcode=zipcode, offering_type_id=offering_type_id, brand_id=brand_id,
        requested_at=requested_at, job_type_id=job_type_id,
    )

    result = {
        "eligible_provider_count": len(match.get("all_scored", [])) if match.get("signals") else 0,
        "candidate_provider_count": match.get("candidate_count", 0),
        "excluded_provider_count": match.get("excluded_count", 0),
        "excluded_providers": match.get("excluded_providers", []),
        "selected_provider": None,
        "top_candidates": [],
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
        result["selected_provider"] = _attach_provider_level(build_admin_provider(signals, score))
        result["top_candidates"] = [
            _attach_provider_level(build_admin_provider(s, sc)) for s, sc in match.get("all_scored", [])[:5]
        ]

        result["area_market_comparison"] = await get_area_market_comparison(
            db, category_id=category_id, offering_id=master_service_id,
            city=city, zipcode=zipcode,
            exclude_tenant_id=uuid.UUID(signals.tenant_id),
        )

    # MODULE-L5-58 — canonical audit trail for every diagnostic run (reuses
    # the existing append-only MasterDataAuditLog rather than a new table).
    # A diagnostic mutates nothing operational; this audit row is the ONLY
    # write a diagnostic performs, and it never touches a booking/job/
    # assignment/score.
    from app.engines.admin_catalog.models import MasterDataAuditLog
    from app.engines.home_service_booking.matching_engine import MATCHING_POLICY_VERSION
    trace_id = uuid.uuid4()
    db.add(MasterDataAuditLog(
        entity_type="matching_decision", entity_id=trace_id, action="diagnostic_run",
        actor_user_id=uuid.UUID(str(u.user_id)) if getattr(u, "user_id", None) else None,
        actor_role=getattr(u, "role", None),
        new_value={
            "trace_id": str(trace_id), "policy_version": MATCHING_POLICY_VERSION,
            "master_service_id": str(master_service_id), "city": city, "zipcode": zipcode,
            "job_type_id": str(job_type_id) if job_type_id else None,
            "candidate_count": result["candidate_provider_count"],
            "eligible_count": result["eligible_provider_count"],
            "excluded_count": result["excluded_provider_count"],
            "selected_provider_id": match["signals"].tenant_id if match.get("signals") else None,
            "outcome": "selected" if match.get("signals") else "no_eligible_provider",
        },
        request_id=_rid(r),
    ))
    await db.commit()
    result["trace_id"] = str(trace_id)
    result["policy_version"] = MATCHING_POLICY_VERSION

    return ok(result, _rid(r), ENGINE_ID)


@admin_router.get("/matching/audit", response_model=ApiResponse[dict],
                   summary="Audit trail of diagnostic runs (actor, input context, outcome) -- canonical audit system")
async def get_matching_diagnostic_audit(
    r: Request,
    limit: int = 50,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.admin_catalog.models import MasterDataAuditLog
    rows = (await db.execute(
        select(MasterDataAuditLog)
        .where(MasterDataAuditLog.entity_type == "matching_decision", MasterDataAuditLog.action == "diagnostic_run")
        .order_by(MasterDataAuditLog.created_at.desc())
        .limit(min(limit, 200))
    )).scalars().all()
    return ok({"items": [row.to_dict() for row in rows]}, _rid(r), ENGINE_ID)


@admin_router.get("/matching/decisions", response_model=ApiResponse[dict],
                   summary="Recent real (production) matching decisions -- Live Decisions view")
async def get_matching_live_decisions(
    r: Request,
    limit: int = 50,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.admin_catalog.models import MasterDataAuditLog
    rows = (await db.execute(
        select(MasterDataAuditLog)
        .where(MasterDataAuditLog.entity_type == "matching_decision", MasterDataAuditLog.action == "production_match")
        .order_by(MasterDataAuditLog.created_at.desc())
        .limit(min(limit, 200))
    )).scalars().all()
    return ok({"items": [row.to_dict() for row in rows]}, _rid(r), ENGINE_ID)


# ── Tenant: Customer Price Preview (read-only) ───────────────────────────────

def _tenant_id(u: UserContext) -> uuid.UUID:
    if not u.tenant_id:
        raise ServiceOSException("TENANT_ACCESS_DENIED", "No tenant context in token.", status_code=403)
    return uuid.UUID(u.tenant_id)


async def tenant_customer_price_preview_removed():
    raise ServiceOSException(
        "CUSTOMER_PRICE_PREVIEW_RETIRED",
        "Customer price preview was removed with the retired tier-based pricing model.",
        status_code=410,
    )

@tenant_router.get("/matching-readiness", response_model=ApiResponse[dict],
                    summary="Check whether this tenant currently passes provider-first matching eligibility (read-only)")
async def tenant_matching_readiness(
    r: Request,
    master_service_id: uuid.UUID,
    job_type_id: uuid.UUID | None = None,
    zipcode: str | None = None,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.home_service_booking.matching_engine import _passes_full_eligibility_gate
    from app.engines.admin_catalog.models import TenantService

    tid = _tenant_id(u)
    # The canonical gate returns ``(eligible, reason_code)``.  This endpoint
    # previously assigned that tuple to ``passes`` and then used it as a
    # boolean.  A non-empty tuple is always truthy, so the API returned
    # ``matching_ready: [false, "NO_VALID_PRICE_RULE"]`` while its message
    # claimed the service was ready.  Resolve the exact published job-type
    # children and unpack every result explicitly.
    if job_type_id is not None:
        job_type_ids: list[uuid.UUID | None] = [job_type_id]
    else:
        job_type_ids = list((await db.execute(
            select(TenantService.job_type_id).where(
                TenantService.tenant_id == tid,
                TenantService.master_service_id == master_service_id,
                TenantService.is_active.is_(True),
                TenantService.is_enabled.is_(True),
                TenantService.setup_status == "published",
                TenantService.deleted_at.is_(None),
            )
        )).scalars().all())

    if not job_type_ids:
        return ok({
            "matching_ready": False,
            "reason_code": "OFFERING_NOT_PUBLISHED",
            "message": "Publish this service before checking provider matching readiness.",
            "job_type_results": [],
        }, _rid(r), ENGINE_ID)

    results: list[dict] = []
    for resolved_job_type_id in job_type_ids:
        eligible, reason_code = await _passes_full_eligibility_gate(
            db,
            tenant_id=tid,
            offering_id=master_service_id,
            offering_type_id=None,
            brand_id=None,
            zipcode=zipcode,
            job_type_id=resolved_job_type_id,
        )
        results.append({
            "job_type_id": str(resolved_job_type_id) if resolved_job_type_id else None,
            "matching_ready": bool(eligible),
            "reason_code": reason_code,
        })

    passes = all(item["matching_ready"] for item in results)
    first_reason = next((item["reason_code"] for item in results if item["reason_code"]), None)
    return ok({
        "matching_ready": bool(passes),
        "reason_code": first_reason,
        "job_type_results": results,
        "message": (
            "Your business currently satisfies provider-matching eligibility for this service."
            if passes else
            "Your business does not currently satisfy all provider-matching eligibility checks "
            "(coverage, technician, availability, pricing, seats, or credits). "
            "See Setup Checklist for details."
        ),
    }, _rid(r), ENGINE_ID)
