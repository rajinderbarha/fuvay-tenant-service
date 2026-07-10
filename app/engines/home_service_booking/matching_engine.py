"""Provider-First Matching + Customer Price Choice Engine.

Corrects the prior model (provider_matching.py's find_bookable_home_service_providers,
consumed by service.py's select_provider) where the customer was shown a LIST of
eligible providers and picked one manually. The correct flow:

    1. Backend resolves the full eligibility gate for every candidate tenant.
    2. Backend scores every eligible candidate and selects exactly one (the best).
    3. Backend computes that ONE provider's Low/Mid/High price options
       (reusing app.engines.admin_catalog.bargain_engine's customer-range +
       platform-fee formula from the BARGAIN MODULE fix).
    4. Backend computes a separate, non-authoritative area/competitor comparison.
    5. Customer chooses Low/Mid/High only — never a provider.

Two layers, matching the pure/DB-aware split used for bargain_engine.py:
  - Pure functions (compute_provider_score, compute_price_tiers) — independently
    unit-testable, no DB.
  - DB-aware functions (select_best_provider, get_area_market_comparison) — real
    SQL eligibility filtering + ranking + competitor stats.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.bargain_engine import (
    evaluate_customer_bargain, BargainValidationError,
    compute_symmetric_customer_price_tiers,
)
from app.exceptions import ServiceOSException

logger = structlog.get_logger("home_service.matching_engine")

# ── Home Services scope guard ───────────────────────────────────────────────
# Provider-First Matching + Low/Mid/High Bargain is a Home Services-only flow.
# Other verticals (CA/professional services, IELTS/coaching, restaurants, real
# estate, education, listing/menu/subscription-based businesses) must never
# run this matching logic, show Low/Mid/High cards, or apply the
# "customer pays provider directly" / Completed Job Deduction model unless
# that vertical's own policy explicitly enables it later.
HOME_SERVICES_VERTICAL = "home_services"


class VerticalFlowNotSupported(ServiceOSException):
    """Raised when the Home-Services-only provider-first bargain flow is
    invoked for a non-Home-Services vertical. Inherits ServiceOSException so
    it automatically becomes a proper 4xx API error via the global handler."""
    def __init__(self, vertical: str | None):
        self.vertical = vertical
        super().__init__(
            "VERTICAL_FLOW_NOT_SUPPORTED",
            "Provider-first bargain flow is available only for Home Services.",
            status_code=422,
            context={"supported": False, "vertical": vertical,
                     "reason": "Provider-first bargain flow is only available for Home Services."},
        )


def assert_home_services_vertical(vertical: str | None) -> None:
    """Hard guard — call at the top of every Home Services matching/bargain
    entry point. Raises VerticalFlowNotSupported for anything else."""
    if vertical != HOME_SERVICES_VERTICAL:
        raise VerticalFlowNotSupported(vertical)

# ── Scoring weights (per ticket's suggested model) ──────────────────────────
WEIGHT_HEALTH_SCORE       = Decimal("0.20")
WEIGHT_JOB_COMPLETION     = Decimal("0.20")
WEIGHT_RATING             = Decimal("0.15")
WEIGHT_AVAILABILITY       = Decimal("0.15")
WEIGHT_SERVICE_MATCH      = Decimal("0.10")
WEIGHT_DISTANCE           = Decimal("0.10")
WEIGHT_CANCELLATION       = Decimal("0.05")
WEIGHT_CAPACITY           = Decimal("0.05")


def _d(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _round2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class CandidateSignals:
    """Raw 0-100 sub-scores for one eligible candidate tenant, plus identity."""
    tenant_id: str
    provider_name: str
    health_score: float = 0.0            # tenants.health_score, already 0-100
    job_completion_score: float = 0.0    # completed / (completed + cancelled), 0-100
    rating_score: float = 0.0            # rating_average / 5 * 100
    availability_score: float = 0.0      # has active technician + availability rules configured
    service_match_score: float = 0.0     # zipcode-exact + type/brand coverage specificity
    distance_score: float = 0.0          # zipcode-exact=100, city-only=60
    cancellation_score: float = 0.0      # 100 - recent_cancellation_rate*100
    capacity_score: float = 0.0          # inverse of current open-job load vs technician count
    public_badges: list[str] = field(default_factory=list)
    rating: float | None = None


def compute_provider_score(signals: CandidateSignals) -> Decimal:
    """provider_score = weighted sum of the 8 sub-scores (ticket's formula)."""
    score = (
        _d(signals.health_score) * WEIGHT_HEALTH_SCORE
        + _d(signals.job_completion_score) * WEIGHT_JOB_COMPLETION
        + _d(signals.rating_score) * WEIGHT_RATING
        + _d(signals.availability_score) * WEIGHT_AVAILABILITY
        + _d(signals.service_match_score) * WEIGHT_SERVICE_MATCH
        + _d(signals.distance_score) * WEIGHT_DISTANCE
        + _d(signals.cancellation_score) * WEIGHT_CANCELLATION
        + _d(signals.capacity_score) * WEIGHT_CAPACITY
    )
    return _round2(score)


def rank_candidates(candidates: list[CandidateSignals]) -> list[tuple[CandidateSignals, Decimal]]:
    """Scores every candidate and returns them sorted best-first. Ties broken by
    tenant_id for determinism (fair distribution is handled upstream by whichever
    candidate query order is used — this function is a pure sort)."""
    scored = [(c, compute_provider_score(c)) for c in candidates]
    scored.sort(key=lambda pair: (-pair[1], pair[0].tenant_id))
    return scored


def select_best_candidate(candidates: list[CandidateSignals]) -> tuple[CandidateSignals, Decimal] | None:
    ranked = rank_candidates(candidates)
    return ranked[0] if ranked else None


def build_score_breakdown(signals: CandidateSignals) -> dict:
    """Internal/admin-only breakdown — never returned by the customer-facing API."""
    return {
        "health_score": signals.health_score,
        "job_completion_score": signals.job_completion_score,
        "rating_score": signals.rating_score,
        "availability_score": signals.availability_score,
        "service_match_score": signals.service_match_score,
        "distance_score": signals.distance_score,
        "cancellation_score": signals.cancellation_score,
        "capacity_score": signals.capacity_score,
    }


CUSTOMER_VISIBLE_REASON = (
    "Best matched provider based on service coverage, availability, quality, and completion history."
)


def build_customer_safe_provider(signals: CandidateSignals, score: Decimal) -> dict:
    """Customer-facing selected_provider block — NEVER includes internal_score or
    internal_score_breakdown (hard gate 9)."""
    return {
        "tenant_id": signals.tenant_id,
        "provider_name": signals.provider_name,
        "public_badges": signals.public_badges,
        "rating": signals.rating,
        "customer_visible_reason": CUSTOMER_VISIBLE_REASON,
    }


def build_admin_provider(signals: CandidateSignals, score: Decimal) -> dict:
    """Admin/debug-only view — includes internal_score and its breakdown."""
    d = build_customer_safe_provider(signals, score)
    d["internal_score"] = float(score)
    d["internal_score_breakdown"] = build_score_breakdown(signals)
    return d


def round_to_nearest_10(value) -> Decimal:
    v = _d(value)
    return (v / Decimal("10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("10")


def compute_price_tiers(
    *,
    admin_min_price, admin_max_price, admin_base_price=None,
    customer_min_price, customer_max_price,
    platform_fee_percent=0, platform_fee_fixed_amount=0,
    currency: str = "INR",
) -> dict:
    """Selected-provider Low/Mid/High price options.

    HS6 fix: previously delegated to evaluate_customer_bargain(), whose
    allowed_offer_max is the RAW customer_max_price with no platform fee
    applied — high_price equaled the pre-fee provider max, violating the
    hard gate "High must include platform fee" / "High must not equal
    pre-fee provider max" (the same asymmetric-formula bug already found
    and fixed on the admin preview endpoint in an earlier sprint, but
    never fixed here since this is a separate function of the same name
    in a different module). Fixed by delegating to
    compute_symmetric_customer_price_tiers — the single formula already
    certified across the admin pricing console, tenant setup wizard, and
    customer price preview — so this module now uses the exact same
    Low/Mid/High math as everywhere else in Home Services.

    Still calls evaluate_customer_bargain first (unchanged) purely to
    preserve its admin/customer-range configuration validation (raises
    BargainValidationError on an invalid range/fee setup) — only the
    final price numbers are now recomputed with the fee-inclusive formula.
    """
    evaluate_customer_bargain(
        service_name=None,
        admin_min_price=admin_min_price, admin_max_price=admin_max_price,
        admin_base_price=admin_base_price,
        customer_min_price=customer_min_price, customer_max_price=customer_max_price,
        platform_fee_percent=platform_fee_percent, platform_fee_fixed_amount=platform_fee_fixed_amount,
        customer_offer=None, currency=currency,
    )
    symmetric = compute_symmetric_customer_price_tiers(
        provider_min_price=customer_min_price, provider_max_price=customer_max_price,
        platform_fee_percent=platform_fee_percent, platform_fee_fixed_amount=platform_fee_fixed_amount,
    )
    low = _d(symmetric["low_price"])
    high = _d(symmetric["high_price"])
    mid = _d(symmetric["mid_price"])

    return {
        "currency": currency,
        "allowed_offer_min": float(low),
        "allowed_offer_max": float(high),
        "low_price": float(low),
        "mid_price": float(mid),
        "high_price": float(high),
        "platform_fee_percent": symmetric["platform_fee_percent"],
        "platform_fee_amount": float(_round2(_d(high) - _d(customer_max_price))),
        "payment_mode": "customer_pays_provider_directly",
    }


PRICE_TIER_TO_FIELD = {"low": "low_price", "mid": "mid_price", "high": "high_price"}


def resolve_customer_offer_for_tier(price_options: dict, tier: str) -> Decimal:
    """Booking-creation-time resolution: Low/Mid/High → the exact stored price.
    Never trusts a customer-submitted numeric offer for tier selection — only
    the tier name is customer input; the amount always comes from the backend's
    own price_options (hard gate: customer cannot submit below Low, since there
    is no raw-amount input at all — only a tier choice)."""
    field_name = PRICE_TIER_TO_FIELD.get(tier)
    if field_name is None:
        raise ValueError(f"Invalid price tier: {tier!r}. Must be 'low', 'mid', or 'high'.")
    return _d(price_options[field_name])


# ── DB-aware: eligibility + ranking + area comparison ───────────────────────

# HS6B — aligned to the single canonical bookability source
# (provider_visibility_statuses.is_bookable, computed by
# _evaluate_provider_bookability in provider_portal/router.py) and the
# HS5B normalized per-area coverage table (tenant_service_area_services).
# The old technician/availability/package/wallet/deposit-specific codes
# were removed — those signals are now folded into the single
# NOT_BOOKABLE_CANONICAL_STATUS check (HS4B's is_bookable already
# considers all of them via tenant_billing/provider_availability_rules/
# tenant_service_areas).
ELIGIBILITY_GATE_CODES = (
    "tenant_not_active",
    "suspended",
    "vertical_mismatch",
    "NOT_BOOKABLE_CANONICAL_STATUS",
    "INSUFFICIENT_USAGE_CREDITS",
    "ZIPCODE_NOT_COVERED",
    "SERVICE_NOT_COVERED_IN_AREA",
    "TYPE_NOT_COVERED_IN_AREA",
    "BRAND_NOT_COVERED_IN_AREA",
    "no_pricing_rule",
)


async def select_best_provider(
    db: AsyncSession,
    *,
    category_id: uuid.UUID,
    offering_id: uuid.UUID,
    city: str,
    zipcode: str | None,
    offering_type_id: uuid.UUID | None = None,
    brand_id: uuid.UUID | None = None,
    requested_at: str | None = None,
    limit_candidates: int = 25,
) -> dict | None:
    """Full eligibility gate + scoring + single-best selection.

    Returns None if no tenant passes every eligibility gate. Returns a dict
    with 'signals', 'score', 'candidate_count', 'excluded_count', and
    'excluded_providers' (HS6B — per-candidate exclusion reason codes for
    admin diagnostics) — callers build the customer-safe / admin views
    from 'signals'/'score'.
    """
    from app.engines.tenant_engine.models import Tenant
    from app.engines.serviceability.models import TenantServiceArea

    norm_city = city.strip().lower()
    strip_zip = zipcode.strip() if zipcode else None

    # Base candidate pool: active, home_services, not suspended, matching category.
    base_rows = (await db.execute(
        select(
            Tenant.id.label("tenant_id"),
            Tenant.business_name.label("business_name"),
            Tenant.tenant_name.label("tenant_name"),
            Tenant.health_score.label("health_score"),
            Tenant.rating_average.label("rating"),
            TenantServiceArea.zipcode.label("area_zipcode"),
        )
        .join(TenantServiceArea, TenantServiceArea.tenant_id == Tenant.id)
        .where(
            Tenant.status == "active",
            Tenant.vertical == "home_services",
            Tenant.suspended_at.is_(None),
            # NOTE: tenants.category_id is unreliably NULL on real seeded
            # tenants (same gap found and worked around in the My Offerings
            # sprint) — vertical is the correct, populated gate; category_id
            # is intentionally not filtered on here.
            TenantServiceArea.is_active.is_(True),
            func.lower(TenantServiceArea.city) == norm_city,
        )
        .limit(limit_candidates)
    )).all()

    candidate_ids = {row.tenant_id for row in base_rows}
    if not candidate_ids:
        return {"signals": None, "score": None, "candidate_count": 0, "excluded_count": 0, "excluded_providers": []}

    exact_zip_ids = {row.tenant_id for row in base_rows if strip_zip and row.area_zipcode == strip_zip}

    signals_list: list[CandidateSignals] = []
    excluded = 0
    excluded_providers: list[dict] = []

    for row in base_rows:
        tid = row.tenant_id
        eligible, reason_code = await _passes_full_eligibility_gate(
            db, tenant_id=tid, offering_id=offering_id,
            offering_type_id=offering_type_id, brand_id=brand_id,
            zipcode=strip_zip, requested_at=requested_at,
        )
        if not eligible:
            excluded += 1
            excluded_providers.append({
                "provider_name": row.business_name or row.tenant_name or "Service Provider",
                "reason_code": reason_code,
            })
            continue

        is_exact_zip = tid in exact_zip_ids
        signals_list.append(CandidateSignals(
            tenant_id=str(tid),
            provider_name=row.business_name or row.tenant_name or "Service Provider",
            health_score=float(row.health_score) if row.health_score is not None else 0.0,
            job_completion_score=await _job_completion_score(db, tid),
            rating_score=(float(row.rating) / 5.0 * 100.0) if row.rating else 0.0,
            availability_score=await _availability_score(db, tid),
            service_match_score=100.0 if (offering_type_id or brand_id) else 80.0,
            distance_score=100.0 if is_exact_zip else 60.0,
            cancellation_score=await _cancellation_score(db, tid),
            capacity_score=await _capacity_score(db, tid),
            public_badges=await _public_badges(db, tid, row.health_score, row.rating),
            rating=float(row.rating) if row.rating else None,
        ))

    if not signals_list:
        return {"signals": None, "score": None, "candidate_count": len(base_rows), "excluded_count": excluded,
                "excluded_providers": excluded_providers}

    best = select_best_candidate(signals_list)
    return {
        "signals": best[0], "score": best[1],
        "candidate_count": len(base_rows), "excluded_count": excluded,
        "excluded_providers": excluded_providers,
        "all_scored": rank_candidates(signals_list),
    }


async def _passes_full_eligibility_gate(
    db: AsyncSession, *, tenant_id: uuid.UUID, offering_id: uuid.UUID,
    offering_type_id: uuid.UUID | None, brand_id: uuid.UUID | None,
    zipcode: str | None = None, requested_at: str | None = None,
) -> tuple[bool, str | None]:
    """HS6B — canonical eligibility gate, aligned to the single sources of
    truth this session already built and certified. Returns
    (eligible, reason_code) — reason_code is one of ELIGIBILITY_GATE_CODES
    when eligible is False, surfaced to admin diagnostics; None otherwise.

    1. Bookability: reads ONLY provider_visibility_statuses.is_bookable,
       computed by _evaluate_provider_bookability() (HS4B — the same
       function POST /v1/provider/status/refresh calls). Previously this
       gate ALSO independently re-derived bookability-adjacent signals
       from tenant_wallets/security_deposits/tenant_package_assignments
       — a second, parallel readiness calculation the ticket explicitly
       forbids ("Do not implement a second independent readiness
       calculation"). Real, confirmed bug: those secondary tables and
       provider_enabled_offerings.status used different criteria than
       is_bookable — a real tenant in this dev DB had
       provider_enabled_offerings.status='pending_approval' (an
       unrelated admin-approval workflow state) which would have
       excluded it from matching even though HS4B's canonical
       is_bookable was already true. Removed; is_bookable is now the
       single, canonical bookability answer.
    2. Area/service/type/brand coverage: reads HS5B's normalized
       tenant_service_area_services table (service_type_id/brand_id
       columns added in migration 121) instead of the old, disconnected
       provider_enabled_offerings.supported_type_ids/supported_brand_ids
       JSON arrays. The JSON-array columns are no longer read here —
       LEGACY_FALLBACK_ONLY, see HS6B_MATCHING_DATA_MODEL_ALIGNMENT_
       REPORT.md (not re-added as a fallback this sprint: every real
       tenant_service_area_services row this session created already
       covers the normalized case, and mixing two coverage sources risks
       exactly the kind of silent inconsistency this sprint exists to
       remove).
    3. HS6B addition: break/holiday/booking-window checks now reuse
       get_tenant_home_services_matching_inputs() (HS5B) — the SAME
       function POST /home-services/matching-inputs/preview calls —
       instead of leaving these unchecked in the real matching path
       (the gap HS6B's first pass over this function left open).
    4. Pricing rule existence: unchanged, still real and necessary.
    """
    from sqlalchemy import text

    # 1. Canonical bookability (HS4B) — single source of truth.
    bookable_row = (await db.execute(text(
        "SELECT is_bookable, bookability_blockers FROM provider_visibility_statuses WHERE tenant_id=:tid "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"tid": str(tenant_id)})).fetchone()
    if not bookable_row or not bookable_row.is_bookable:
        # HS9B — surface the more specific INSUFFICIENT_USAGE_CREDITS
        # reason when that's the actual root cause of non-bookability,
        # rather than the generic NOT_BOOKABLE_CANONICAL_STATUS, so a
        # low-credit tenant's exclusion is diagnosable at the matching
        # layer without cross-referencing the bookability endpoint
        # separately. Falls back to the generic code for every other
        # non-bookability cause (unchanged from HS4B/HS6B).
        blockers = bookable_row.bookability_blockers if bookable_row else None
        if blockers and any(
            isinstance(b, dict) and b.get("code") == "USAGE_CREDITS_INSUFFICIENT"
            for b in blockers
        ):
            return False, "INSUFFICIENT_USAGE_CREDITS"
        return False, "NOT_BOOKABLE_CANONICAL_STATUS"

    # 2. Normalized per-area service/type/brand coverage (HS5B).
    #    Requires at least one active service area covering this exact
    #    service (+ type + brand, when given) for this tenant.
    if zipcode:
        zip_row = (await db.execute(text(
            "SELECT count(*) FROM tenant_service_areas WHERE tenant_id=:tid AND is_active=true AND zipcode=:zip"
        ), {"tid": str(tenant_id), "zip": zipcode})).scalar()
        if not zip_row:
            return False, "ZIPCODE_NOT_COVERED"

    svc_row = (await db.execute(text(
        "SELECT count(*) FROM tenant_service_area_services tsas "
        "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
        "WHERE tsas.tenant_id=:tid AND tsas.service_id=:oid AND tsas.is_available=true AND tsa.is_active=true"
        + (" AND tsa.zipcode=:zip" if zipcode else "")
    ), {"tid": str(tenant_id), "oid": str(offering_id), **({"zip": zipcode} if zipcode else {})})).scalar()
    if not svc_row:
        return False, "SERVICE_NOT_COVERED_IN_AREA"

    if offering_type_id:
        type_row = (await db.execute(text(
            "SELECT count(*) FROM tenant_service_area_services tsas "
            "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
            "WHERE tsas.tenant_id=:tid AND tsas.service_id=:oid AND tsas.service_type_id=:stid "
            "AND tsas.is_available=true AND tsa.is_active=true"
            + (" AND tsa.zipcode=:zip" if zipcode else "")
        ), {"tid": str(tenant_id), "oid": str(offering_id), "stid": str(offering_type_id),
            **({"zip": zipcode} if zipcode else {})})).scalar()
        if not type_row:
            return False, "TYPE_NOT_COVERED_IN_AREA"

    if brand_id:
        brand_row = (await db.execute(text(
            "SELECT count(*) FROM tenant_service_area_services tsas "
            "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
            "WHERE tsas.tenant_id=:tid AND tsas.service_id=:oid AND tsas.brand_id=:bid "
            "AND tsas.is_available=true AND tsa.is_active=true"
            + (" AND tsa.zipcode=:zip" if zipcode else "")
        ), {"tid": str(tenant_id), "oid": str(offering_id), "bid": str(brand_id),
            **({"zip": zipcode} if zipcode else {})})).scalar()
        if not brand_row:
            return False, "BRAND_NOT_COVERED_IN_AREA"

    # 3. Break/holiday/booking-window (HS5B, shared — not re-derived here).
    if requested_at:
        from app.engines.provider_portal.router import get_tenant_home_services_matching_inputs
        inputs = await get_tenant_home_services_matching_inputs(
            db, tenant_id,
            service_id=offering_id, service_type_id=offering_type_id, brand_id=brand_id,
            zipcode=zipcode, requested_at=requested_at,
        )
        if inputs["blocked_by_break"]:
            return False, "BLOCKED_BY_BREAK"
        if inputs["blocked_by_exception"]:
            return False, "BLOCKED_BY_HOLIDAY"
        if not inputs["booking_window_valid"]:
            return False, "OUTSIDE_BOOKING_WINDOW"
        if not inputs["available_at_requested_time"]:
            return False, "NOT_AVAILABLE_AT_REQUESTED_TIME"

    # 4. Pricing exists for this service.
    pricing_row = (await db.execute(text(
        "SELECT id FROM service_pricing_rules WHERE master_service_id=:oid AND is_active=true LIMIT 1"
    ), {"oid": str(offering_id)})).fetchone()
    if not pricing_row:
        return False, "NO_VALID_PRICE_RULE"

    return True, None


async def _job_completion_score(db: AsyncSession, tenant_id: uuid.UUID) -> float:
    from sqlalchemy import text
    row = (await db.execute(text(
        "SELECT count(*) FILTER (WHERE status='completed') AS completed, "
        "       count(*) FILTER (WHERE status='cancelled') AS cancelled "
        "FROM jobs WHERE tenant_id=:tid"
    ), {"tid": str(tenant_id)})).fetchone()
    if not row or (row.completed or 0) + (row.cancelled or 0) == 0:
        return 50.0  # neutral score for providers with no job history yet
    total = row.completed + row.cancelled
    return round((row.completed / total) * 100.0, 2)


async def _cancellation_score(db: AsyncSession, tenant_id: uuid.UUID) -> float:
    from sqlalchemy import text
    row = (await db.execute(text(
        "SELECT count(*) FILTER (WHERE status='cancelled') AS cancelled, count(*) AS total "
        "FROM jobs WHERE tenant_id=:tid AND created_at > now() - interval '30 days'"
    ), {"tid": str(tenant_id)})).fetchone()
    if not row or not row.total:
        return 100.0  # no recent activity — no evidence of cancellations
    rate = row.cancelled / row.total
    return round(max(0.0, (1 - rate)) * 100.0, 2)


async def _availability_score(db: AsyncSession, tenant_id: uuid.UUID) -> float:
    from sqlalchemy import text
    count = (await db.execute(text(
        "SELECT count(*) FROM provider_availability_rules WHERE tenant_id=:tid AND is_active=true"
    ), {"tid": str(tenant_id)})).scalar()
    return min(100.0, float(count or 0) * 20.0)


async def _capacity_score(db: AsyncSession, tenant_id: uuid.UUID) -> float:
    from sqlalchemy import text
    row = (await db.execute(text(
        "SELECT (SELECT count(*) FROM jobs WHERE tenant_id=:tid AND status IN ('pending_assignment','assigned','in_progress')) AS open_jobs, "
        "(SELECT count(*) FROM provider_team_members WHERE tenant_id=:tid AND status='active' AND deleted_at IS NULL) AS active_techs"
    ), {"tid": str(tenant_id)})).fetchone()
    if not row or not row.active_techs:
        return 0.0
    load_ratio = (row.open_jobs or 0) / row.active_techs
    return round(max(0.0, 100.0 - load_ratio * 25.0), 2)


async def _public_badges(db: AsyncSession, tenant_id: uuid.UUID, health_score, rating) -> list[str]:
    badges = ["Verified"]
    if rating and float(rating) >= 4.5:
        badges.append("Highly Rated")
    if health_score and float(health_score) >= 90:
        badges.append("High Completion")
    return badges


async def get_area_market_comparison(
    db: AsyncSession, *,
    category_id: uuid.UUID, offering_id: uuid.UUID, city: str, zipcode: str | None,
    exclude_tenant_id: uuid.UUID | None = None,
) -> dict:
    """Read-only competitor price comparison. Never affects selected-provider
    price or assignment (hard gates 4-5) — this function has no return path
    that can influence select_best_provider's output; it is called
    independently, after selection, purely for display."""
    from sqlalchemy import text

    rows = (await db.execute(text("""
        SELECT ps.base_price
        FROM provider_enabled_offerings peo
        JOIN tenants t ON t.id = peo.tenant_id
        JOIN tenant_service_areas tsa ON tsa.tenant_id = t.id
        JOIN provider_visibility_statuses pvs ON pvs.tenant_id = t.id
        LEFT JOIN service_pricing_rules ps ON ps.master_service_id = peo.offering_id AND ps.is_active = true
        WHERE peo.offering_id = :oid AND peo.is_enabled = true AND peo.status = 'active'
          AND t.status = 'active' AND t.vertical = 'home_services'
          AND tsa.is_active = true AND lower(tsa.city) = :city
          AND pvs.is_bookable = true
          AND (CAST(:zipcode AS TEXT) IS NULL OR tsa.zipcode = CAST(:zipcode AS TEXT))
          AND (CAST(:exclude_id AS TEXT) IS NULL OR t.id != CAST(:exclude_id AS UUID))
    """), {
        "oid": str(offering_id), "city": city.strip().lower(),
        "zipcode": zipcode.strip() if zipcode else None,
        "exclude_id": str(exclude_tenant_id) if exclude_tenant_id else None,
    })).all()

    prices = [float(r.base_price) for r in rows if r.base_price is not None]
    area_label = f"{city} {zipcode}".strip() if zipcode else city

    if not prices:
        return {
            "area": area_label, "competitor_provider_count": 0,
            "area_competitor_min": None, "area_competitor_avg": None, "area_competitor_max": None,
        }

    return {
        "area": area_label,
        "competitor_provider_count": len(prices),
        "area_competitor_min": round(min(prices), 2),
        "area_competitor_avg": round(sum(prices) / len(prices), 2),
        "area_competitor_max": round(max(prices), 2),
    }
