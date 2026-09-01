"""Trust & Quality Engine service — Phase 1.

Implements the Badge Rule Engine (criteria evaluation, simulate, award/revoke)
and the Health Rule Engine (weighted formula calculation, penalties, bonuses,
bands, risk level) plus a simple Risk Scoring Engine and synchronous
recalculation-job runner. Frontend/simulator UI and async job scheduling are
later phases — this phase makes the rules real and runnable.
"""
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.trust_quality.models import (
    BadgeDefinition, BadgeRule, BadgeRuleCriteria, BadgeRuleRemovalCriteria,
    BadgeAssignment, HealthFormula, HealthFormulaComponent, HealthPenaltyRule,
    HealthBonusRule, HealthBandRule, HealthScore, RiskRule, RiskScore,
    TrustQualityRecalculationJob, TrustQualityAuditLog,
)
from app.exceptions import ServiceOSException

# Where a recalculation job finds the rows for each target_type. The badge engine
# and the health engine name the same entity differently ("tenant" vs
# "tenant_provider"), so both spellings map to the tenants table. Every statement
# ends in a WHERE so _enumerate_targets can append a scope filter with AND.
_TARGET_SOURCE_SQL: dict[str, str] = {
    "tenant":           "SELECT id FROM tenants WHERE status = 'active'",
    "tenant_provider":  "SELECT id FROM tenants WHERE status = 'active'",
    "staff":            "SELECT id FROM users WHERE role = 'staff' AND deleted_at IS NULL",
    "technician":       "SELECT id FROM users WHERE role = 'staff' AND deleted_at IS NULL",
    "customer_account": "SELECT id FROM users WHERE role = 'customer' AND deleted_at IS NULL",
}

# A job that reached delivery vs one that never did. Both sets are terminal, and
# together they form the denominator for completion/cancellation/complaint rates.
_JOB_DONE_STATUSES = ("completed", "invoice_issued", "force_closed")
_JOB_CANCELLED_STATUSES = ("cancelled", "voided")

# How much of a formula's total weight must be measurable before its score is
# trustworthy enough to put a target into a band. See _calc_score.
_MIN_HEALTH_COVERAGE_PERCENT = 50.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Badges are customer-facing trust markers, so the catalog is intentionally
# fixed. Admins can configure the rules that award them, but cannot mint
# arbitrary new badge identities that would fragment customer understanding.
VALID_BADGE_TARGETS = {"tenant", "staff", "technician"}
VALID_BADGE_RULE_TYPES = {
    "auto_award", "manual_award", "hybrid", "seasonal", "quality_based",
    "performance_based", "verification_based", "subscription_based", "compliance_based",
}
VALID_SCOPES = {"global", "vertical", "category", "service", "plan", "tenant"}
VALID_OPERATORS = {
    "equals", "not_equals", "greater_than", "greater_than_or_equal",
    "less_than", "less_than_or_equal", "between", "in", "not_in", "exists", "not_exists",
}
VALID_HEALTH_TARGETS = {
    # Provider health is consumed by matching, provider directories and the
    # command centre under the canonical ``tenant`` target. Technician health
    # is operationally useful for field-service quality. Customer health has
    # its own commerce engine, while service/category quality are analytics
    # concerns; keeping copies here produced rows with no downstream consumer.
    "tenant", "technician",
}
VALID_RISK_LEVELS = {"normal", "watchlist", "high_risk", "finance_blocked", "quality_blocked", "suspended"}
VALID_AWARD_SOURCES = {"auto_rule", "manual_admin", "system_migration", "seasonal_campaign", "appeal_approved"}

FIXED_BADGE_CATALOG: tuple[dict, ...] = (
    {
        "badge_key": "verified_provider", "name": "Verified Provider",
        "description": "Business identity, documents and owner verification are approved.",
        "target_type": "tenant", "level": 1, "customer_visible": True,
        "tenant_visible": True, "icon": "shield-check", "color": "#2563eb",
        "tone": "trust-blue",
    },
    {
        "badge_key": "fast_response", "name": "Rapid Response",
        "description": "Consistently responds quickly when customers need help.",
        "target_type": "tenant", "level": 2, "customer_visible": True,
        "tenant_visible": True, "icon": "zap", "color": "#f97316",
        "tone": "action-orange",
    },
    {
        "badge_key": "low_complaint_provider", "name": "Reliability Shield",
        "description": "Low complaint rate and dependable issue handling.",
        "target_type": "tenant", "level": 3, "customer_visible": True,
        "tenant_visible": True, "icon": "shield", "color": "#10b981",
        "tone": "reliability-green",
    },
    {
        "badge_key": "top_rated_provider", "name": "Elite Provider",
        "description": "High ratings, strong volume and excellent customer outcomes.",
        "target_type": "tenant", "level": 4, "customer_visible": True,
        "tenant_visible": True, "icon": "crown", "color": "#8b5cf6",
        "tone": "elite-violet",
    },
    {
        "badge_key": "verified_staff", "name": "Verified Staff",
        "description": "Staff profile and employment verification are complete.",
        "target_type": "staff", "level": 1, "customer_visible": False,
        "tenant_visible": True, "icon": "badge-check", "color": "#0284c7",
        "tone": "staff-blue",
    },
    {
        "badge_key": "punctual_staff", "name": "On-Time Operator",
        "description": "Strong attendance and on-time operational discipline.",
        "target_type": "staff", "level": 2, "customer_visible": False,
        "tenant_visible": True, "icon": "target", "color": "#16a34a",
        "tone": "staff-green",
    },
    {
        "badge_key": "customer_loved_staff", "name": "Customer Loved",
        "description": "Excellent customer feedback across completed jobs.",
        "target_type": "staff", "level": 3, "customer_visible": False,
        "tenant_visible": True, "icon": "heart", "color": "#ec4899",
        "tone": "staff-pink",
    },
    {
        "badge_key": "safety_champion_staff", "name": "Safety Champion",
        "description": "Clean complaint profile and dependable field conduct.",
        "target_type": "staff", "level": 4, "customer_visible": False,
        "tenant_visible": True, "icon": "trophy", "color": "#ca8a04",
        "tone": "staff-gold",
    },
    {
        "badge_key": "verified_technician", "name": "Verified Technician",
        "description": "Technician identity and required documents are verified.",
        "target_type": "technician", "level": 1, "customer_visible": True,
        "tenant_visible": True, "icon": "badge-check", "color": "#2563eb",
        "tone": "tech-blue",
    },
    {
        "badge_key": "precision_technician", "name": "Precision Pro",
        "description": "Accurate diagnosis, tidy execution and low rework.",
        "target_type": "technician", "level": 2, "customer_visible": True,
        "tenant_visible": True, "icon": "target", "color": "#0f766e",
        "tone": "tech-teal",
    },
    {
        "badge_key": "top_technician", "name": "Top Technician",
        "description": "High customer rating and strong completion performance.",
        "target_type": "technician", "level": 3, "customer_visible": True,
        "tenant_visible": True, "icon": "medal", "color": "#f59e0b",
        "tone": "tech-amber",
    },
    {
        "badge_key": "elite_technician", "name": "Elite Technician",
        "description": "Best-in-class technician performance and customer trust.",
        "target_type": "technician", "level": 4, "customer_visible": True,
        "tenant_visible": True, "icon": "gem", "color": "#7c3aed",
        "tone": "tech-violet",
    },
)
FIXED_BADGE_BY_KEY = {b["badge_key"]: b for b in FIXED_BADGE_CATALOG}
FIXED_BADGE_KEYS = set(FIXED_BADGE_BY_KEY)


def _fixed_badge_payload(row: BadgeDefinition | None, spec: dict) -> dict:
    """Return the canonical presentation for a fixed badge.

    Existing rows supply the id/status/timestamps; the customer-facing copy,
    target, icon and colour come from code so old ad-hoc edits cannot dilute the
    four-level catalog.
    """
    payload = {
        "id": str(row.id) if row else None,
        "badge_key": spec["badge_key"],
        "name": spec["name"],
        "description": spec.get("description"),
        "icon": spec.get("icon"),
        "color": spec.get("color"),
        "target_type": spec["target_type"],
        "customer_visible": spec.get("customer_visible", False),
        "tenant_visible": spec.get("tenant_visible", True),
        "admin_only": False,
        "status": row.status if row else "missing",
        "level": spec["level"],
        "tone": spec.get("tone"),
        "created_at": row.created_at.isoformat() if row and row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }
    return payload


def _evaluate_operator(actual, operator: str, expected) -> bool:
    """Evaluate a single criterion. `actual` is the metric value from the metrics dict."""
    if operator == "exists":
        return actual is not None
    if operator == "not_exists":
        return actual is None
    if actual is None:
        return False
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "greater_than":
        return actual > expected
    if operator == "greater_than_or_equal":
        return actual >= expected
    if operator == "less_than":
        return actual < expected
    if operator == "less_than_or_equal":
        return actual <= expected
    if operator == "between":
        lo, hi = expected[0], expected[1]
        return lo <= actual <= hi
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    raise ServiceOSException("VALIDATION_ERROR", f"Unknown operator '{operator}'.")


def calc_health_score(formula: HealthFormula, components: list[HealthFormulaComponent],
                      penalties: list[HealthPenaltyRule], bonuses: list[HealthBonusRule],
                      bands: list[HealthBandRule], metrics: dict) -> dict:
    """Score one target against one formula. Pure: no DB, no I/O.

    Module-level rather than a method because the batched recalculation engine
    (`recalculation.py`) evaluates thousands of targets against one preloaded
    formula and must not need a service instance — or a session — to do it.
    """
    base = float(formula.base_score)
    breakdown = []
    weighted_sum = 0.0
    scoring_weight = 0.0
    contributing_weight = 0.0
    for c in components:
        raw = metrics.get(c.metric_key)
        if raw is None:
            if not c.is_required:
                continue
            # A missing required signal contributes zero; it must never become
            # a perfect score merely because a negative-direction component
            # would invert the fabricated numeric value zero. It also does not
            # count as measured coverage, so targets with too little real data
            # remain explicitly unassessed instead of receiving a false band.
            norm = 0.0
            missing = True
        else:
            missing = False
            contributing_weight += float(c.weight_percent)
            norm = float(raw)
            lo = float(c.min_value) if c.min_value is not None else 0.0
            hi = float(c.max_value) if c.max_value is not None else 100.0
            if hi > lo:
                norm = max(0.0, min(1.0, (norm - lo) / (hi - lo))) * 100.0
            if c.direction == "negative":
                norm = 100.0 - norm
        scoring_weight += float(c.weight_percent)
        contribution = norm * float(c.weight_percent) / 100.0
        weighted_sum += contribution
        breakdown.append({"metric_key": c.metric_key, "raw_value": raw, "normalized": norm,
                           "weight_percent": float(c.weight_percent), "contribution": contribution,
                           "missing": missing})

    # Optional components whose metric is unavailable are skipped above, so
    # their weight must leave the denominator too. Scoring the weighted sum
    # straight out of 100 would cap a target at the total weight of whichever
    # metrics happen to be measurable, marking a flawless provider "at_risk"
    # purely because, say, no deposit score exists yet. So renormalise over
    # the weight that actually contributed.
    #
    # But renormalising over a *sliver* of the formula is just as wrong in the
    # other direction: a provider whose only known metric is "documents
    # verified" would score 100/100 and land in the top band off one 10-point
    # component. So the score is only banded when enough of the formula is
    # actually measurable. Below that, the target is genuinely unassessed and
    # is left unbanded (band_key = None) rather than given a flattering or
    # damning band it has not earned — health bands gate commission, so an
    # invented band is worse than no band.
    total_weight = sum(float(c.weight_percent) for c in components)
    coverage = (contributing_weight / total_weight * 100.0) if total_weight else 0.0
    insufficient = bool(components) and coverage < _MIN_HEALTH_COVERAGE_PERCENT

    if not components or scoring_weight <= 0:
        score = base
    else:
        score = weighted_sum * 100.0 / scoring_weight
    penalties_applied = []
    hard_override = None
    for p in penalties:
        actual = metrics.get(p.metric_key)
        if _evaluate_operator(actual, p.operator, p.value_json):
            if p.hard_override_score is not None:
                hard_override = float(p.hard_override_score)
            score -= float(p.penalty_points)
            penalties_applied.append({"metric_key": p.metric_key, "penalty_points": float(p.penalty_points)})

    bonuses_applied = []
    bonus_total = 0.0
    for b in bonuses:
        actual = metrics.get(b.metric_key)
        if _evaluate_operator(actual, b.operator, b.value_json):
            pts = float(b.bonus_points)
            if b.max_bonus_cap is not None:
                pts = min(pts, float(b.max_bonus_cap) - bonus_total)
                pts = max(pts, 0)
            bonus_total += pts
            score += pts
            bonuses_applied.append({"metric_key": b.metric_key, "bonus_points": pts})

    min_score, max_score = float(formula.min_score), float(formula.max_score)
    score = max(min_score, min(max_score, score))
    if hard_override is not None:
        score = hard_override

    # A hard override (e.g. the tenant is suspended) is a declared verdict, not
    # a score inferred from metrics, so it bands regardless of coverage — a
    # suspended provider is blocked whether or not we can measure anything else.
    band_key, recommended_actions = None, []
    if hard_override is not None:
        insufficient = False
    if not insufficient:
        for band in bands:
            if float(band.min_score) <= score <= float(band.max_score):
                band_key = band.band_key
                if band.recommended_action:
                    recommended_actions.append(band.recommended_action)
                break

    return {
        "score": round(score, 2), "band_key": band_key,
        "coverage_percent": round(coverage, 2), "insufficient_data": insufficient,
        "component_breakdown": breakdown, "penalties_applied": penalties_applied,
        "bonuses_applied": bonuses_applied, "recommended_actions": recommended_actions,
    }


class TrustQualityService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role

    # ── Audit ────────────────────────────────────────────────────────────────

    def _audit(self, action_type: str, target_type: str | None = None,
               target_id: uuid.UUID | None = None, old_value: dict | None = None,
               new_value: dict | None = None, reason: str | None = None,
               request_id: str | None = None) -> None:
        self.db.add(TrustQualityAuditLog(
            action_type=action_type, target_type=target_type, target_id=target_id,
            actor_user_id=self.actor_id, actor_role=self.actor_role,
            old_value_json=old_value, new_value_json=new_value,
            reason=reason, request_id=request_id, created_at=_now(),
        ))

    # ── Badge Definitions ───────────────────────────────────────────────────

    async def list_badge_definitions(self, target_type: str | None = None) -> list[dict]:
        if target_type and target_type not in VALID_BADGE_TARGETS:
            raise ServiceOSException("VALIDATION_ERROR", f"target_type must be one of {sorted(VALID_BADGE_TARGETS)}")
        stmt = select(BadgeDefinition).where(BadgeDefinition.badge_key.in_(FIXED_BADGE_KEYS))
        if target_type:
            stmt = stmt.where(BadgeDefinition.target_type == target_type)
        rows = {r.badge_key: r for r in (await self.db.execute(stmt)).scalars().all()}
        return [
            _fixed_badge_payload(rows.get(spec["badge_key"]), spec)
            for spec in FIXED_BADGE_CATALOG
            if not target_type or spec["target_type"] == target_type
        ]

    async def create_badge_definition(self, data: dict) -> dict:
        raise ServiceOSException(
            "VALIDATION_ERROR",
            "Badge identities are fixed: tenant, staff and technician each have exactly four approved badges. "
            "Configure award rules instead of creating custom badges.",
        )

    async def update_badge_definition(self, badge_id: uuid.UUID, data: dict) -> dict:
        """Patch operational status only.

        Badge copy, target, icon and colour are fixed customer-facing trust
        assets. Letting admins free-edit them recreates the old badge-creation
        problem under a different button.
        """
        b = await self._get_badge(badge_id)
        if b.badge_key not in FIXED_BADGE_KEYS:
            raise ServiceOSException("VALIDATION_ERROR", "Only fixed trust badges can be managed here.")
        old = b.to_dict()
        if "status" in data and data["status"] is not None:
            if data["status"] not in {"active", "inactive"}:
                raise ServiceOSException("VALIDATION_ERROR", "status must be active or inactive.")
            b.status = data["status"]
        b.updated_at = _now()
        self._audit("badge_definition.updated", target_type=b.target_type, target_id=b.id,
                    old_value=old, new_value=b.to_dict())
        await self.db.commit()
        return _fixed_badge_payload(b, FIXED_BADGE_BY_KEY[b.badge_key])

    async def _get_badge(self, badge_id: uuid.UUID) -> BadgeDefinition:
        b = await self.db.get(BadgeDefinition, badge_id)
        if not b:
            raise ServiceOSException("NOT_FOUND", "Badge definition not found.")
        if b.badge_key not in FIXED_BADGE_KEYS:
            raise ServiceOSException("VALIDATION_ERROR", "This badge is not part of the fixed Trust & Quality catalog.")
        return b

    # ── Badge Rules ──────────────────────────────────────────────────────────

    async def list_badge_rules(self, target_type: str | None = None, status: str | None = None) -> list[dict]:
        stmt = select(BadgeRule, BadgeDefinition).join(BadgeDefinition, BadgeDefinition.id == BadgeRule.badge_id)
        stmt = stmt.where(BadgeDefinition.badge_key.in_(FIXED_BADGE_KEYS))
        if target_type:
            stmt = stmt.where(BadgeRule.target_type == target_type)
        if status:
            stmt = stmt.where(BadgeRule.status == status)
        rows = (await self.db.execute(stmt)).all()
        out = []
        for r, badge in rows:
            d = r.to_dict()
            d["badge"] = _fixed_badge_payload(badge, FIXED_BADGE_BY_KEY[badge.badge_key])
            d["criteria"] = [c.to_dict() for c in await self._get_criteria(r.id)]
            d["removal_criteria"] = [c.to_dict() for c in await self._get_removal_criteria(r.id)]
            out.append(d)
        return out

    async def get_badge_rule(self, rule_id: uuid.UUID) -> dict:
        r = await self._get_badge_rule(rule_id)
        badge = await self._get_badge(r.badge_id)
        d = r.to_dict()
        d["badge"] = _fixed_badge_payload(badge, FIXED_BADGE_BY_KEY[badge.badge_key])
        d["criteria"] = [c.to_dict() for c in await self._get_criteria(r.id)]
        d["removal_criteria"] = [c.to_dict() for c in await self._get_removal_criteria(r.id)]
        return d

    async def _get_badge_rule(self, rule_id: uuid.UUID) -> BadgeRule:
        r = await self.db.get(BadgeRule, rule_id)
        if not r:
            raise ServiceOSException("NOT_FOUND", "Badge rule not found.")
        return r

    async def _get_criteria(self, rule_id: uuid.UUID) -> list[BadgeRuleCriteria]:
        return list((await self.db.execute(
            select(BadgeRuleCriteria).where(BadgeRuleCriteria.badge_rule_id == rule_id))).scalars().all())

    async def _get_removal_criteria(self, rule_id: uuid.UUID) -> list[BadgeRuleRemovalCriteria]:
        return list((await self.db.execute(
            select(BadgeRuleRemovalCriteria).where(BadgeRuleRemovalCriteria.badge_rule_id == rule_id))).scalars().all())

    async def create_badge_rule(self, data: dict) -> dict:
        rule_key = (data.get("rule_key") or "").strip()
        if not rule_key:
            raise ServiceOSException("VALIDATION_ERROR", "rule_key is required.")
        badge_id = uuid.UUID(str(data["badge_id"]))
        badge = await self._get_badge(badge_id)
        rule_type = data.get("rule_type")
        if rule_type not in VALID_BADGE_RULE_TYPES:
            raise ServiceOSException("VALIDATION_ERROR", f"rule_type must be one of {sorted(VALID_BADGE_RULE_TYPES)}")
        scope_type = data.get("scope_type", "global")
        if scope_type not in VALID_SCOPES:
            raise ServiceOSException("VALIDATION_ERROR", f"scope_type must be one of {sorted(VALID_SCOPES)}")
        existing = await self.db.scalar(select(BadgeRule).where(BadgeRule.rule_key == rule_key))
        if existing:
            raise ServiceOSException("DUPLICATE", f"Rule key '{rule_key}' already exists.")

        expiry_enabled = data.get("expiry_enabled", False)
        if expiry_enabled and not data.get("expiry_days"):
            raise ServiceOSException("VALIDATION_ERROR", "expiry_days is required when expiry_enabled is true.")

        requested_target = data.get("target_type") or badge.target_type
        if requested_target != badge.target_type:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"Rule target_type must match badge target_type ({badge.target_type}).",
            )

        r = BadgeRule(
            rule_key=rule_key, badge_id=badge_id, target_type=requested_target,
            rule_type=rule_type, scope_type=scope_type, scope_id=data.get("scope_id"),
            auto_award=data.get("auto_award", True), manual_award_allowed=data.get("manual_award_allowed", True),
            requires_admin_review=data.get("requires_admin_review", False),
            expiry_enabled=expiry_enabled, expiry_days=data.get("expiry_days"),
            status=data.get("status", "draft"), version=1,
            created_by_user_id=self.actor_id, created_at=_now(), updated_at=_now(),
        )
        self.db.add(r)
        await self.db.flush()

        for c in data.get("criteria", []):
            if c.get("operator") not in VALID_OPERATORS:
                raise ServiceOSException("VALIDATION_ERROR", f"Invalid criterion operator '{c.get('operator')}'.")
            self.db.add(BadgeRuleCriteria(
                badge_rule_id=r.id, metric_key=c["metric_key"], operator=c["operator"],
                value_json=c.get("value"), time_window_days=c.get("time_window_days"),
                is_required=c.get("is_required", True), weight=c.get("weight"),
                created_at=_now(), updated_at=_now(),
            ))
        for c in data.get("removal_criteria", []):
            self.db.add(BadgeRuleRemovalCriteria(
                badge_rule_id=r.id, metric_key=c["metric_key"], operator=c["operator"],
                value_json=c.get("value"), time_window_days=c.get("time_window_days"),
                created_at=_now(), updated_at=_now(),
            ))

        if r.status == "active" and not data.get("criteria") and not r.manual_award_allowed:
            raise ServiceOSException("VALIDATION_ERROR",
                                      "Active rule must have at least one award criterion unless manual-only.")

        await self.db.flush()
        self._audit("badge_rule.created", target_type="badge_rule", target_id=r.id, new_value=r.to_dict())
        await self.db.commit()
        return await self.get_badge_rule(r.id)

    async def update_badge_rule(self, rule_id: uuid.UUID, data: dict) -> dict:
        """Edit a rule's scalar config and, when `criteria` is supplied, replace
        its criteria wholesale (same shape as create). rule_key is immutable."""
        r = await self._get_badge_rule(rule_id)
        old = r.to_dict()

        if "badge_id" in data and data["badge_id"]:
            badge_id = uuid.UUID(str(data["badge_id"]))
            badge = await self._get_badge(badge_id)
            if ("target_type" in data and data["target_type"] and data["target_type"] != badge.target_type) \
                    or ("target_type" not in data and r.target_type != badge.target_type):
                raise ServiceOSException(
                    "VALIDATION_ERROR",
                    f"Rule target_type must match badge target_type ({badge.target_type}).",
                )
            r.badge_id = badge_id
        if "rule_type" in data and data["rule_type"] is not None:
            if data["rule_type"] not in VALID_BADGE_RULE_TYPES:
                raise ServiceOSException("VALIDATION_ERROR", f"rule_type must be one of {sorted(VALID_BADGE_RULE_TYPES)}")
            r.rule_type = data["rule_type"]
        if "scope_type" in data and data["scope_type"] is not None:
            if data["scope_type"] not in VALID_SCOPES:
                raise ServiceOSException("VALIDATION_ERROR", f"scope_type must be one of {sorted(VALID_SCOPES)}")
            r.scope_type = data["scope_type"]
        for field in ("target_type", "auto_award", "manual_award_allowed",
                      "requires_admin_review", "expiry_enabled", "expiry_days"):
            if field in data and data[field] is not None:
                setattr(r, field, data[field])
        badge = await self._get_badge(r.badge_id)
        if r.target_type != badge.target_type:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"Rule target_type must match badge target_type ({badge.target_type}).",
            )

        # Replacing criteria only when the caller sends the key, so a scalar-only
        # edit leaves the existing criteria untouched.
        if "criteria" in data:
            for c in await self._get_criteria(rule_id):
                await self.db.delete(c)
            await self.db.flush()
            for c in data["criteria"]:
                if c.get("operator") not in VALID_OPERATORS:
                    raise ServiceOSException("VALIDATION_ERROR", f"Invalid criterion operator '{c.get('operator')}'.")
                self.db.add(BadgeRuleCriteria(
                    badge_rule_id=r.id, metric_key=c["metric_key"], operator=c["operator"],
                    value_json=c.get("value"), time_window_days=c.get("time_window_days"),
                    is_required=c.get("is_required", True), weight=c.get("weight"),
                    created_at=_now(), updated_at=_now(),
                ))

        # An active rule must keep at least one criterion unless it is manual-only.
        if r.status == "active" and not r.manual_award_allowed:
            remaining = await self._get_criteria(rule_id)
            if not remaining:
                raise ServiceOSException("VALIDATION_ERROR",
                                          "Active rule must have at least one award criterion unless manual-only.")

        r.updated_at = _now()
        await self.db.flush()
        self._audit("badge_rule.updated", target_type="badge_rule", target_id=r.id,
                    old_value=old, new_value=r.to_dict())
        await self.db.commit()
        return await self.get_badge_rule(rule_id)

    async def activate_badge_rule(self, rule_id: uuid.UUID, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required to activate a rule.")
        r = await self._get_badge_rule(rule_id)
        criteria = await self._get_criteria(rule_id)
        if not criteria and not r.manual_award_allowed:
            raise ServiceOSException("VALIDATION_ERROR",
                                      "Active rule must have at least one award criterion unless manual-only.")
        old = r.to_dict()
        r.status = "active"
        r.updated_at = _now()
        self._audit("badge_rule.activated", target_type="badge_rule", target_id=r.id,
                    old_value=old, new_value=r.to_dict(), reason=reason)
        await self.db.commit()
        return await self.get_badge_rule(rule_id)

    async def deactivate_badge_rule(self, rule_id: uuid.UUID, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required to deactivate a rule.")
        r = await self._get_badge_rule(rule_id)
        old = r.to_dict()
        r.status = "inactive"
        r.updated_at = _now()
        self._audit("badge_rule.deactivated", target_type="badge_rule", target_id=r.id,
                    old_value=old, new_value=r.to_dict(), reason=reason)
        await self.db.commit()
        return await self.get_badge_rule(rule_id)

    async def simulate_badge_rule(self, rule_id: uuid.UUID, metrics: dict) -> dict:
        r = await self._get_badge_rule(rule_id)
        criteria = await self._get_criteria(rule_id)
        removal = await self._get_removal_criteria(rule_id)
        matched, failed = [], []
        for c in criteria:
            actual = metrics.get(c.metric_key)
            ok = _evaluate_operator(actual, c.operator, c.value_json)
            entry = {"metric_key": c.metric_key, "operator": c.operator, "expected": c.value_json, "actual": actual}
            (matched if ok else failed).append(entry)
        eligible = all(_evaluate_operator(metrics.get(c.metric_key), c.operator, c.value_json)
                       for c in criteria if c.is_required)
        would_remove = False
        removal_matched = []
        for c in removal:
            actual = metrics.get(c.metric_key)
            if _evaluate_operator(actual, c.operator, c.value_json):
                would_remove = True
                removal_matched.append({"metric_key": c.metric_key, "operator": c.operator, "expected": c.value_json, "actual": actual})
        result = {
            "rule_id": str(rule_id), "eligible": eligible and not would_remove,
            "matched_criteria": matched, "failed_criteria": failed,
            "would_award_badge": eligible and not would_remove,
            "would_remove_badge": would_remove,
            "removal_matched": removal_matched,
            "warnings": [] if criteria else ["Rule has no award criteria configured."],
        }
        return result

    async def manual_award_badge(self, badge_id: uuid.UUID, target_type: str, target_id: uuid.UUID,
                                  reason: str, expires_at: datetime | None = None) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required for a manual badge award.")
        badge = await self._get_badge(badge_id)
        if target_type != badge.target_type:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"Cannot award a {badge.target_type} badge to target_type '{target_type}'.",
            )
        if target_type == "tenant":
            target_exists = await self.db.scalar(
                text("SELECT EXISTS(SELECT 1 FROM tenants WHERE id = :target_id)"),
                {"target_id": str(target_id)},
            )
        else:
            target_exists = await self.db.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM users "
                    "WHERE id = :target_id AND role = 'staff' AND deleted_at IS NULL)"
                ),
                {"target_id": str(target_id)},
            )
        if not target_exists:
            raise ServiceOSException("NOT_FOUND", f"{target_type.replace('_', ' ').title()} target not found.")
        existing = (await self.db.execute(
            select(BadgeAssignment).where(
                BadgeAssignment.badge_id == badge_id,
                BadgeAssignment.target_type == target_type,
                BadgeAssignment.target_id == target_id,
                BadgeAssignment.status == "active",
            )
        )).scalar_one_or_none()
        if existing:
            return existing.to_dict()
        a = BadgeAssignment(
            badge_id=badge_id, target_type=target_type, target_id=target_id,
            status="active", award_source="manual_admin", assigned_by_user_id=self.actor_id,
            assigned_reason=reason, earned_at=_now(), expires_at=expires_at,
            created_at=_now(), updated_at=_now(),
        )
        self.db.add(a)
        await self.db.flush()
        self._audit("badge_assignment.awarded", target_type=target_type, target_id=target_id,
                    new_value=a.to_dict(), reason=reason)
        await self.db.commit()
        return a.to_dict()

    async def revoke_badge(self, assignment_id: uuid.UUID, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required to revoke a badge.")
        a = await self.db.get(BadgeAssignment, assignment_id)
        if not a:
            raise ServiceOSException("NOT_FOUND", "Badge assignment not found.")
        old = a.to_dict()
        a.status = "revoked"
        a.revoked_at = _now()
        a.revoked_by_user_id = self.actor_id
        a.revoked_reason = reason
        a.updated_at = _now()
        self._audit("badge_assignment.revoked", target_type=a.target_type, target_id=a.target_id,
                    old_value=old, new_value=a.to_dict(), reason=reason)
        await self.db.commit()
        return a.to_dict()

    async def list_earned_badges(self, target_type: str, target_id: uuid.UUID,
                                 audience: str = "admin") -> list[dict]:
        """A target's currently-earned badges, joined with their definition and
        filtered for the audience that will see them.

        This is the read side that every consumer surface (provider self-view,
        customer provider-view, admin per-target view) shares. Only active,
        non-expired assignments count, and `audience` gates by the badge's
        visibility flags so a customer never sees an internal-only badge.
        """
        rows = (await self.db.execute(
            select(BadgeAssignment, BadgeDefinition)
            .join(BadgeDefinition, BadgeDefinition.id == BadgeAssignment.badge_id)
            .where(
                BadgeAssignment.target_type == target_type,
                BadgeAssignment.target_id == target_id,
                BadgeAssignment.status == "active",
            )
        )).all()
        now = _now()
        # A target holds each distinct badge once — historical data can carry
        # several active assignment rows for the same badge, so dedupe by
        # badge_key and keep the earliest earned_at (when it was first earned).
        by_key: dict[str, dict] = {}
        for a, b in rows:
            if b.badge_key not in FIXED_BADGE_KEYS:
                continue
            spec = FIXED_BADGE_BY_KEY[b.badge_key]
            if spec["target_type"] != target_type:
                continue
            if a.expires_at and a.expires_at < now:
                continue
            if audience == "customer" and not spec.get("customer_visible", False):
                continue
            if audience == "provider" and not (spec.get("tenant_visible", True) or spec.get("customer_visible", False)):
                continue
            earned = a.earned_at.isoformat() if a.earned_at else None
            prev = by_key.get(b.badge_key)
            if prev and (prev["earned_at"] or "") <= (earned or ""):
                continue  # keep the earlier assignment
            by_key[b.badge_key] = {
                "assignment_id": str(a.id), "badge_key": b.badge_key, "name": spec["name"],
                "description": spec.get("description"), "icon": spec.get("icon"), "color": spec.get("color"),
                "customer_visible": spec.get("customer_visible", False), "tenant_visible": spec.get("tenant_visible", True),
                "level": spec["level"], "tone": spec.get("tone"),
                "award_source": a.award_source, "earned_at": earned,
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
        # Most-recently earned first.
        return sorted(by_key.values(), key=lambda x: x.get("level", 99))[:4]

    async def list_badge_assignments(
        self,
        *,
        q: str | None = None,
        target_type: str | None = None,
        badge_key: str | None = None,
        award_source: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> dict:
        """Return a server-paged directory of badges currently held."""
        if target_type and target_type not in VALID_BADGE_TARGETS:
            raise ServiceOSException(
                "VALIDATION_ERROR", f"target_type must be one of {sorted(VALID_BADGE_TARGETS)}"
            )
        if badge_key and badge_key not in FIXED_BADGE_KEYS:
            raise ServiceOSException("VALIDATION_ERROR", "Unknown fixed badge key.")
        if award_source and award_source not in VALID_AWARD_SOURCES:
            raise ServiceOSException("VALIDATION_ERROR", "Unknown award source.")

        limit = max(1, min(int(limit), 100))
        offset = max(0, int(offset))
        search = (q or "").strip().lower()
        params: dict = {
            "badge_keys": list(FIXED_BADGE_KEYS),
            "target_type": target_type,
            "badge_key": badge_key,
            "award_source": award_source,
            "search": f"%{search}%" if search else None,
            "target_id_exact": search if search else None,
            "limit": limit,
            "offset": offset,
        }
        # Historical imports occasionally created the same active assignment
        # twice. Rank them so the directory shows one holder/badge pair while
        # the underlying audit history remains intact.
        cte = """
            WITH current_assignments AS (
                SELECT ba.*,
                       row_number() OVER (
                           PARTITION BY ba.target_type, ba.target_id, ba.badge_id
                           ORDER BY ba.earned_at ASC NULLS LAST, ba.created_at ASC, ba.id ASC
                       ) AS holder_rank
                  FROM badge_assignments ba
                 WHERE ba.status = 'active'
                   AND (ba.expires_at IS NULL OR ba.expires_at > now())
            )
        """
        from_where = """
            FROM current_assignments ba
            JOIN badge_definitions bd ON bd.id = ba.badge_id
            LEFT JOIN tenants tenant
              ON ba.target_type = 'tenant' AND tenant.id = ba.target_id
            LEFT JOIN users member
              ON ba.target_type IN ('staff', 'technician') AND member.id = ba.target_id
             AND member.deleted_at IS NULL
            WHERE ba.holder_rank = 1
              AND bd.badge_key = ANY(CAST(:badge_keys AS text[]))
              AND bd.target_type = ba.target_type
              AND (
                    (ba.target_type = 'tenant' AND tenant.id IS NOT NULL)
                    OR (ba.target_type IN ('staff', 'technician') AND member.id IS NOT NULL)
                  )
              AND (CAST(:target_type AS text) IS NULL OR ba.target_type = CAST(:target_type AS text))
              AND (CAST(:badge_key AS text) IS NULL OR bd.badge_key = CAST(:badge_key AS text))
              AND (CAST(:award_source AS text) IS NULL OR ba.award_source = CAST(:award_source AS text))
              AND (
                    CAST(:search AS text) IS NULL
                    OR lower(tenant.business_name) LIKE CAST(:search AS text)
                    OR lower(tenant.tenant_name) LIKE CAST(:search AS text)
                    OR lower(tenant.email) LIKE CAST(:search AS text)
                    OR lower(tenant.phone) LIKE CAST(:search AS text)
                    OR lower(member.full_name) LIKE CAST(:search AS text)
                    OR lower(member.email) LIKE CAST(:search AS text)
                    OR lower(member.phone) LIKE CAST(:search AS text)
                    OR lower(bd.name) LIKE CAST(:search AS text)
                    OR CAST(ba.target_id AS text) = CAST(:target_id_exact AS text)
                  )
        """
        total = int((await self.db.execute(
            text(cte + "SELECT count(*) " + from_where), params
        )).scalar_one())
        rows = (await self.db.execute(text(cte + """
            SELECT ba.id AS assignment_id, ba.target_type, ba.target_id,
                   COALESCE(tenant.business_name, tenant.tenant_name,
                            member.full_name, member.email, CAST(ba.target_id AS text)) AS target_name,
                   COALESCE(tenant.email, member.email) AS target_secondary,
                   bd.id AS badge_id, bd.badge_key, bd.name, bd.description,
                   bd.icon, bd.color,
                   bd.customer_visible, bd.tenant_visible,
                   ba.award_source, ba.earned_at, ba.expires_at
        """ + from_where + """
            ORDER BY ba.earned_at DESC NULLS LAST, ba.id DESC
            LIMIT :limit OFFSET :offset
        """), params)).mappings().all()
        return {
            "items": [
                {
                    **dict(row),
                    "assignment_id": str(row["assignment_id"]),
                    "target_id": str(row["target_id"]),
                    "badge_id": str(row["badge_id"]),
                    "level": int(FIXED_BADGE_BY_KEY[row["badge_key"]]["level"]),
                    "tone": FIXED_BADGE_BY_KEY[row["badge_key"]].get("tone"),
                    "earned_at": row["earned_at"].isoformat() if row["earned_at"] else None,
                    "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                }
                for row in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def recalculate_badges_for_target(self, target_type: str, target_id: uuid.UUID, metrics: dict) -> list[dict]:
        """Evaluate all active auto-award rules for target_type against metrics; award/revoke as needed."""
        if target_type not in VALID_BADGE_TARGETS:
            return []
        rules = (await self.db.execute(
            select(BadgeRule, BadgeDefinition)
            .join(BadgeDefinition, BadgeDefinition.id == BadgeRule.badge_id)
            .where(
                BadgeRule.target_type == target_type,
                BadgeRule.status == "active",
                BadgeRule.auto_award == True,  # noqa: E712
                BadgeDefinition.badge_key.in_(FIXED_BADGE_KEYS),
            )
        )).all()
        results = []
        for r, badge in rules:
            if FIXED_BADGE_BY_KEY[badge.badge_key]["target_type"] != target_type:
                continue
            criteria = await self._get_criteria(r.id)
            removal = await self._get_removal_criteria(r.id)
            eligible = bool(criteria) and all(
                _evaluate_operator(metrics.get(c.metric_key), c.operator, c.value_json)
                for c in criteria if c.is_required)
            would_remove = any(
                _evaluate_operator(metrics.get(c.metric_key), c.operator, c.value_json) for c in removal)

            existing = (await self.db.execute(
                select(BadgeAssignment).where(
                    BadgeAssignment.badge_id == r.badge_id, BadgeAssignment.target_type == target_type,
                    BadgeAssignment.target_id == target_id, BadgeAssignment.status == "active")
            )).scalar_one_or_none()

            if eligible and not would_remove and not existing:
                expires_at = _now() + timedelta(days=r.expiry_days) if r.expiry_enabled and r.expiry_days else None
                a = BadgeAssignment(
                    badge_id=r.badge_id, badge_rule_id=r.id, target_type=target_type, target_id=target_id,
                    status="active", award_source="auto_rule", earned_at=_now(), expires_at=expires_at,
                    created_at=_now(), updated_at=_now(),
                )
                self.db.add(a)
                await self.db.flush()
                self._audit("badge_assignment.awarded", target_type=target_type, target_id=target_id, new_value=a.to_dict())
                results.append({"action": "awarded", "badge_id": str(r.badge_id), "rule_key": r.rule_key})
            elif existing and (would_remove or not eligible):
                existing.status = "revoked" if would_remove else "expired"
                existing.revoked_at = _now()
                existing.revoked_reason = "auto: removal criteria matched" if would_remove else "auto: no longer eligible"
                existing.updated_at = _now()
                self._audit("badge_assignment.expired" if not would_remove else "badge_assignment.revoked",
                            target_type=target_type, target_id=target_id, new_value=existing.to_dict())
                results.append({"action": "removed", "badge_id": str(r.badge_id), "rule_key": r.rule_key})
        await self.db.commit()
        return results

    # ── Health Formulas ──────────────────────────────────────────────────────

    async def list_health_formulas(self, target_type: str | None = None) -> list[dict]:
        stmt = select(HealthFormula).where(HealthFormula.target_type.in_(VALID_HEALTH_TARGETS))
        if target_type:
            if target_type not in VALID_HEALTH_TARGETS:
                return []
            stmt = stmt.where(HealthFormula.target_type == target_type)
        rows = (await self.db.execute(
            stmt.order_by(
                (HealthFormula.status == "active").desc(),
                HealthFormula.updated_at.desc(),
            )
        )).scalars().all()
        return [f.to_dict() for f in rows]

    async def _get_formula(self, formula_id: uuid.UUID) -> HealthFormula:
        f = await self.db.get(HealthFormula, formula_id)
        if not f or f.target_type not in VALID_HEALTH_TARGETS:
            raise ServiceOSException("NOT_FOUND", "Health formula not found.")
        return f

    async def get_health_formula(self, formula_id: uuid.UUID) -> dict:
        f = await self._get_formula(formula_id)
        d = f.to_dict()
        d["components"] = [c.to_dict() for c in await self._get_components(formula_id)]
        d["penalties"] = [p.to_dict() for p in await self._get_penalties(formula_id)]
        d["bonuses"] = [b.to_dict() for b in await self._get_bonuses(formula_id)]
        d["bands"] = [b.to_dict() for b in await self._get_bands(formula_id)]
        return d

    async def _get_components(self, formula_id: uuid.UUID) -> list[HealthFormulaComponent]:
        return list((await self.db.execute(
            select(HealthFormulaComponent).where(HealthFormulaComponent.formula_id == formula_id))).scalars().all())

    async def _get_penalties(self, formula_id: uuid.UUID) -> list[HealthPenaltyRule]:
        return list((await self.db.execute(
            select(HealthPenaltyRule).where(HealthPenaltyRule.formula_id == formula_id))).scalars().all())

    async def _get_bonuses(self, formula_id: uuid.UUID) -> list[HealthBonusRule]:
        return list((await self.db.execute(
            select(HealthBonusRule).where(HealthBonusRule.formula_id == formula_id))).scalars().all())

    async def _get_bands(self, formula_id: uuid.UUID) -> list[HealthBandRule]:
        return list((await self.db.execute(
            select(HealthBandRule).where(HealthBandRule.formula_id == formula_id).order_by(HealthBandRule.min_score))).scalars().all())

    @staticmethod
    def _validate_bands(bands: list[dict]) -> None:
        if not bands:
            raise ServiceOSException("VALIDATION_ERROR", "Active formula must have at least one band.")
        sorted_bands = sorted(bands, key=lambda b: b["min_score"])
        if sorted_bands[0]["min_score"] > 0:
            raise ServiceOSException("VALIDATION_ERROR", "Band ranges must cover 0-100 (missing lower bound at 0).")
        if sorted_bands[-1]["max_score"] < 100:
            raise ServiceOSException("VALIDATION_ERROR", "Band ranges must cover 0-100 (missing upper bound at 100).")
        for i in range(len(sorted_bands) - 1):
            if sorted_bands[i]["max_score"] > sorted_bands[i + 1]["min_score"]:
                raise ServiceOSException("VALIDATION_ERROR", "Band ranges cannot overlap.")

    async def create_health_formula(self, data: dict) -> dict:
        formula_key = (data.get("formula_key") or "").strip()
        if not formula_key:
            raise ServiceOSException("VALIDATION_ERROR", "formula_key is required.")
        target_type = data.get("target_type")
        if target_type not in VALID_HEALTH_TARGETS:
            raise ServiceOSException("VALIDATION_ERROR", f"target_type must be one of {sorted(VALID_HEALTH_TARGETS)}")
        existing = await self.db.scalar(select(HealthFormula).where(HealthFormula.formula_key == formula_key))
        if existing:
            raise ServiceOSException("DUPLICATE", f"Formula key '{formula_key}' already exists.")

        components = data.get("components", [])
        total_weight = sum(float(c["weight_percent"]) for c in components)
        status = data.get("status", "draft")
        if status != "draft":
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "New formulas must start as draft. Use the audited activate action after review.",
            )

        bands = data.get("bands", [])
        f = HealthFormula(
            formula_key=formula_key, name=data["name"], target_type=target_type,
            scope_type=data.get("scope_type", "global"), scope_id=data.get("scope_id"),
            base_score=data.get("base_score", 100), min_score=data.get("min_score", 0),
            max_score=data.get("max_score", 100), status=status, version=1,
            created_by_user_id=self.actor_id, created_at=_now(), updated_at=_now(),
        )
        self.db.add(f)
        await self.db.flush()

        for c in components:
            self.db.add(HealthFormulaComponent(
                formula_id=f.id, metric_key=c["metric_key"], weight_percent=c["weight_percent"],
                direction=c.get("direction", "positive"), min_value=c.get("min_value"),
                max_value=c.get("max_value"), normalization_method=c.get("normalization_method", "linear"),
                is_required=c.get("is_required", True), created_at=_now(), updated_at=_now(),
            ))
        for p in data.get("penalties", []):
            self.db.add(HealthPenaltyRule(
                formula_id=f.id, metric_key=p["metric_key"], operator=p["operator"],
                value_json=p.get("value"), penalty_points=p["penalty_points"],
                hard_override_score=p.get("hard_override_score"), created_at=_now(), updated_at=_now(),
            ))
        for b in data.get("bonuses", []):
            self.db.add(HealthBonusRule(
                formula_id=f.id, metric_key=b["metric_key"], operator=b["operator"],
                value_json=b.get("value"), bonus_points=b["bonus_points"],
                max_bonus_cap=b.get("max_bonus_cap"), created_at=_now(), updated_at=_now(),
            ))
        for band in bands:
            self.db.add(HealthBandRule(
                formula_id=f.id, band_key=band["band_key"], band_name=band["band_name"],
                min_score=band["min_score"], max_score=band["max_score"], color=band.get("color"),
                bookable_allowed=band.get("bookable_allowed", True),
                recommended_action=band.get("recommended_action"), created_at=_now(), updated_at=_now(),
            ))

        await self.db.flush()
        self._audit("health_formula.created", target_type="health_formula", target_id=f.id, new_value=f.to_dict())
        await self.db.commit()
        return await self.get_health_formula(f.id)

    async def update_health_formula(self, formula_id: uuid.UUID, data: dict) -> dict:
        """Edit a formula's scalars and, when supplied, replace its components,
        bands, penalties and bonuses wholesale. formula_key is immutable.

        If the formula is active (or is being set active) the same integrity gates
        as create apply: component weights must total 100% and bands must cover
        0-100 — an edit cannot leave a live formula in an invalid state.
        """
        f = await self._get_formula(formula_id)
        old = f.to_dict()

        if "target_type" in data and data["target_type"] is not None:
            if data["target_type"] not in VALID_HEALTH_TARGETS:
                raise ServiceOSException("VALIDATION_ERROR", f"target_type must be one of {sorted(VALID_HEALTH_TARGETS)}")
            f.target_type = data["target_type"]
        if "status" in data and data["status"] != f.status:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "Formula status changes must use the audited activate/deactivate actions.",
            )
        for field in ("name", "scope_type", "scope_id", "base_score", "min_score", "max_score"):
            if field in data and data[field] is not None:
                setattr(f, field, data[field])

        async def _replace(get_rows, add_fn, key):
            if key not in data:
                return
            for row in await get_rows(formula_id):
                await self.db.delete(row)
            await self.db.flush()
            for item in data[key]:
                add_fn(item)

        await _replace(self._get_components, lambda c: self.db.add(HealthFormulaComponent(
            formula_id=f.id, metric_key=c["metric_key"], weight_percent=c["weight_percent"],
            direction=c.get("direction", "positive"), min_value=c.get("min_value"),
            max_value=c.get("max_value"), normalization_method=c.get("normalization_method", "linear"),
            is_required=c.get("is_required", True), created_at=_now(), updated_at=_now())), "components")
        await _replace(self._get_penalties, lambda p: self.db.add(HealthPenaltyRule(
            formula_id=f.id, metric_key=p["metric_key"], operator=p["operator"],
            value_json=p.get("value"), penalty_points=p["penalty_points"],
            hard_override_score=p.get("hard_override_score"), created_at=_now(), updated_at=_now())), "penalties")
        await _replace(self._get_bonuses, lambda b: self.db.add(HealthBonusRule(
            formula_id=f.id, metric_key=b["metric_key"], operator=b["operator"],
            value_json=b.get("value"), bonus_points=b["bonus_points"],
            max_bonus_cap=b.get("max_bonus_cap"), created_at=_now(), updated_at=_now())), "bonuses")
        await _replace(self._get_bands, lambda band: self.db.add(HealthBandRule(
            formula_id=f.id, band_key=band["band_key"], band_name=band["band_name"],
            min_score=band["min_score"], max_score=band["max_score"], color=band.get("color"),
            bookable_allowed=band.get("bookable_allowed", True),
            recommended_action=band.get("recommended_action"), created_at=_now(), updated_at=_now())), "bands")

        await self.db.flush()

        if f.status == "active":
            components = await self._get_components(formula_id)
            if not components:
                raise ServiceOSException("VALIDATION_ERROR", "Active formula must have valid components.")
            total_weight = sum(float(c.weight_percent) for c in components)
            if abs(total_weight - 100.0) > 0.01:
                raise ServiceOSException("VALIDATION_ERROR", f"Total component weights must equal 100% (got {total_weight}%).")
            self._validate_bands([b.to_dict() for b in await self._get_bands(formula_id)])

        f.updated_at = _now()
        self._audit("health_formula.updated", target_type="health_formula", target_id=f.id,
                    old_value=old, new_value=f.to_dict())
        await self.db.commit()
        return await self.get_health_formula(formula_id)

    async def activate_health_formula(self, formula_id: uuid.UUID, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required to activate a formula.")
        f = await self._get_formula(formula_id)
        components = await self._get_components(formula_id)
        if not components:
            raise ServiceOSException("VALIDATION_ERROR", "Active formula must have valid components.")
        total_weight = sum(float(c.weight_percent) for c in components)
        if abs(total_weight - 100.0) > 0.01:
            raise ServiceOSException("VALIDATION_ERROR", f"Total component weights must equal 100% (got {total_weight}%).")
        bands = [b.to_dict() for b in await self._get_bands(formula_id)]
        self._validate_bands(bands)
        old = f.to_dict()
        # Exactly one formula may be authoritative for a target type. Without
        # this guard, matching could read whichever score happened to be
        # recalculated last when two formulas were active.
        peers = (await self.db.execute(
            select(HealthFormula).where(
                HealthFormula.target_type == f.target_type,
                HealthFormula.status == "active",
                HealthFormula.id != f.id,
            )
        )).scalars().all()
        for peer in peers:
            peer_old = peer.to_dict()
            peer.status = "inactive"
            peer.updated_at = _now()
            self._audit(
                "health_formula.deactivated",
                target_type="health_formula",
                target_id=peer.id,
                old_value=peer_old,
                new_value=peer.to_dict(),
                reason=f"Superseded by activation of {f.formula_key}: {reason.strip()}",
            )
        if peers:
            await self.db.flush()
        f.status = "active"
        f.updated_at = _now()
        self._audit("health_formula.activated", target_type="health_formula", target_id=f.id,
                    old_value=old, new_value=f.to_dict(), reason=reason)
        await self.db.commit()
        return await self.get_health_formula(formula_id)

    async def deactivate_health_formula(self, formula_id: uuid.UUID, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required to deactivate a formula.")
        f = await self._get_formula(formula_id)
        old = f.to_dict()
        f.status = "inactive"
        f.updated_at = _now()
        self._audit("health_formula.deactivated", target_type="health_formula", target_id=f.id,
                    old_value=old, new_value=f.to_dict(), reason=reason)
        await self.db.commit()
        return await self.get_health_formula(formula_id)

    def _calc_score(self, formula: HealthFormula, components: list[HealthFormulaComponent],
                     penalties: list[HealthPenaltyRule], bonuses: list[HealthBonusRule],
                     bands: list[HealthBandRule], metrics: dict) -> dict:
        return calc_health_score(formula, components, penalties, bonuses, bands, metrics)

    async def simulate_health_formula(self, formula_id: uuid.UUID, metrics: dict) -> dict:
        f = await self._get_formula(formula_id)
        result = calc_health_score(
            f, await self._get_components(formula_id), await self._get_penalties(formula_id),
            await self._get_bonuses(formula_id), await self._get_bands(formula_id), metrics)
        result["formula_id"] = str(formula_id)
        return result

    async def recalculate_health_for_target(self, formula_id: uuid.UUID, target_type: str,
                                             target_id: uuid.UUID, metrics: dict) -> dict:
        f = await self._get_formula(formula_id)
        components = await self._get_components(formula_id)
        penalties = await self._get_penalties(formula_id)
        bonuses = await self._get_bonuses(formula_id)
        bands = await self._get_bands(formula_id)
        result = self._calc_score(f, components, penalties, bonuses, bands, metrics)

        existing = (await self.db.execute(
            select(HealthScore).where(HealthScore.target_type == target_type, HealthScore.target_id == target_id,
                                       HealthScore.formula_id == formula_id)
        )).scalar_one_or_none()
        if existing:
            existing.score = result["score"]
            existing.band_key = result["band_key"]
            existing.component_breakdown_json = result["component_breakdown"]
            existing.penalties_json = result["penalties_applied"]
            existing.bonuses_json = result["bonuses_applied"]
            existing.recommended_actions_json = result["recommended_actions"]
            existing.calculated_at = _now()
            existing.updated_at = _now()
            hs = existing
        else:
            hs = HealthScore(
                target_type=target_type, target_id=target_id, formula_id=formula_id,
                score=result["score"], band_key=result["band_key"],
                component_breakdown_json=result["component_breakdown"],
                penalties_json=result["penalties_applied"], bonuses_json=result["bonuses_applied"],
                recommended_actions_json=result["recommended_actions"],
                calculated_at=_now(), created_at=_now(), updated_at=_now(),
            )
            self.db.add(hs)
        await self.db.flush()
        # Score rows are the calculation record. Writing a second audit row for
        # every target on every sweep doubles storage at platform scale and
        # makes the human audit trail unusable. Recalculation jobs provide the
        # batch-level operational audit instead.
        await self.db.commit()
        return hs.to_dict()

    # ── Risk Scoring (simple) ────────────────────────────────────────────────

    async def recalculate_risk_for_target(self, target_type: str, target_id: uuid.UUID, metrics: dict) -> dict:
        if target_type not in VALID_HEALTH_TARGETS:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"target_type must be one of {sorted(VALID_HEALTH_TARGETS)}",
            )
        rules = (await self.db.execute(
            select(RiskRule).where(RiskRule.target_type == target_type, RiskRule.status == "active")
        )).scalars().all()
        reasons, actions = [], []
        score_delta = 0.0
        risk_level = "normal"
        level_rank = {lvl: i for i, lvl in enumerate(
            ["normal", "watchlist", "high_risk", "finance_blocked", "quality_blocked", "suspended"])}
        for r in rules:
            cond = r.condition_json
            actual = metrics.get(cond.get("metric_key"))
            if _evaluate_operator(actual, cond.get("operator"), cond.get("value")):
                score_delta += float(r.risk_score_delta)
                reasons.append(r.name)
                actions.extend(r.recommended_actions_json or [])
                if level_rank.get(r.risk_level, 0) > level_rank.get(risk_level, 0):
                    risk_level = r.risk_level

        existing = (await self.db.execute(
            select(RiskScore).where(RiskScore.target_type == target_type, RiskScore.target_id == target_id)
        )).scalar_one_or_none()
        bookable_impact = risk_level in ("high_risk", "quality_blocked", "suspended")
        finance_impact = risk_level in ("finance_blocked", "suspended")
        if existing:
            existing.risk_score = score_delta
            existing.risk_level = risk_level
            existing.reasons_json = reasons
            existing.recommended_actions_json = actions
            existing.bookable_impact = bookable_impact
            existing.finance_impact = finance_impact
            existing.calculated_at = _now()
            existing.updated_at = _now()
            rs = existing
        else:
            rs = RiskScore(
                target_type=target_type, target_id=target_id, risk_score=score_delta, risk_level=risk_level,
                reasons_json=reasons, recommended_actions_json=actions,
                bookable_impact=bookable_impact, finance_impact=finance_impact,
                calculated_at=_now(), created_at=_now(), updated_at=_now(),
            )
            self.db.add(rs)
        await self.db.flush()
        await self.db.commit()
        return rs.to_dict()

    # ── Recalculation ───────────────────────────────────────────────────────

    async def gather_live_metrics(self, target_type: str, target_id: uuid.UUID) -> dict:
        """Compute a target's live metrics from the operational tables.

        Only metrics with a real source are returned. A metric with no source is
        left OUT rather than defaulted, because a criterion that reads a missing
        metric evaluates false — which correctly withholds a badge instead of
        awarding one off a fabricated number.
        """
        m: dict = {}

        if target_type in ("tenant", "tenant_provider"):
            job_col, review_col, complaint_col = "tenant_id", "tenant_id", "tenant_id"
        elif target_type in ("staff", "technician", "tenant_staff"):
            job_col, review_col, complaint_col = "assigned_staff_id", "staff_member_id", None
        elif target_type == "customer_account":
            job_col, review_col, complaint_col = "customer_id", "customer_id", "customer_id"
        else:
            return m

        counts = dict((await self.db.execute(
            text(f"SELECT status, count(*) AS c FROM service_jobs "
                 f"WHERE {job_col} = :t GROUP BY status"), {"t": str(target_id)})).all())
        done = sum(counts.get(s, 0) for s in _JOB_DONE_STATUSES)
        cancelled = sum(counts.get(s, 0) for s in _JOB_CANCELLED_STATUSES)
        terminal = done + cancelled
        m["completed_jobs_count"] = done
        if terminal:
            m["job_completion_rate"] = round(done * 100.0 / terminal, 2)
            m["cancellation_rate"] = round(cancelled * 100.0 / terminal, 2)

        row = (await self.db.execute(
            text(f"SELECT avg(overall_rating) AS avg, count(*) AS n FROM customer_reviews "
                 f"WHERE {review_col} = :t AND hidden_at IS NULL"), {"t": str(target_id)})).one()
        m["review_count"] = int(row.n or 0)
        if row.avg is not None:
            m["average_rating"] = round(float(row.avg), 2)
            # Formulas score out of 100, ratings are out of 5.
            m["rating_score"] = round(float(row.avg) * 20.0, 2)

        if target_type in ("staff", "technician", "tenant_staff"):
            punctuality = (await self.db.execute(text("""
                SELECT count(*) FILTER (WHERE punctuality_rating >= 4) AS on_time,
                       count(punctuality_rating) AS measured
                  FROM customer_reviews
                 WHERE staff_member_id = :target_id AND hidden_at IS NULL
            """), {"target_id": str(target_id)})).one()
            if punctuality.measured:
                m["on_time_arrival_rate"] = round(
                    int(punctuality.on_time or 0) * 100.0 / int(punctuality.measured), 2
                )

        if complaint_col:
            row = (await self.db.execute(
                text(f"SELECT count(*) AS n, "
                     f"       count(*) FILTER (WHERE sla_status = 'breached') AS breached "
                     f"FROM customer_complaints WHERE {complaint_col} = :t"),
                {"t": str(target_id)})).one()
            n, breached = int(row.n or 0), int(row.breached or 0)
            if terminal:
                rate = round(n * 100.0 / terminal, 2)
                m["complaint_rate"] = rate
                m["complaint_dispute_score"] = rate
            if n:
                # Share of complaints answered inside the SLA.
                m["response_sla_score"] = round((n - breached) * 100.0 / n, 2)
                m["sla_success_rate"] = m["response_sla_score"]
        elif target_type in ("staff", "technician", "tenant_staff"):
            row = (await self.db.execute(text("""
                SELECT count(*) AS n,
                       count(*) FILTER (WHERE cc.sla_status = 'breached') AS breached
                  FROM customer_complaints cc
                  JOIN service_jobs sj ON sj.id = cc.job_id
                 WHERE sj.assigned_staff_id = :target_id
            """), {"target_id": str(target_id)})).one()
            n, breached = int(row.n or 0), int(row.breached or 0)
            if terminal:
                rate = round(n * 100.0 / terminal, 2)
                m["complaint_rate"] = rate
                m["complaint_dispute_score"] = rate
            if n:
                m["response_sla_score"] = round((n - breached) * 100.0 / n, 2)
                m["sla_success_rate"] = m["response_sla_score"]

        if target_type in ("tenant", "tenant_provider"):
            tenant = (await self.db.execute(text("""
                SELECT status, verification_status, business_name, email, phone,
                       address_line1, city, state, zipcode, business_type
                  FROM tenants WHERE id = :target_id
            """), {"target_id": str(target_id)})).mappings().one_or_none()
            verified = bool(tenant and tenant["verification_status"] == "verified")
            m["document_verified"] = verified
            m["owner_verified"] = verified
            m["document_verification_score"] = 100.0 if verified else 0.0
            if tenant:
                profile_fields = (
                    "business_name", "email", "phone", "address_line1",
                    "city", "state", "zipcode", "business_type",
                )
                m["profile_completion_percent"] = round(
                    sum(bool(tenant[key]) for key in profile_fields) * 100.0 / len(profile_fields), 2
                )
                m["tenant_status"] = tenant["status"]

            billing = (await self.db.execute(text("""
                SELECT credit_balance
                  FROM tenant_billing
                 WHERE tenant_id = :target_id AND vertical_key = 'home_services'
                 ORDER BY updated_at DESC NULLS LAST LIMIT 1
            """), {"target_id": str(target_id)})).mappings().one_or_none()
            if billing:
                credit_ready = float(billing["credit_balance"] or 0) > 0
                m["usage_credit_score"] = 100.0 if credit_ready else 0.0
                m["usage_credit_depleted"] = not credit_ready

            active_staff = int((await self.db.execute(text("""
                SELECT count(*) FROM users
                 WHERE tenant_id = :target_id AND role = 'staff'
                   AND is_active IS TRUE AND deleted_at IS NULL
            """), {"target_id": str(target_id)})).scalar_one())
            m["staff_availability_score"] = 100.0 if active_staff > 0 else 0.0

            response_minutes = (await self.db.execute(text("""
                SELECT avg(EXTRACT(EPOCH FROM (provider_responded_at - created_at)) / 60.0)
                  FROM customer_complaints
                 WHERE tenant_id = :target_id AND provider_responded_at IS NOT NULL
            """), {"target_id": str(target_id)})).scalar_one_or_none()
            if response_minutes is not None:
                m["response_time_minutes"] = round(float(response_minutes), 2)
        elif target_type in ("staff", "technician", "tenant_staff"):
            verified = bool((await self.db.execute(
                text("SELECT is_verified FROM users WHERE id = :t"),
                {"t": str(target_id)})).scalar_one_or_none())
            m["document_verified"] = verified
            m["document_verification_score"] = 100.0 if verified else 0.0

        return m

    async def enqueue_recalculation_job(self, job_type: str, scope_type: str = "all",
                                        scope_id: uuid.UUID | None = None,
                                        triggered_by: str = "manual") -> dict:
        """Queue a platform sweep and return immediately.

        The sweep itself runs in `app/jobs/trust_quality_worker.py`. It is not
        executed here because re-scoring every provider, technician and customer
        against every active rule is minutes of database work at any real size,
        and doing it inline would hold an HTTP request open for all of it — the
        admin's browser would time out long before the work finished, leaving a
        job row stuck at `running` with no way to tell a dead sweep from a slow
        one. Enqueuing returns in milliseconds and the console tracks progress.

        Only one sweep may be pending or in flight at a time: a second identical
        sweep queued behind the first would recompute the same rows from the same
        rules for no benefit, so the in-flight job is returned instead.
        """
        if job_type not in ("badges", "health", "all"):
            raise ServiceOSException("VALIDATION_ERROR", "job_type must be one of badges|health|all")
        if scope_type not in ("all", "tenant"):
            raise ServiceOSException("VALIDATION_ERROR", "scope_type must be one of all|tenant")
        if scope_type == "tenant" and scope_id is None:
            raise ServiceOSException("VALIDATION_ERROR", "scope_id is required when scope_type is 'tenant'.")

        active = (await self.db.execute(
            select(TrustQualityRecalculationJob)
            .where(TrustQualityRecalculationJob.status.in_(("queued", "running", "cancelling")))
            .order_by(TrustQualityRecalculationJob.created_at.desc())
            .limit(1)
        )).scalars().first()
        if active is not None:
            return {**active.to_dict(), "already_running": True}

        job = TrustQualityRecalculationJob(
            job_type=job_type, scope_type=scope_type, scope_id=scope_id, status="queued",
            triggered_by=triggered_by, triggered_by_user_id=self.actor_id,
            created_at=_now(), updated_at=_now(),
        )
        self.db.add(job)
        await self.db.flush()
        self._audit("recalculation_job.queued", target_type="recalculation_job",
                    target_id=job.id, new_value=job.to_dict())
        await self.db.commit()
        return {**job.to_dict(), "already_running": False}

    async def cancel_recalculation_job(self, job_id: uuid.UUID) -> dict:
        """Ask a queued or running sweep to stop.

        A queued job is cancelled outright. A running one is marked `cancelling`
        and stops at its next batch boundary — the batch in flight is allowed to
        finish so the scores it has already computed are committed rather than
        thrown away.
        """
        job = await self.db.get(TrustQualityRecalculationJob, job_id)
        if job is None:
            raise ServiceOSException("NOT_FOUND", "Recalculation job not found.")
        if job.status == "queued":
            job.status = "cancelled"
            job.completed_at = _now()
        elif job.status == "running":
            job.status = "cancelling"
        else:
            raise ServiceOSException(
                "VALIDATION_ERROR", f"A '{job.status}' job cannot be cancelled.")
        job.updated_at = _now()
        self._audit("recalculation_job.cancelled", target_type="recalculation_job",
                    target_id=job.id, new_value=job.to_dict())
        await self.db.commit()
        return job.to_dict()

    async def get_recalculation_job(self, job_id: uuid.UUID) -> dict:
        job = await self.db.get(TrustQualityRecalculationJob, job_id)
        if job is None:
            raise ServiceOSException("NOT_FOUND", "Recalculation job not found.")
        return job.to_dict()

    async def list_recalculation_jobs(self, status: str | None = None,
                                      limit: int = 25, offset: int = 0) -> dict:
        """A page of job history, newest first.

        Paginated rather than returning the table: sweeps accumulate for as long
        as the platform runs, and a console that reads every row it has ever
        written gets slower every day it stays up.
        """
        limit = max(1, min(limit, 200))
        where = []
        if status:
            where.append(TrustQualityRecalculationJob.status == status)
        total = int((await self.db.execute(
            select(func.count()).select_from(TrustQualityRecalculationJob).where(*where)
        )).scalar_one())
        rows = (await self.db.execute(
            select(TrustQualityRecalculationJob).where(*where)
            .order_by(TrustQualityRecalculationJob.created_at.desc())
            .limit(limit).offset(max(0, offset))
        )).scalars().all()
        return {"items": [j.to_dict() for j in rows], "total": total,
                "limit": limit, "offset": max(0, offset)}

    async def list_audit_logs(self, target_type: str | None = None, action_type: str | None = None,
                              limit: int = 50, offset: int = 0) -> dict:
        """A page of the engine's audit trail, newest first."""
        limit = max(1, min(limit, 200))
        where = []
        if target_type:
            where.append(TrustQualityAuditLog.target_type == target_type)
        if action_type:
            where.append(TrustQualityAuditLog.action_type == action_type)
        total = int((await self.db.execute(
            select(func.count()).select_from(TrustQualityAuditLog).where(*where)
        )).scalar_one())
        rows = (await self.db.execute(
            select(TrustQualityAuditLog).where(*where)
            .order_by(TrustQualityAuditLog.created_at.desc())
            .limit(limit).offset(max(0, offset))
        )).scalars().all()
        return {"items": [r.to_dict() for r in rows], "total": total,
                "limit": limit, "offset": max(0, offset)}

    # ── Engine Output (scores) ───────────────────────────────────────────────

    async def list_health_scores(self, target_type: str | None = None, band_key: str | None = None,
                                 formula_id: uuid.UUID | None = None,
                                 limit: int = 25, offset: int = 0) -> dict:
        """Who scored what. The health engine's actual output.

        Scores are joined to the target's display name in SQL rather than looked
        up per row, so rendering a page costs two queries whatever the page size.
        """
        limit = max(1, min(limit, 200))
        where, params = [], {}
        if target_type:
            where.append("hs.target_type = :target_type")
            params["target_type"] = target_type
        if band_key:
            where.append("hs.band_key = :band_key" if band_key != "__unbanded__"
                         else "hs.band_key IS NULL")
            if band_key != "__unbanded__":
                params["band_key"] = band_key
        if formula_id:
            where.append("hs.formula_id = CAST(:formula_id AS uuid)")
            params["formula_id"] = str(formula_id)
        canonical = "hs.target_type IN ('tenant', 'technician') AND f.status = 'active'"
        effective_clause = (
            f"WHERE {canonical} AND " + " AND ".join(where)
            if where else f"WHERE {canonical}"
        )
        total = int((await self.db.execute(text(
            f"SELECT count(*) FROM health_scores hs "
            f"JOIN health_formulas f ON f.id = hs.formula_id {effective_clause}"
        ), params)).scalar_one())
        rows = (await self.db.execute(text(
            f"""SELECT hs.id, hs.target_type, hs.target_id, hs.formula_id, hs.score,
                       hs.band_key, hs.risk_level, hs.calculated_at,
                       hs.component_breakdown_json, hs.penalties_json, hs.bonuses_json,
                       hs.recommended_actions_json,
                       f.name AS formula_name,
                       COALESCE(t.business_name, u.full_name, u.email) AS target_name
                FROM health_scores hs
                JOIN health_formulas f ON f.id = hs.formula_id
                LEFT JOIN tenants t ON t.id = hs.target_id
                LEFT JOIN users u ON u.id = hs.target_id
                {effective_clause}
                ORDER BY hs.score ASC, hs.calculated_at DESC
                LIMIT :limit OFFSET :offset"""),
            {**params, "limit": limit, "offset": max(0, offset)})).mappings().all()
        return {
            "items": [{
                "id": str(r["id"]), "target_type": r["target_type"],
                "target_id": str(r["target_id"]), "target_name": r["target_name"],
                "formula_id": str(r["formula_id"]), "formula_name": r["formula_name"],
                "score": float(r["score"]), "band_key": r["band_key"],
                "risk_level": r["risk_level"],
                "component_breakdown": r["component_breakdown_json"],
                "penalties": r["penalties_json"], "bonuses": r["bonuses_json"],
                "recommended_actions": r["recommended_actions_json"],
                "calculated_at": r["calculated_at"].isoformat() if r["calculated_at"] else None,
            } for r in rows],
            "total": total, "limit": limit, "offset": max(0, offset),
        }

    async def list_risk_scores(self, target_type: str | None = None, risk_level: str | None = None,
                               limit: int = 25, offset: int = 0) -> dict:
        """Who the risk engine flagged, worst first."""
        limit = max(1, min(limit, 200))
        where, params = [], {}
        if target_type:
            where.append("rs.target_type = :target_type")
            params["target_type"] = target_type
        if risk_level:
            where.append("rs.risk_level = :risk_level")
            params["risk_level"] = risk_level
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        total = int((await self.db.execute(
            text(f"SELECT count(*) FROM risk_scores rs {clause}"), params)).scalar_one())
        rows = (await self.db.execute(text(
            f"""SELECT rs.id, rs.target_type, rs.target_id, rs.risk_score, rs.risk_level,
                       rs.reasons_json, rs.recommended_actions_json,
                       rs.bookable_impact, rs.finance_impact, rs.calculated_at,
                       COALESCE(t.business_name, u.full_name, u.email) AS target_name
                FROM risk_scores rs
                LEFT JOIN tenants t ON t.id = rs.target_id
                LEFT JOIN users u ON u.id = rs.target_id
                {clause}
                ORDER BY rs.risk_score DESC, rs.calculated_at DESC
                LIMIT :limit OFFSET :offset"""),
            {**params, "limit": limit, "offset": max(0, offset)})).mappings().all()
        return {
            "items": [{
                "id": str(r["id"]), "target_type": r["target_type"],
                "target_id": str(r["target_id"]), "target_name": r["target_name"],
                "risk_score": float(r["risk_score"]), "risk_level": r["risk_level"],
                "reasons": r["reasons_json"] or [],
                "recommended_actions": r["recommended_actions_json"] or [],
                "bookable_impact": r["bookable_impact"], "finance_impact": r["finance_impact"],
                "calculated_at": r["calculated_at"].isoformat() if r["calculated_at"] else None,
            } for r in rows],
            "total": total, "limit": limit, "offset": max(0, offset),
        }

    async def get_engine_overview(self) -> dict:
        """Headline counts for the console, in one round trip per table.

        Every number the dashboard shows is an aggregate computed in the
        database. Counting in Python would mean shipping every score row to the
        API process to length-check a list.
        """
        fixed_keys_sql = ", ".join(f"'{key}'" for key in sorted(FIXED_BADGE_KEYS))
        row = (await self.db.execute(text("""
            SELECT
              (SELECT count(*) FROM badge_definitions
                 WHERE status = 'active' AND badge_key IN (__FIXED_BADGE_KEYS__))   AS active_badges,
              (SELECT count(*) FROM badge_rules br
                 JOIN badge_definitions bd ON bd.id = br.badge_id
                WHERE br.status = 'active' AND bd.badge_key IN (__FIXED_BADGE_KEYS__)) AS active_badge_rules,
              (SELECT count(*) FROM badge_assignments ba
                 JOIN badge_definitions bd ON bd.id = ba.badge_id
                WHERE ba.status = 'active' AND bd.badge_key IN (__FIXED_BADGE_KEYS__)) AS badges_held,
              (SELECT count(*) FROM health_formulas
                WHERE status = 'active' AND target_type IN ('tenant','technician')) AS active_formulas,
              (SELECT count(*) FROM health_scores hs
                 JOIN health_formulas hf ON hf.id = hs.formula_id
                WHERE hf.status = 'active' AND hs.target_type IN ('tenant','technician')) AS scored_targets,
              (SELECT count(*) FROM health_scores hs
                 JOIN health_formulas hf ON hf.id = hs.formula_id
                WHERE hf.status = 'active' AND hs.target_type IN ('tenant','technician')
                  AND hs.band_key IS NULL)                                          AS unbanded_targets,
              (SELECT count(*) FROM trust_quality_recalculation_jobs
                 WHERE status IN ('queued','running','cancelling'))                 AS jobs_in_flight
        """.replace("__FIXED_BADGE_KEYS__", fixed_keys_sql)))).mappings().one()
        return {k: int(v or 0) for k, v in row.items()}


    # ── Seed Defaults ────────────────────────────────────────────────────────

    async def seed_defaults_preview(self) -> dict:
        return {
            "badges": len(_DEFAULT_BADGES),
            "badge_rules": len(_DEFAULT_BADGE_RULES),
            "health_formulas": len(_DEFAULT_HEALTH_FORMULAS),
        }

    async def seed_defaults(self) -> dict:
        created = {"badges": 0, "badge_rules": 0, "health_formulas": 0}
        badge_id_by_key: dict[str, uuid.UUID] = {}

        for spec in _DEFAULT_BADGES:
            existing = await self.db.scalar(select(BadgeDefinition).where(BadgeDefinition.badge_key == spec["badge_key"]))
            if existing:
                existing.name = spec["name"]
                existing.description = spec.get("description")
                existing.target_type = spec["target_type"]
                existing.customer_visible = spec.get("customer_visible", False)
                existing.tenant_visible = spec.get("tenant_visible", True)
                existing.admin_only = False
                existing.icon = spec.get("icon")
                existing.color = spec.get("color")
                existing.updated_at = _now()
                badge_id_by_key[spec["badge_key"]] = existing.id
                continue
            b = BadgeDefinition(
                badge_key=spec["badge_key"], name=spec["name"], description=spec.get("description"),
                target_type=spec["target_type"], customer_visible=spec.get("customer_visible", False),
                tenant_visible=spec.get("tenant_visible", True),
                icon=spec.get("icon"), color=spec.get("color"), status="active",
                created_at=_now(), updated_at=_now(),
            )
            self.db.add(b)
            await self.db.flush()
            badge_id_by_key[spec["badge_key"]] = b.id
            created["badges"] += 1

        for spec in _DEFAULT_BADGE_RULES:
            existing = await self.db.scalar(select(BadgeRule).where(BadgeRule.rule_key == spec["rule_key"]))
            if existing:
                continue
            badge_id = badge_id_by_key.get(spec["badge_key"])
            if not badge_id:
                continue
            r = BadgeRule(
                rule_key=spec["rule_key"], badge_id=badge_id, target_type=spec["target_type"],
                rule_type=spec.get("rule_type", "auto_award"), scope_type="global",
                auto_award=True, manual_award_allowed=True, status="active", version=1,
                created_at=_now(), updated_at=_now(),
            )
            self.db.add(r)
            await self.db.flush()
            for c in spec.get("criteria", []):
                self.db.add(BadgeRuleCriteria(
                    badge_rule_id=r.id, metric_key=c["metric_key"], operator=c["operator"],
                    value_json=c["value"], is_required=True, created_at=_now(), updated_at=_now(),
                ))
            for c in spec.get("removal_criteria", []):
                self.db.add(BadgeRuleRemovalCriteria(
                    badge_rule_id=r.id, metric_key=c["metric_key"], operator=c["operator"],
                    value_json=c["value"], created_at=_now(), updated_at=_now(),
                ))
            created["badge_rules"] += 1

        for spec in _DEFAULT_HEALTH_FORMULAS:
            existing = await self.db.scalar(select(HealthFormula).where(HealthFormula.formula_key == spec["formula_key"]))
            if existing:
                continue
            f = HealthFormula(
                formula_key=spec["formula_key"], name=spec["name"], target_type=spec["target_type"],
                scope_type="global", base_score=100, min_score=0, max_score=100,
                status="active", version=1, created_at=_now(), updated_at=_now(),
            )
            self.db.add(f)
            await self.db.flush()
            for c in spec["components"]:
                self.db.add(HealthFormulaComponent(
                    formula_id=f.id, metric_key=c["metric_key"], weight_percent=c["weight_percent"],
                    direction=c.get("direction", "positive"), min_value=c.get("min_value", 0),
                    max_value=c.get("max_value", 100), is_required=False,
                    created_at=_now(), updated_at=_now(),
                ))
            for p in spec.get("penalties", []):
                self.db.add(HealthPenaltyRule(
                    formula_id=f.id, metric_key=p["metric_key"], operator=p["operator"],
                    value_json=p["value"], penalty_points=p["penalty_points"],
                    hard_override_score=p.get("hard_override_score"), created_at=_now(), updated_at=_now(),
                ))
            for b in spec.get("bonuses", []):
                self.db.add(HealthBonusRule(
                    formula_id=f.id, metric_key=b["metric_key"], operator=b["operator"],
                    value_json=b["value"], bonus_points=b["bonus_points"],
                    created_at=_now(), updated_at=_now(),
                ))
            for band in spec["bands"]:
                self.db.add(HealthBandRule(
                    formula_id=f.id, band_key=band["band_key"], band_name=band["band_name"],
                    min_score=band["min_score"], max_score=band["max_score"],
                    bookable_allowed=band.get("bookable_allowed", True),
                    recommended_action=band.get("recommended_action"),
                    created_at=_now(), updated_at=_now(),
                ))
            created["health_formulas"] += 1

        if any(created.values()):
            self._audit("trust_quality.seed_defaults", new_value=created)
        await self.db.commit()
        return created


# ── Default seed specs (Home Services baseline; extended per-vertical in later phases) ──

# The seeded badge rows mirror FIXED_BADGE_CATALOG. Old custom rows can stay in
# history, but every active/read path above ignores them.
_DEFAULT_BADGES = list(FIXED_BADGE_CATALOG)

_DEFAULT_BADGE_RULES = [
    {
        "rule_key": "rule_top_rated_provider", "badge_key": "top_rated_provider", "target_type": "tenant",
        "rule_type": "quality_based",
        "criteria": [
            {"metric_key": "average_rating", "operator": "greater_than_or_equal", "value": 4.6},
            {"metric_key": "review_count", "operator": "greater_than_or_equal", "value": 50},
            {"metric_key": "completed_jobs_count", "operator": "greater_than_or_equal", "value": 100},
            {"metric_key": "complaint_rate", "operator": "less_than_or_equal", "value": 3},
        ],
        "removal_criteria": [
            {"metric_key": "average_rating", "operator": "less_than", "value": 4.3},
            {"metric_key": "complaint_rate", "operator": "greater_than", "value": 8},
        ],
    },
    {
        "rule_key": "rule_verified_provider", "badge_key": "verified_provider", "target_type": "tenant",
        "rule_type": "verification_based",
        "criteria": [
            {"metric_key": "document_verified", "operator": "equals", "value": True},
            {"metric_key": "owner_verified", "operator": "equals", "value": True},
        ],
    },
    {
        "rule_key": "rule_fast_response", "badge_key": "fast_response", "target_type": "tenant",
        "rule_type": "performance_based",
        "criteria": [{"metric_key": "response_time_minutes", "operator": "less_than_or_equal", "value": 15}],
    },
    {
        "rule_key": "rule_low_complaint_provider", "badge_key": "low_complaint_provider", "target_type": "tenant",
        "rule_type": "quality_based",
        "criteria": [
            {"metric_key": "completed_jobs_count", "operator": "greater_than_or_equal", "value": 25},
            {"metric_key": "complaint_rate", "operator": "less_than_or_equal", "value": 3},
        ],
        "removal_criteria": [
            {"metric_key": "complaint_rate", "operator": "greater_than", "value": 8},
        ],
    },
    {
        "rule_key": "rule_verified_staff", "badge_key": "verified_staff", "target_type": "staff",
        "rule_type": "verification_based",
        "criteria": [{"metric_key": "document_verified", "operator": "equals", "value": True}],
    },
    {
        "rule_key": "rule_punctual_staff", "badge_key": "punctual_staff", "target_type": "staff",
        "rule_type": "performance_based",
        "criteria": [{"metric_key": "on_time_arrival_rate", "operator": "greater_than_or_equal", "value": 95}],
    },
    {
        "rule_key": "rule_customer_loved_staff", "badge_key": "customer_loved_staff", "target_type": "staff",
        "rule_type": "quality_based",
        "criteria": [
            {"metric_key": "average_rating", "operator": "greater_than_or_equal", "value": 4.7},
            {"metric_key": "review_count", "operator": "greater_than_or_equal", "value": 20},
        ],
    },
    {
        "rule_key": "rule_safety_champion_staff", "badge_key": "safety_champion_staff", "target_type": "staff",
        "rule_type": "compliance_based",
        "criteria": [
            {"metric_key": "job_completion_rate", "operator": "greater_than_or_equal", "value": 95},
            {"metric_key": "complaint_rate", "operator": "less_than_or_equal", "value": 2},
        ],
    },
    {
        "rule_key": "rule_verified_technician", "badge_key": "verified_technician", "target_type": "technician",
        "rule_type": "verification_based",
        "criteria": [{"metric_key": "document_verified", "operator": "equals", "value": True}],
    },
    {
        "rule_key": "rule_precision_technician", "badge_key": "precision_technician", "target_type": "technician",
        "rule_type": "performance_based",
        "criteria": [
            {"metric_key": "job_completion_rate", "operator": "greater_than_or_equal", "value": 92},
            {"metric_key": "complaint_rate", "operator": "less_than_or_equal", "value": 3},
        ],
    },
    {
        "rule_key": "rule_top_technician", "badge_key": "top_technician", "target_type": "technician",
        "rule_type": "quality_based",
        "criteria": [
            {"metric_key": "average_rating", "operator": "greater_than_or_equal", "value": 4.7},
            {"metric_key": "job_completion_rate", "operator": "greater_than_or_equal", "value": 95},
        ],
    },
    {
        "rule_key": "rule_elite_technician", "badge_key": "elite_technician", "target_type": "technician",
        "rule_type": "quality_based",
        "criteria": [
            {"metric_key": "average_rating", "operator": "greater_than_or_equal", "value": 4.85},
            {"metric_key": "review_count", "operator": "greater_than_or_equal", "value": 40},
            {"metric_key": "job_completion_rate", "operator": "greater_than_or_equal", "value": 97},
        ],
    },
]

_DEFAULT_HEALTH_FORMULAS = [
    {
        "formula_key": "provider_business_health_default", "name": "Provider Business Health",
        "target_type": "tenant",
        "components": [
            {"metric_key": "profile_completion_percent", "weight_percent": 10},
            {"metric_key": "document_verification_score", "weight_percent": 10},
            {"metric_key": "usage_credit_score", "weight_percent": 20},
            {"metric_key": "job_completion_rate", "weight_percent": 15},
            {"metric_key": "response_sla_score", "weight_percent": 10},
            {"metric_key": "rating_score", "weight_percent": 15},
            {"metric_key": "complaint_dispute_score", "weight_percent": 10, "direction": "negative"},
            {"metric_key": "cancellation_rate", "weight_percent": 5, "direction": "negative"},
            {"metric_key": "staff_availability_score", "weight_percent": 5},
        ],
        "penalties": [
            {"metric_key": "tenant_status", "operator": "equals", "value": "suspended", "penalty_points": 0, "hard_override_score": 0},
            {"metric_key": "usage_credit_depleted", "operator": "equals", "value": True, "penalty_points": 20},
            {"metric_key": "complaint_rate", "operator": "greater_than", "value": 10, "penalty_points": 20},
            {"metric_key": "average_rating", "operator": "less_than", "value": 3.5, "penalty_points": 20},
        ],
        "bonuses": [
            {"metric_key": "average_rating", "operator": "greater_than_or_equal", "value": 4.7, "bonus_points": 5},
            {"metric_key": "job_completion_rate", "operator": "greater_than_or_equal", "value": 95, "bonus_points": 5},
        ],
        "bands": [
            {"band_key": "platinum", "band_name": "Platinum", "min_score": 90, "max_score": 100},
            {"band_key": "gold", "band_name": "Gold", "min_score": 75, "max_score": 89.99},
            {"band_key": "silver", "band_name": "Silver", "min_score": 60, "max_score": 74.99},
            {"band_key": "watchlist", "band_name": "Watchlist", "min_score": 40, "max_score": 59.99,
             "recommended_action": "Request improvement plan"},
            {"band_key": "at_risk", "band_name": "At Risk", "min_score": 20, "max_score": 39.99,
             "recommended_action": "Put under review", "bookable_allowed": False},
            {"band_key": "blocked", "band_name": "Blocked", "min_score": 0, "max_score": 19.99,
             "recommended_action": "Stop new bookings", "bookable_allowed": False},
        ],
    },
    {
        "formula_key": "technician_performance_health_default", "name": "Technician Performance Health",
        "target_type": "technician",
        "components": [
            {"metric_key": "job_completion_rate", "weight_percent": 30},
            {"metric_key": "rating_score", "weight_percent": 25},
            {"metric_key": "on_time_arrival_rate", "weight_percent": 20},
            {"metric_key": "complaint_dispute_score", "weight_percent": 15, "direction": "negative"},
            {"metric_key": "document_verification_score", "weight_percent": 10},
        ],
        "bands": [
            {"band_key": "excellent", "band_name": "Excellent", "min_score": 90, "max_score": 100},
            {"band_key": "good", "band_name": "Good", "min_score": 75, "max_score": 89.99},
            {"band_key": "average", "band_name": "Average", "min_score": 60, "max_score": 74.99},
            {"band_key": "watchlist", "band_name": "Watchlist", "min_score": 40, "max_score": 59.99},
            {"band_key": "blocked", "band_name": "Blocked", "min_score": 0, "max_score": 39.99, "bookable_allowed": False},
        ],
    },
]
