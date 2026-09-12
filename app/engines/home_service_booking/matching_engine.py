"""Provider-first matching engine.

Corrects the prior model (provider_matching.py's find_bookable_home_service_providers,
consumed by service.py's select_provider) where the customer was shown a LIST of
eligible providers and picked one manually. The correct flow:

    1. Backend resolves the full eligibility gate for every candidate tenant.
    2. Backend scores every eligible candidate and selects exactly one (the best).
    3. Backend computes a separate, non-authoritative area/competitor comparison.
    4. Booking pricing is resolved from the selected provider's published
       TenantService price plus Home Services Finance charges.
    5. Customer confirms the single server-resolved price contract.

Two layers keep pure scoring separate from database-aware eligibility:
  - Pure functions (compute_provider_score) — independently
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
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException

logger = structlog.get_logger("home_service.matching_engine")

# ── Home Services scope guard ───────────────────────────────────────────────
# Provider-first matching is a Home Services-only flow.
# Other verticals (CA/professional services, IELTS/coaching, restaurants, real
# estate, education, listing/menu/subscription-based businesses) must never
# run this matching logic or apply the
# "customer pays provider directly" / Completed Job Deduction model unless
# that vertical's own policy explicitly enables it later.
HOME_SERVICES_VERTICAL = "home_services"


class VerticalFlowNotSupported(ServiceOSException):
    """Raised when the Home-Services-only provider-first booking flow is
    invoked for a non-Home-Services vertical. Inherits ServiceOSException so
    it automatically becomes a proper 4xx API error via the global handler."""
    def __init__(self, vertical: str | None):
        self.vertical = vertical
        super().__init__(
            "VERTICAL_FLOW_NOT_SUPPORTED",
            "Provider-first booking flow is available only for Home Services.",
            status_code=422,
            context={"supported": False, "vertical": vertical,
                     "reason": "Provider-first booking flow is only available for Home Services."},
        )


def assert_home_services_vertical(vertical: str | None) -> None:
    """Hard guard — call at the top of every Home Services matching
    entry point. Raises VerticalFlowNotSupported for anything else."""
    if vertical != HOME_SERVICES_VERTICAL:
        raise VerticalFlowNotSupported(vertical)

# ── Enterprise v2 scoring weights ───────────────────────────────────────────
WEIGHT_HEALTH_SCORE         = Decimal("0.30")
WEIGHT_SERVICE_RELIABILITY  = Decimal("0.20")
WEIGHT_SLOT_FIT             = Decimal("0.20")
WEIGHT_DISTANCE             = Decimal("0.10")
WEIGHT_CAPACITY             = Decimal("0.10")
WEIGHT_FAIR_SHARE           = Decimal("0.10")

MIN_HEALTH_ALLOCATION_WEIGHT = Decimal("0.10")
ALLOCATION_HOLD_MINUTES = 15


def _d(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _round2(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class CandidateSignals:
    """Raw 0-100 sub-scores for one eligible candidate tenant, plus identity."""
    tenant_id: str
    provider_name: str
    health_score: float = 0.0            # canonical trust_quality.HealthScore, or documented fallback
    health_score_source: str = "unassessed_default"  # "canonical" | "unassessed_default"
    health_score_calculated_at: str | None = None
    job_completion_score: float = 0.0    # completed / (completed + cancelled), 0-100
    rating_score: float = 0.0            # rating_average / 5 * 100
    availability_score: float = 0.0      # has active technician + availability rules configured
    service_match_score: float = 0.0     # zipcode-exact + type/brand coverage specificity
    distance_score: float = 0.0          # zipcode-exact=100, city-only=60
    cancellation_score: float = 0.0      # 100 - recent_cancellation_rate*100
    capacity_score: float = 0.0          # inverse of current open-job load vs technician count
    # Enterprise v2 signals. Optional fields preserve compatibility with old
    # pure callers while DB-backed matching always supplies real values.
    service_reliability_score: float | None = None
    slot_fit_score: float | None = None
    fair_share_score: float | None = None
    reliability_sample_size: int = 0
    recent_allocations: int = 0
    allocation_weight: float = 1.0
    allocation_finish_position: float = 1.0
    earliest_slot: dict | None = None
    # Objects {name, icon, color} — the real customer-visible trust badges when
    # the provider has them, else computed fallbacks (see _public_badges).
    public_badges: list[dict] = field(default_factory=list)
    rating: float | None = None


def compute_provider_score(signals: CandidateSignals) -> Decimal:
    """Enterprise v2 provider score.

    Health is long-lived quality. Service reliability is exact-offering
    performance. Slot fit and capacity are transient supply. Fair share stops
    equally-qualified providers being starved.
    """
    reliability = signals.service_reliability_score
    if reliability is None:
        reliability = (
            signals.job_completion_score * 0.50
            + signals.cancellation_score * 0.30
            + signals.rating_score * 0.20
        )
    slot_fit = signals.slot_fit_score
    if slot_fit is None:
        slot_fit = signals.availability_score
    fair_share = signals.fair_share_score
    if fair_share is None:
        fair_share = 50.0
    score = (
        _d(signals.health_score) * WEIGHT_HEALTH_SCORE
        + _d(reliability) * WEIGHT_SERVICE_RELIABILITY
        + _d(slot_fit) * WEIGHT_SLOT_FIT
        + _d(signals.distance_score) * WEIGHT_DISTANCE
        + _d(signals.capacity_score) * WEIGHT_CAPACITY
        + _d(fair_share) * WEIGHT_FAIR_SHARE
    )
    return _round2(score)


def rank_candidates(candidates: list[CandidateSignals]) -> list[tuple[CandidateSignals, Decimal]]:
    """Scores candidates best-first with fair share as the business tie-break."""
    scored = [(c, compute_provider_score(c)) for c in candidates]
    scored.sort(key=lambda pair: (
        -pair[1],
        -_d(pair[0].fair_share_score if pair[0].fair_share_score is not None else 50),
        pair[0].tenant_id,
    ))
    return scored


def _quality_score(candidate: CandidateSignals) -> Decimal:
    """Stable quality axis used to define the fair-allocation peer group."""
    reliability = candidate.service_reliability_score
    if reliability is None:
        reliability = (
            candidate.job_completion_score * 0.50
            + candidate.cancellation_score * 0.30
            + candidate.rating_score * 0.20
        )
    return _round2(
        _d(candidate.health_score) * Decimal("0.60")
        + _d(reliability) * Decimal("0.40")
    )


def health_allocation_weight(health_score: float) -> Decimal:
    """Continuous allocation share for an eligible marketplace provider.

    Health affects relative share only; it is never an assignment cutoff.
    A score of 100 receives full weight, 70 receives 0.55, and even a score of
    zero retains a 0.10 floor. This lets the marketplace reduce exposure when
    alternatives exist while still routing automatically when that provider
    is the only otherwise-eligible option.
    """
    health = min(Decimal("100"), max(Decimal("0"), _d(health_score)))
    return MIN_HEALTH_ALLOCATION_WEIGHT + (
        health / Decimal("100")
    ) * (Decimal("1") - MIN_HEALTH_ALLOCATION_WEIGHT)


def _allocation_finish_position(candidate: CandidateSignals) -> Decimal:
    weight = health_allocation_weight(candidate.health_score)
    return _d(candidate.recent_allocations + 1) / weight


def select_best_candidate(candidates: list[CandidateSignals]) -> tuple[CandidateSignals, Decimal] | None:
    if not candidates:
        return None

    # Weighted round robin is authoritative after all hard eligibility,
    # bookability, slot and health-floor checks have passed. The provider with
    # the lowest projected allocations-per-health-weight gets the next turn.
    # Enterprise score and tenant id are deterministic tie-breakers only.
    scored = [(candidate, compute_provider_score(candidate)) for candidate in candidates]
    scored.sort(key=lambda pair: (
        _allocation_finish_position(pair[0]),
        -pair[1],
        pair[0].tenant_id,
    ))
    return scored[0]


def build_score_breakdown(signals: CandidateSignals) -> dict:
    """Internal/admin-only breakdown — never returned by the customer-facing API."""
    return {
        "health_score": signals.health_score,
        "health_score_source": signals.health_score_source,
        "health_score_calculated_at": signals.health_score_calculated_at,
        "job_completion_score": signals.job_completion_score,
        "rating_score": signals.rating_score,
        "availability_score": signals.availability_score,
        "service_match_score": signals.service_match_score,
        "distance_score": signals.distance_score,
        "cancellation_score": signals.cancellation_score,
        "capacity_score": signals.capacity_score,
        "service_reliability_score": signals.service_reliability_score,
        "slot_fit_score": signals.slot_fit_score,
        "fair_share_score": signals.fair_share_score,
        "reliability_sample_size": signals.reliability_sample_size,
        "recent_allocations": signals.recent_allocations,
        "allocation_weight": signals.allocation_weight,
        "allocation_finish_position": signals.allocation_finish_position,
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
    "TENANT_CATEGORY_NOT_ENTITLED",
    "NOT_BOOKABLE_CANONICAL_STATUS",
    "INSUFFICIENT_USAGE_CREDITS",
    "ZIPCODE_NOT_COVERED",
    "SERVICE_NOT_COVERED_IN_AREA",
    "TYPE_NOT_COVERED_IN_AREA",
    "BRAND_NOT_COVERED_IN_AREA",
    "no_pricing_rule",
    "EXACT_JOB_TYPE_NOT_SUPPORTED",
    "OFFERING_NOT_PUBLISHED",
    "HEALTH_BAND_NOT_BOOKABLE",
    "NO_LIVE_SLOT_CAPACITY",
)

MATCHING_POLICY_KEY = "home_services_provider_matching_v4"
MATCHING_POLICY_VERSION = 4


def get_policy_manifest() -> dict:
    """Read-only, code-controlled matching policy manifest. There is no
    database-backed policy table and no admin write path for any of this --
    the values below ARE the deployed source of truth (the same module
    constants select_best_provider/_passes_full_eligibility_gate actually
    use), not a separately-maintained description that could drift."""
    factors = [
        {"factor_key": "health_score", "label": "Canonical Quality / Health", "weight": float(WEIGHT_HEALTH_SCORE),
         "source_engine": "active trust_quality.HealthScore; unassessed providers receive a neutral prior"},
        {"factor_key": "service_reliability", "label": "Service Reliability", "weight": float(WEIGHT_SERVICE_RELIABILITY),
         "source_engine": "service_jobs for the exact Master Service / Job Type with Bayesian cold-start"},
        {"factor_key": "slot_fit", "label": "Live Slot Fit", "weight": float(WEIGHT_SLOT_FIT),
         "source_engine": "confirmed booking capacity, holidays, notice period and provider hours"},
        {"factor_key": "area_match", "label": "Area Match", "weight": float(WEIGHT_DISTANCE),
         "source_engine": "tenant_service_areas (exact zipcode vs city-only)"},
        {"factor_key": "capacity", "label": "Live Capacity", "weight": float(WEIGHT_CAPACITY),
         "source_engine": "service-qualified funded technicians and confirmed service_jobs"},
        {"factor_key": "fair_share", "label": "Health-weighted Round Robin", "weight": float(WEIGHT_FAIR_SHARE),
         "source_engine": "7-day confirmed geographic allocation ledger plus 15-minute soft reservations"},
    ]
    return {
        "policy_key": MATCHING_POLICY_KEY,
        "version": MATCHING_POLICY_VERSION,
        "scope": "home_services",
        "code_controlled": True,
        "factors": factors,
        "eligibility_gates": list(ELIGIBILITY_GATE_CODES),
        "tie_break_policy": [
            "Every provider must first pass service, coverage, bookability, credit and live-slot gates.",
            "The lowest projected allocations-per-health-weight receives the next job.",
            "Enterprise score and tenant_id break only identical weighted-round-robin positions.",
        ],
        "missing_signal_policy": {
            "health_score": (
                f"Reads a fresh score from an active Trust & Quality formula. Missing, stale or "
                f"unbanded scores use the neutral prior {MISSING_HEALTH_SCORE_DEFAULT}; the legacy "
                "tenants.health_score default is never used for allocation."
            ),
            "service_reliability": "No exact-service history -> Bayesian neutral prior 70 with sample size 0.",
            "fair_share": "Equal-health providers alternate; lower health produces a smaller share but never blocks an otherwise-eligible provider.",
        },
        "allocation_policy": {
            "mode": "health_weighted_round_robin",
            "history_days": 7,
            "soft_reservation_minutes": ALLOCATION_HOLD_MINUTES,
            "scope": "zipcode when present, otherwise normalized city; shared across services",
            "confirmed_source": "service_jobs",
        },
        "data_science": {
            "mode": "shadow",
            "minimum_exact_service_samples": 50,
            "policy": (
                "Operational rules remain authoritative. Reliability sample size and every v2 feature are "
                "logged for offline validation; a trained model must pass bias, calibration and rollback "
                "checks before it may influence allocation."
            ),
        },
    }


def _parse_requested_at(value: str | None):
    """Parse a customer/request timestamp into the naive local wall-clock form
    consumed by provider_slot_service.

    Home Services providers and customers currently share the configured
    market timezone. An explicit numeric offset is preserved as its wall-clock
    value instead of being silently converted to the API server timezone.
    """
    if not value:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


async def _recent_allocation_counts(
    db: AsyncSession, tenant_ids: set[uuid.UUID], *, offering_id: uuid.UUID,
    city: str, zipcode: str | None, days: int = 7,
) -> dict[uuid.UUID, int]:
    """Count geographic allocations across services without draft pollution.

    Confirmed ``service_jobs`` are the durable seven-day ledger. Very recent
    matching decisions act as short soft reservations so concurrent chats do
    not all select the same provider; abandoned drafts stop affecting routing
    after fifteen minutes.
    """
    if not tenant_ids:
        return {}
    from sqlalchemy import text
    rows = (await db.execute(text(
        "SELECT provider_id, count(*) AS n FROM ("
        "  SELECT tenant_id::text AS provider_id FROM service_jobs "
        "  WHERE created_at >= now() - (:days * interval '1 day') "
        "  AND created_at < now() - (:hold_minutes * interval '1 minute') "
        "  AND tenant_id::text = ANY(CAST(:tenant_ids AS text[])) "
        "  AND ((:zipcode IS NOT NULL AND zipcode = :zipcode) "
        "    OR (:zipcode IS NULL AND lower(COALESCE(city,'')) = :city)) "
        "  UNION ALL "
        "  SELECT DISTINCT ON (COALESCE(NULLIF(new_value->>'draft_id',''), entity_id::text)) "
        "    new_value->>'selected_provider_id' AS provider_id "
        "  FROM master_data_audit_log "
        "  WHERE entity_type='matching_decision' AND action='production_match' "
        "  AND created_at >= now() - (:hold_minutes * interval '1 minute') "
        "  AND ((:zipcode IS NOT NULL AND new_value->>'zipcode' = :zipcode) "
        "    OR (:zipcode IS NULL AND lower(COALESCE(new_value->>'city','')) = :city)) "
        "  AND new_value->>'selected_provider_id' = ANY(CAST(:tenant_ids AS text[])) "
        "  ORDER BY COALESCE(NULLIF(new_value->>'draft_id',''), entity_id::text), created_at DESC "
        ") AS allocations GROUP BY provider_id"
    ), {
        "days": days,
        "hold_minutes": ALLOCATION_HOLD_MINUTES,
        "city": city.strip().lower(),
        "zipcode": zipcode,
        "tenant_ids": [str(tenant_id) for tenant_id in tenant_ids],
    })).fetchall()
    return {
        uuid.UUID(str(row.provider_id)): int(row.n or 0)
        for row in rows if row.provider_id
    }


def _fair_share_scores(
    tenant_ids: set[uuid.UUID], allocation_counts: dict[uuid.UUID, int],
) -> dict[uuid.UUID, float]:
    """Translate recent allocation deficit into a 0-100 score.

    Equal history is neutral. Once a provider receives work, providers with a
    lower count receive the boost, naturally rotating comparable candidates.
    """
    if not tenant_ids:
        return {}
    counts = {tenant_id: allocation_counts.get(tenant_id, 0) for tenant_id in tenant_ids}
    low, high = min(counts.values()), max(counts.values())
    if low == high:
        return {tenant_id: 50.0 for tenant_id in tenant_ids}
    span = high - low
    return {
        tenant_id: round((high - count) * 100.0 / span, 2)
        for tenant_id, count in counts.items()
    }


async def _service_reliability_score(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    offering_id: uuid.UUID,
    job_type_id: uuid.UUID | None,
) -> dict[str, float | int]:
    """Bayesian exact-service reliability from canonical Home Service records.

    Ten historical-equivalent jobs at a 70% completion / 90% non-cancellation
    prior prevent both cold-start perfection and cold-start punishment. Rating
    uses five prior reviews at 4/5. Real evidence gradually dominates.
    """
    from sqlalchemy import text
    params = {
        "tid": str(tenant_id), "oid": str(offering_id),
        "jtid": str(job_type_id) if job_type_id else None,
    }
    row = (await db.execute(text(
        "SELECT count(*) FILTER (WHERE status IN ('completed','invoice_issued','force_closed')) AS completed, "
        "count(*) FILTER (WHERE status IN ('cancelled','voided')) AS cancelled "
        "FROM service_jobs WHERE tenant_id=CAST(:tid AS uuid) "
        "AND offering_id=CAST(:oid AS uuid) "
        "AND (CAST(:jtid AS uuid) IS NULL OR job_type_id=CAST(:jtid AS uuid)) "
        "AND created_at >= now() - interval '90 days'"
    ), params)).one()
    completed = int(row.completed or 0)
    cancelled = int(row.cancelled or 0)
    terminal = completed + cancelled

    prior_jobs = 10.0
    completion = (completed + 0.70 * prior_jobs) * 100.0 / (terminal + prior_jobs)
    non_cancel = (completed + 0.90 * prior_jobs) * 100.0 / (terminal + prior_jobs)

    review = (await db.execute(text(
        "SELECT avg(overall_rating) AS average, count(*) AS n FROM customer_reviews "
        "WHERE tenant_id=CAST(:tid AS uuid) AND offering_id=CAST(:oid AS uuid) "
        "AND status='approved' AND hidden_at IS NULL"
    ), params)).one()
    review_count = int(review.n or 0)
    rating_total = float(review.average or 0.0) * review_count
    rating_score = (rating_total + 4.0 * 5.0) * 20.0 / (review_count + 5.0)

    score = completion * 0.60 + non_cancel * 0.25 + rating_score * 0.15
    return {
        "score": round(score, 2),
        "completion_score": round(completion, 2),
        "cancellation_score": round(non_cancel, 2),
        "rating_score": round(rating_score, 2),
        "sample_size": terminal,
    }


def _slot_fit_score(slot: dict) -> float:
    days_ahead = max(0, int(slot.get("days_ahead") or 0))
    freshness = max(20.0, 100.0 - days_ahead * 15.0)
    capacity = max(1, int(slot.get("capacity") or 1))
    available = max(0, int(slot.get("available_slots") or 0))
    room = min(100.0, available * 100.0 / capacity)
    return round(freshness * 0.80 + room * 0.20, 2)


def _live_capacity_score(slot: dict) -> float:
    capacity = max(1, int(slot.get("capacity") or 1))
    available = max(0, int(slot.get("available_slots") or 0))
    return round(min(100.0, available * 100.0 / capacity), 2)


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
    job_type_id: uuid.UUID | None = None,
    serialize_allocation: bool = False,
    exclude_tenant_id: uuid.UUID | None = None,
    exclude_tenant_ids: set[uuid.UUID] | None = None,
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

    # MODULE-L5-02: defensive — city can be None if the draft has no address yet;
    # never AttributeError here (the service layer also validates upstream).
    norm_city = (city or "").strip().lower()
    strip_zip = zipcode.strip() if zipcode else None

    # Base candidate pool: one deterministic row per tenant. Joining raw areas
    # previously duplicated providers with multiple matching coverage rows and
    # applied an unordered LIMIT 25, making both counts and selection unstable.
    excluded_ids = set(exclude_tenant_ids or set())
    if exclude_tenant_id is not None:
        excluded_ids.add(exclude_tenant_id)
    base_rows = (await db.execute(
        select(
            Tenant.id.label("tenant_id"),
            Tenant.business_name.label("business_name"),
            Tenant.tenant_name.label("tenant_name"),
            Tenant.health_score.label("health_score"),
            Tenant.rating_average.label("rating"),
            func.bool_or(TenantServiceArea.zipcode == strip_zip).label("exact_zip"),
        )
        .join(TenantServiceArea, TenantServiceArea.tenant_id == Tenant.id)
        .where(
            Tenant.status == "active",
            Tenant.vertical == "home_services",
            Tenant.suspended_at.is_(None),
            Tenant.id.notin_(excluded_ids) if excluded_ids else True,
            # NOTE: tenants.category_id is unreliably NULL on real seeded
            # tenants (same gap found and worked around in the My Offerings
            # sprint) — vertical is the correct, populated gate; category_id
            # is intentionally not filtered on here.
            TenantServiceArea.is_active.is_(True),
            # A zipcode is already a unique, authoritative geographic
            # identifier -- requiring the free-text `city` column to ALSO
            # match exactly excluded a real, active tenant whose coverage
            # area was stored as "BASSIPATHANA" while the customer's own
            # address city was "Bassi Pathana" (same bug fixed in
            # HomeServiceServiceabilityService.check; that fix alone wasn't
            # enough because this is a second, independent query with the
            # same city-equality mistake -- confirmed live: serviceability
            # reported serviceable=True but match-and-price still excluded
            # the same tenant from its own candidate pool). A zipcode match
            # is accepted on its own; city match remains the fallback for
            # when no zipcode was supplied.
            or_(
                func.lower(TenantServiceArea.city) == norm_city,
                TenantServiceArea.zipcode == strip_zip,
            ) if strip_zip else func.lower(TenantServiceArea.city) == norm_city,
        )
        .group_by(
            Tenant.id, Tenant.business_name, Tenant.tenant_name,
            Tenant.health_score, Tenant.rating_average,
        )
        .order_by(Tenant.id.asc())
        .limit(limit_candidates)
    )).all()

    candidate_ids = {row.tenant_id for row in base_rows}
    if not candidate_ids:
        return {"signals": None, "score": None, "candidate_count": 0, "excluded_count": 0, "excluded_providers": []}

    exact_zip_ids = {row.tenant_id for row in base_rows if strip_zip and row.exact_zip}

    # FINAL-L5-04C — tenant category entitlement, resolved ONCE for every
    # candidate in a single bulk query (not one query per candidate — see
    # EntitlementService.get_entitled_tenant_ids_for_category()). offering_id
    # is always a master_service_id (confirmed at both call sites); its
    # service_group_id is the entitlement-gated category.
    entitled_tenant_ids: set[uuid.UUID] | None = None
    from app.engines.admin_catalog.models import MasterService
    from app.engines.entitlement.service import entitlement_service
    svc_group_row = (await db.execute(
        select(MasterService.service_group_id).where(MasterService.id == offering_id)
    )).scalar_one_or_none()
    if svc_group_row:
        entitled_tenant_ids = await entitlement_service.get_entitled_tenant_ids_for_category(
            db, svc_group_row, tenant_ids=list(candidate_ids)
        )

    signals_list: list[CandidateSignals] = []
    excluded = 0
    excluded_providers: list[dict] = []

    # Existing production decisions form the fair-share ledger. Diagnostics do
    # not influence it. A failed audit lookup degrades to equal neutral shares;
    # it must never stop a customer booking.
    if serialize_allocation:
        from sqlalchemy import text
        # One lock per geographic market, not per service. Otherwise two
        # simultaneous bookings for different services can both see the same
        # zero-count tie and choose the same provider.
        market_key = f"home-service-match:{strip_zip or norm_city}"
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:market_key, 0))"),
            {"market_key": market_key},
        )
    try:
        async with db.begin_nested():
            allocation_counts = await _recent_allocation_counts(
                db, candidate_ids, offering_id=offering_id, city=norm_city,
                zipcode=strip_zip,
            )
    except Exception as exc:  # noqa: BLE001 -- fairness telemetry is fail-open
        import structlog
        structlog.get_logger("home_service_booking.matching").warning(
            "matching.fair_share_history_unavailable", error=str(exc),
        )
        allocation_counts = {}
    fair_share_scores = _fair_share_scores(candidate_ids, allocation_counts)

    for row in base_rows:
        tid = row.tenant_id
        if entitled_tenant_ids is not None and tid not in entitled_tenant_ids:
            excluded += 1
            excluded_providers.append({
                "provider_name": row.business_name or row.tenant_name or "Service Provider",
                "reason_code": "TENANT_CATEGORY_NOT_ENTITLED",
            })
            continue
        eligible, reason_code = await _passes_full_eligibility_gate(
            db, tenant_id=tid, offering_id=offering_id,
            offering_type_id=offering_type_id, brand_id=brand_id,
            zipcode=strip_zip, requested_at=requested_at, job_type_id=job_type_id,
        )
        if not eligible:
            excluded += 1
            excluded_providers.append({
                "provider_name": row.business_name or row.tenant_name or "Service Provider",
                "reason_code": reason_code,
            })
            continue

        is_exact_zip = tid in exact_zip_ids
        health_score, health_source, health_calc_at, health_bookable = await _canonical_health_score(
            db, tid, float(row.health_score) if row.health_score is not None else None,
        )
        if health_source == "canonical" and not health_bookable:
            excluded += 1
            excluded_providers.append({
                "provider_name": row.business_name or row.tenant_name or "Service Provider",
                "reason_code": "HEALTH_BAND_NOT_BOOKABLE",
            })
            continue
        # Capacity is a hard feasibility gate, not something quality can
        # compensate for. The provider is scored only after a real slot exists.
        from app.engines.home_service_booking.provider_slot_service import (
            find_earliest_available_slot,
        )
        from_datetime = _parse_requested_at(requested_at)
        earliest_slot = await find_earliest_available_slot(
            db,
            tenant_id=tid,
            from_datetime=from_datetime,
            master_service_id=offering_id,
            job_type_id=job_type_id,
        )
        if earliest_slot is None:
            excluded += 1
            excluded_providers.append({
                "provider_name": row.business_name or row.tenant_name or "Service Provider",
                "reason_code": "NO_LIVE_SLOT_CAPACITY",
            })
            continue

        reliability = await _service_reliability_score(
            db, tid, offering_id=offering_id, job_type_id=job_type_id,
        )
        slot_fit = _slot_fit_score(earliest_slot)
        capacity = _live_capacity_score(earliest_slot)
        allocation_weight = health_allocation_weight(health_score)
        allocation_finish = _d(allocation_counts.get(tid, 0) + 1) / allocation_weight
        signals_list.append(CandidateSignals(
            tenant_id=str(tid),
            provider_name=row.business_name or row.tenant_name or "Service Provider",
            health_score=health_score,
            health_score_source=health_source,
            health_score_calculated_at=health_calc_at,
            job_completion_score=reliability["completion_score"],
            rating_score=reliability["rating_score"],
            availability_score=slot_fit,
            service_match_score=100.0 if (offering_type_id or brand_id) else 80.0,
            distance_score=100.0 if is_exact_zip else 60.0,
            cancellation_score=reliability["cancellation_score"],
            capacity_score=capacity,
            service_reliability_score=reliability["score"],
            slot_fit_score=slot_fit,
            fair_share_score=fair_share_scores.get(tid, 50.0),
            reliability_sample_size=reliability["sample_size"],
            recent_allocations=allocation_counts.get(tid, 0),
            allocation_weight=float(_round2(allocation_weight)),
            allocation_finish_position=float(_round2(allocation_finish)),
            earliest_slot=earliest_slot,
            public_badges=await _public_badges(db, tid, row.health_score, row.rating),
            rating=float(row.rating) if row.rating else None,
        ))

    if not signals_list:
        return {"signals": None, "score": None, "candidate_count": len(base_rows), "excluded_count": excluded,
                "excluded_providers": excluded_providers}

    best = select_best_candidate(signals_list)
    ranked = rank_candidates(signals_list)
    # Keep the actual selected provider first in diagnostics. Candidates that
    # missed the quality peer band remain visible afterwards for transparency.
    ordered = [best] + [pair for pair in ranked if pair[0].tenant_id != best[0].tenant_id]
    return {
        "signals": best[0], "score": best[1],
        "earliest_slot": best[0].earliest_slot,
        "candidate_count": len(base_rows), "excluded_count": excluded,
        "excluded_providers": excluded_providers,
        "all_scored": ordered,
    }


async def _passes_full_eligibility_gate(
    db: AsyncSession, *, tenant_id: uuid.UUID, offering_id: uuid.UUID,
    offering_type_id: uuid.UUID | None, brand_id: uuid.UUID | None,
    zipcode: str | None = None, requested_at: str | None = None,
    job_type_id: uuid.UUID | None = None,
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

    # 0. MODULE-L5-58 — exact Job-Type Blueprint gate. When the caller has
    # resolved an exact job_type_id (the canonical Business Vertical ->
    # Service Group -> Master Service -> Job Type -> Job-Type Blueprint
    # chain), the tenant must have that exact job type active as a child of
    # this Master Service (master_service_job_types) -- matching by
    # master_service_id alone is not sufficient once a service has multiple
    # job types (e.g. AC Repair vs AC Installation must resolve
    # independently). Skipped (not guessed) when the caller has no exact
    # job_type_id yet -- never invents or assumes one.
    from app.engines.admin_catalog.models import MasterServiceJobType, TenantService
    if job_type_id is not None:
        link = (await db.execute(
            select(MasterServiceJobType.id).where(
                MasterServiceJobType.master_service_id == offering_id,
                MasterServiceJobType.job_type_id == job_type_id,
                MasterServiceJobType.is_active.is_(True),
            )
        )).scalar_one_or_none()
        if link is None:
            return False, "EXACT_JOB_TYPE_NOT_SUPPORTED"
        tenant_offering = (await db.execute(
            select(TenantService.id).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == offering_id,
                TenantService.job_type_id == job_type_id,
                TenantService.is_active.is_(True),
                TenantService.is_enabled.is_(True),
                TenantService.setup_status == "published",
            ).limit(1)
        )).scalar_one_or_none()
        if tenant_offering is None:
            return False, "EXACT_JOB_TYPE_NOT_PUBLISHED"

    # A tenant-wide bookability flag cannot prove that this specific service
    # is published. Coverage rows are deliberately retained across draft/
    # retirement transitions, so they are not publication evidence either.
    # Matching therefore requires one active, enabled, published tenant
    # service for the exact master service (and exact job type when known).
    tenant_service_filters = [
        TenantService.tenant_id == tenant_id,
        TenantService.master_service_id == offering_id,
        TenantService.is_active.is_(True),
        TenantService.is_enabled.is_(True),
        TenantService.setup_status == "published",
    ]
    if job_type_id is not None:
        tenant_service_filters.append(TenantService.job_type_id == job_type_id)
    published_offering_id = (await db.execute(
        select(TenantService.id).where(*tenant_service_filters).limit(1)
    )).scalar_one_or_none()
    if published_offering_id is None:
        return False, "OFFERING_NOT_PUBLISHED"

    # Area-wide wildcard coverage must not widen the exact offering's type /
    # brand selection. Reuse the same policy as tenant setup and pricing.
    if offering_type_id or brand_id:
        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        offering = await db.get(TenantService, published_offering_id)
        catalog = TenantCatalogService(db, request_id="matching")
        if offering_type_id and not await catalog.is_type_supported(offering, offering_type_id):
            return False, "TYPE_NOT_SUPPORTED"
        if brand_id and not await catalog.is_brand_supported(offering, brand_id, offering_type_id):
            return False, "BRAND_NOT_SUPPORTED"

    # 1. Canonical bookability (HS4B) — single source of truth.
    bookable_row = (await db.execute(text(
        "SELECT is_bookable, bookability_blockers FROM provider_visibility_statuses WHERE tenant_id=:tid "
        "AND category_id IS NULL ORDER BY created_at DESC, id DESC LIMIT 1"
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

    # Money moves independently of the cached visibility projection. Read the
    # canonical balance at the actual matching decision so a provider whose
    # latest deduction took them below the Rs.500 policy floor cannot receive
    # one more job during the interval before visibility refreshes.
    from app.engines.vertical_catalog.seat_enforcement import get_credit_state
    credit_state = await get_credit_state(db, tenant_id)
    if credit_state["below_floor"]:
        return False, "INSUFFICIENT_USAGE_CREDITS"

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

    # MODULE-L5-02: a service-level coverage row (service_type_id / brand_id NULL)
    # covers ANY type/brand. The exact-match-only check here, combined with the
    # add_service_mapping duplicate constraint on (area, service, job_type) —
    # which blocks adding a type/brand-specific row alongside a service-level one
    # — meant a brand- or type-required service with only service-level coverage
    # could NEVER match (BRAND_NOT_COVERED / TYPE_NOT_COVERED), so it was never
    # bookable. Treat NULL (service-level) coverage as a wildcard.
    if offering_type_id:
        type_row = (await db.execute(text(
            "SELECT count(*) FROM tenant_service_area_services tsas "
            "JOIN tenant_service_areas tsa ON tsa.id = tsas.tenant_service_area_id "
            "WHERE tsas.tenant_id=:tid AND tsas.service_id=:oid "
            "AND (tsas.service_type_id=:stid OR tsas.service_type_id IS NULL) "
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
            "WHERE tsas.tenant_id=:tid AND tsas.service_id=:oid "
            "AND (tsas.brand_id=:bid OR tsas.brand_id IS NULL) "
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

    # 4. Pricing exists for this service -- either a real, positive
    # tenant-owned price (TenantService.tenant_base_price/tenant_min_price,
    # this tenant's OWN configured number) or a real, positive global
    # ServicePricingRule. Real defect fixed here: this previously only
    # checked that a ServicePricingRule ROW EXISTED (any `is_active` row,
    # even one with `base_price=0.00`) and never even looked at whether the
    # candidate tenant had its own price configured at all -- Guramrit's
    # AC Installation offering has a real, positive tenant price
    # (tenant_min_price=1200) but was excluded from matching entirely
    # because the global admin ServicePricingRule for that offering has
    # base_price=0.00. An inspection-mode offering (requires_inspection_
    # estimate) is priced via its visit fee, never this fixed/range rule at
    # all -- checked first so a real inspection offering with no
    # ServicePricingRule/TenantService price row is never wrongly excluded.
    offering_row = (await db.execute(text(
        "SELECT ms.pricing_model, ms.visit_fee, sjw.pricing_behavior "
        "FROM master_services ms LEFT JOIN service_job_workflow sjw "
        "ON sjw.master_service_id=ms.id AND sjw.job_type_id=:jtid "
        "AND sjw.is_current=true AND sjw.status='published' WHERE ms.id=:oid"
    ), {"oid": str(offering_id), "jtid": str(job_type_id) if job_type_id else None})).fetchone()
    effective_behavior = offering_row[2] if offering_row and offering_row[2] else (offering_row[0] if offering_row else None)
    is_inspection_offering = effective_behavior in {"visit_fee_plus_quote", "inspection_required", "custom_quote"}
    if is_inspection_offering:
        # An inspection-mode offering is priced by its VISIT FEE. That fee is
        # tenant-owned exactly like the fixed-price branch below: the admin API
        # refuses to write master_services.visit_fee at all
        # (ADMIN_PRICING_NOT_ALLOWED — "Price is tenant-owned (Tenant Setup >
        # Pricing)"). This branch used to read only the admin column, so a
        # tenant who had correctly set tenant_visit_fee still failed the gate,
        # and no one was permitted to set the field that would have passed it —
        # making every inspection_required / visit_fee_plus_quote / custom_quote
        # service permanently unbookable on every channel. Confirmed live: the
        # customer got "No eligible providers available in <city>. Try a nearby
        # city." for a pricing-configuration problem that no city change fixes.
        # Now prefers the tenant's own fee and falls back to the master column.
        tenant_fee_sql = (
            "SELECT tenant_visit_fee FROM tenant_services "
            "WHERE tenant_id=:tid AND master_service_id=:oid "
            + ("AND job_type_id=:jtid " if job_type_id else "")
            + "AND is_active=true AND is_enabled=true AND setup_status='published' LIMIT 1"
        )
        tenant_fee_params = {"tid": str(tenant_id), "oid": str(offering_id)}
        if job_type_id:
            tenant_fee_params["jtid"] = str(job_type_id)
        tenant_fee_row = (await db.execute(
            text(tenant_fee_sql), tenant_fee_params,
        )).fetchone()
        has_visit_fee = bool(tenant_fee_row and tenant_fee_row[0] and float(tenant_fee_row[0]) > 0)             or bool(offering_row and offering_row[1] and float(offering_row[1]) > 0)
        if not has_visit_fee:
            return False, "NO_VALID_PRICE_RULE"
    else:
        tenant_price_sql = (
            "SELECT tenant_base_price, tenant_min_price FROM tenant_services "
            "WHERE tenant_id=:tid AND master_service_id=:oid "
            + ("AND job_type_id=:jtid " if job_type_id else "")
            + "AND is_active=true AND is_enabled=true AND setup_status='published' LIMIT 1"
        )
        tenant_price_params = {"tid": str(tenant_id), "oid": str(offering_id)}
        if job_type_id:
            tenant_price_params["jtid"] = str(job_type_id)
        tenant_price_row = (await db.execute(
            text(tenant_price_sql), tenant_price_params,
        )).fetchone()
        has_tenant_price = bool(
            tenant_price_row and (
                (tenant_price_row[0] and float(tenant_price_row[0]) > 0)
                or (tenant_price_row[1] and float(tenant_price_row[1]) > 0)
            )
        )
        if not has_tenant_price:
            pricing_row = (await db.execute(text(
                "SELECT id FROM service_pricing_rules "
                "WHERE master_service_id=:oid AND is_active=true AND base_price > 0 LIMIT 1"
            ), {"oid": str(offering_id)})).fetchone()
            if not pricing_row:
                return False, "NO_VALID_PRICE_RULE"

    return True, None


# MODULE-L5-58: missing-signal policy for Trust & Quality's canonical
# HealthScore. A missing, unbanded or stale result is treated as unassessed.
# The legacy tenants.health_score column historically defaulted to 100 and is
# therefore never valid allocation evidence.
HEALTH_SCORE_STALE_AFTER_DAYS = 30
MISSING_HEALTH_SCORE_DEFAULT = 65.0  # neutral monitored-provider prior


async def _canonical_health_score(
    db: AsyncSession, tenant_id: uuid.UUID, legacy_fallback: float | None,
) -> tuple[float, str, str | None, bool]:
    """Reads the canonical Trust & Quality HealthScore for this provider
    (target_type='tenant', matching the convention TrustQualityService's own
    badge lookups already use — see _public_badges). This is the SAME table
    the /admin/trust-quality console reads and writes; matching never
    computes or stores a second trust number.

    Returns (score, source, calculated_at_iso, bookable_allowed) where source is:
      "canonical"          -- a fresh, banded active-formula row exists
      "unassessed_default" -- missing/stale/unbanded; neutral prior used

    ``legacy_fallback`` remains in the signature for API compatibility but is
    intentionally ignored. That column's historical default is indistinguish-
    able from an earned perfect score.
    """
    from app.engines.trust_quality.provider_health import get_provider_health_snapshot

    snapshot = await get_provider_health_snapshot(
        db, tenant_id, max_age_days=HEALTH_SCORE_STALE_AFTER_DAYS,
    )
    return (
        float(snapshot["score"]),
        snapshot["source"],
        snapshot["calculated_at"] if snapshot["source"] == "canonical" else None,
        bool(snapshot["bookable_allowed"]),
    )


async def _public_badges(db: AsyncSession, tenant_id: uuid.UUID, health_score, rating) -> list[dict]:
    """The customer-visible badges shown on a provider card.

    Prefers the provider's real, admin-configured trust_quality badges (with the
    icon/colour the admin set). Falls back to computed signals only when the
    provider has not earned any configured badge yet, so a card is never empty.

    Collapsed by DISPLAY NAME, not by badge key. `list_earned_badges` already
    dedupes by key, which is right for an admin view -- two definitions are two
    records. To a customer they are one claim, and the same word repeated is not
    five reasons to trust someone. Live case this fixes: Guramrit held five
    separately-keyed definitions all named "L5 Cfg Badge", so the booking card
    printed that label five times in a row (and, keyed on the name, collided in
    the app's list rendering).

    The first of a repeated name wins, so the icon/colour stay those of the
    most-recently-earned one -- `list_earned_badges` returns newest first.

    The provider's STANDING leads the list when they have earned a level (see
    provider_standing). It is the one claim compact surfaces show on its own, so it
    must never be the entry that falls off the end of the cap.
    """
    from app.engines.trust_quality.service import TrustQualityService
    from app.engines.trust_quality.provider_standing import resolve_standing_badge

    standing = await resolve_standing_badge(db, tenant_id)
    try:
        earned = await TrustQualityService(db, None, "public").list_earned_badges(
            "tenant", tenant_id, "customer")
    except Exception:  # badge lookup must never break provider matching
        earned = []
    if standing or earned:
        by_name: dict[str, dict] = {}
        if standing:
            by_name[standing["name"]] = standing
        for b in earned:
            name = (b.get("name") or "").strip()
            # An unnamed badge has nothing to show a customer.
            if not name or name in by_name:
                continue
            by_name[name] = {"name": name, "icon": b.get("icon"), "color": b.get("color")}
        if by_name:
            return list(by_name.values())[:MAX_PUBLIC_BADGES]

    # INTEGRITY FIX. The previous fallback added "Verified" UNCONDITIONALLY and
    # "High Completion" from `health_score >= 90` -- but health_score defaults to
    # 100 for a brand-new tenant with no history at all. Live result: Guramrit
    # showed a customer "Verified · High Completion" while its
    # verification_status was 'not_started' and it had completed ZERO jobs.
    #
    # A badge is a claim the platform makes on a provider's behalf. Fabricating
    # one is worse than showing none: it is the assurance a customer relies on
    # when letting a stranger into their home. Every badge below is now tied to
    # a fact that can be pointed at in the database.
    return await _earned_fallback_badges(db, tenant_id, rating)


# A card shows a handful of claims, not a wall of them. Beyond this the badges stop
# distinguishing one provider from another and start reading as decoration.
MAX_PUBLIC_BADGES = 3

# Enough reviews that an average means something, rather than one happy customer.
_MIN_REVIEWS_FOR_RATING_BADGE = 3
# Enough finished work that a completion rate is not noise.
_MIN_JOBS_FOR_COMPLETION_BADGE = 5


async def _earned_fallback_badges(db: AsyncSession, tenant_id: uuid.UUID, rating) -> list[dict]:
    """Badges derived only from facts, for a provider with no admin-configured
    ones yet. Returns [] when nothing has genuinely been earned -- the card then
    says something honest about being new instead of borrowing credibility."""
    from sqlalchemy import text as _t

    badges: list[dict] = []

    # "Verified" means the platform actually verified them.
    status = (await db.execute(_t(
        "SELECT verification_status FROM tenants WHERE id = :tid"
    ), {"tid": str(tenant_id)})).scalar()
    if str(status or "").strip().lower() in ("verified", "approved", "completed"):
        badges.append({"name": "Verified", "icon": "shield-check", "color": "#3b82f6"})

    # "Highly Rated" needs a real average over a meaningful number of reviews.
    review_row = (await db.execute(_t(
        "SELECT count(*) AS n, avg(overall_rating) AS avg_rating "
        "FROM customer_reviews WHERE tenant_id = :tid AND status = 'approved'"
    ), {"tid": str(tenant_id)})).first()
    review_count = int(review_row._mapping["n"] or 0) if review_row else 0
    avg_rating = review_row._mapping["avg_rating"] if review_row else None
    if review_count >= _MIN_REVIEWS_FOR_RATING_BADGE and avg_rating and float(avg_rating) >= 4.5:
        badges.append({"name": "Highly Rated", "icon": "star", "color": "#f59e0b"})

    # "High Completion" needs real finished jobs, not a default score.
    job_row = (await db.execute(_t(
        "SELECT count(*) FILTER (WHERE status = 'completed') AS done, "
        "       count(*) FILTER (WHERE status IN ('cancelled','failed')) AS lost "
        "FROM service_jobs WHERE tenant_id = :tid"
    ), {"tid": str(tenant_id)})).first()
    done = int(job_row._mapping["done"] or 0) if job_row else 0
    lost = int(job_row._mapping["lost"] or 0) if job_row else 0
    if done >= _MIN_JOBS_FOR_COMPLETION_BADGE and done / max(1, done + lost) >= 0.9:
        badges.append({"name": "High Completion", "icon": "check-circle", "color": "#10b981"})

    return badges[:MAX_PUBLIC_BADGES]


async def customer_provider_facts(
    db: AsyncSession, tenant_id: uuid.UUID, *, offering_id: uuid.UUID | None = None,
) -> dict:
    """Real, customer-relevant facts about a provider, for the booking card.

    Everything here is a counted or stored fact. Deliberately EXCLUDES the
    internal score and its sub-scores (hard gate 9) -- and also excludes
    `tenants.health_score`, which is an internal quality metric that defaults to
    100 and would read to a customer as an earned rating.

    A field is None/0 when there is genuinely nothing to show, so the UI can
    stay silent rather than dress up an absence.
    """
    from sqlalchemy import text as _t

    row = (await db.execute(_t(
        "SELECT verification_status, city, created_at, activated_at "
        "FROM tenants WHERE id = :tid"
    ), {"tid": str(tenant_id)})).first()
    m = row._mapping if row else {}

    reviews = (await db.execute(_t(
        "SELECT count(*) AS n, avg(overall_rating) AS avg_rating "
        "FROM customer_reviews WHERE tenant_id = :tid AND status = 'approved'"
    ), {"tid": str(tenant_id)})).first()
    review_count = int(reviews._mapping["n"] or 0) if reviews else 0
    avg_rating = reviews._mapping["avg_rating"] if reviews else None

    jobs = (await db.execute(_t(
        "SELECT count(*) FILTER (WHERE status = 'completed') AS done, "
        "       count(*) FILTER (WHERE status IN ('cancelled','failed')) AS lost "
        "FROM service_jobs WHERE tenant_id = :tid"
    ), {"tid": str(tenant_id)})).first()
    done = int(jobs._mapping["done"] or 0) if jobs else 0
    lost = int(jobs._mapping["lost"] or 0) if jobs else 0

    # How the approved reviews are distributed. A customer reads "18 of 20 gave
    # 5 stars" very differently from a bare 4.6, and it is a plain count -- no
    # weighting, no scoring.
    breakdown_rows = (await db.execute(_t(
        "SELECT overall_rating AS stars, count(*) AS n "
        "FROM customer_reviews WHERE tenant_id = :tid AND status = 'approved' "
        "GROUP BY overall_rating"
    ), {"tid": str(tenant_id)})).all()
    breakdown = {str(star): 0 for star in range(5, 0, -1)}
    for row in breakdown_rows:
        stars = int(row._mapping["stars"] or 0)
        if 1 <= stars <= 5:
            breakdown[str(stars)] = int(row._mapping["n"] or 0)

    # A few real, publicly visible comments in the customer's own words. Only
    # approved AND public (an approved-but-hidden review is not ours to show),
    # and never the reviewer's identity -- the customer sees what was said, not
    # who said it.
    recent_rows = (await db.execute(_t(
        "SELECT overall_rating AS stars, review_title, review_text, created_at "
        "FROM customer_reviews "
        "WHERE tenant_id = :tid AND status = 'approved' AND visibility = 'public' "
        "  AND review_text IS NOT NULL AND btrim(review_text) <> '' "
        "ORDER BY created_at DESC LIMIT 3"
    ), {"tid": str(tenant_id)})).all()
    recent_reviews = [{
        "rating": int(r._mapping["stars"] or 0),
        "title": (r._mapping["review_title"] or None),
        "text": r._mapping["review_text"].strip(),
        "created_at": r._mapping["created_at"].isoformat() if r._mapping["created_at"] else None,
    } for r in recent_rows]

    # Completed jobs for THIS service, which is what the customer is actually
    # buying -- a general total says nothing about whether they have done this
    # particular job before. Omitted (None) when no offering was supplied,
    # rather than silently reported as 0.
    offering_done = None
    if offering_id is not None:
        offering_row = (await db.execute(_t(
            "SELECT count(*) AS n FROM service_jobs "
            "WHERE tenant_id = :tid AND offering_id = :oid AND status = 'completed'"
        ), {"tid": str(tenant_id), "oid": str(offering_id)})).first()
        offering_done = int(offering_row._mapping["n"] or 0) if offering_row else 0

    since = m.get("activated_at") or m.get("created_at")
    verified = str(m.get("verification_status") or "").strip().lower() in (
        "verified", "approved", "completed")

    return {
        "rating_breakdown": breakdown,
        "recent_reviews": recent_reviews,
        "jobs_completed_for_service": offering_done,
        "verified": verified,
        # Only a rating backed by real approved reviews. An average of zero
        # reviews is not "0 stars", it is "no rating yet".
        "rating": round(float(avg_rating), 1) if (review_count and avg_rating) else None,
        "review_count": review_count,
        "jobs_completed": done,
        # Withheld until there is enough finished work for a percentage to mean
        # anything, rather than showing "100%" off a single job.
        "completion_rate": (
            round(done / (done + lost) * 100) if done + lost >= _MIN_JOBS_FOR_COMPLETION_BADGE else None
        ),
        "on_platform_since": since.isoformat() if since else None,
        "city": m.get("city"),
        # True when this provider genuinely has no track record yet, so the card
        # can say so plainly instead of implying experience it does not have.
        "is_new": review_count == 0 and done == 0,
    }


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
        JOIN LATERAL (
            SELECT is_bookable
            FROM provider_visibility_statuses
            WHERE tenant_id = t.id AND category_id IS NULL
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        ) pvs ON true
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
