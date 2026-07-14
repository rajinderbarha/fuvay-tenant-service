"""Trust & Quality Engine service — Phase 1.

Implements the Badge Rule Engine (criteria evaluation, simulate, award/revoke)
and the Health Rule Engine (weighted formula calculation, penalties, bonuses,
bands, risk level) plus a simple Risk Scoring Engine and synchronous
recalculation-job runner. Frontend/simulator UI and async job scheduling are
later phases — this phase makes the rules real and runnable.
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

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


VALID_BADGE_TARGETS = {"tenant", "tenant_owner", "staff", "technician", "customer", "service", "category"}
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
    "tenant_provider", "tenant_staff", "technician", "customer_account",
    "service_quality", "category_quality",
}
VALID_RISK_LEVELS = {"normal", "watchlist", "high_risk", "finance_blocked", "quality_blocked", "suspended"}
VALID_AWARD_SOURCES = {"auto_rule", "manual_admin", "system_migration", "seasonal_campaign", "appeal_approved"}


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
        stmt = select(BadgeDefinition)
        if target_type:
            stmt = stmt.where(BadgeDefinition.target_type == target_type)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [r.to_dict() for r in rows]

    async def create_badge_definition(self, data: dict) -> dict:
        badge_key = (data.get("badge_key") or "").strip()
        if not badge_key:
            raise ServiceOSException("VALIDATION_ERROR", "badge_key is required.")
        target_type = data.get("target_type")
        if target_type not in VALID_BADGE_TARGETS:
            raise ServiceOSException("VALIDATION_ERROR", f"target_type must be one of {sorted(VALID_BADGE_TARGETS)}")
        existing = await self.db.scalar(select(BadgeDefinition).where(BadgeDefinition.badge_key == badge_key))
        if existing:
            raise ServiceOSException("DUPLICATE", f"Badge key '{badge_key}' already exists.")
        b = BadgeDefinition(
            badge_key=badge_key, name=data["name"], description=data.get("description"),
            icon=data.get("icon"), color=data.get("color"), target_type=target_type,
            customer_visible=data.get("customer_visible", False),
            tenant_visible=data.get("tenant_visible", True),
            admin_only=data.get("admin_only", False),
            status=data.get("status", "active"),
            created_at=_now(), updated_at=_now(),
        )
        self.db.add(b)
        await self.db.flush()
        self._audit("badge_definition.created", target_type=target_type, target_id=b.id, new_value=b.to_dict())
        await self.db.commit()
        return b.to_dict()

    async def update_badge_definition(self, badge_id: uuid.UUID, data: dict) -> dict:
        """Patch a badge's presentation/visibility. Only the fields present in
        `data` change; badge_key and target_type are immutable identity."""
        b = await self._get_badge(badge_id)
        old = b.to_dict()
        for field in ("name", "description", "icon", "color",
                      "customer_visible", "tenant_visible", "admin_only", "status"):
            if field in data and data[field] is not None:
                setattr(b, field, data[field])
        b.updated_at = _now()
        self._audit("badge_definition.updated", target_type=b.target_type, target_id=b.id,
                    old_value=old, new_value=b.to_dict())
        await self.db.commit()
        return b.to_dict()

    async def _get_badge(self, badge_id: uuid.UUID) -> BadgeDefinition:
        b = await self.db.get(BadgeDefinition, badge_id)
        if not b:
            raise ServiceOSException("NOT_FOUND", "Badge definition not found.")
        return b

    # ── Badge Rules ──────────────────────────────────────────────────────────

    async def list_badge_rules(self, target_type: str | None = None, status: str | None = None) -> list[dict]:
        stmt = select(BadgeRule)
        if target_type:
            stmt = stmt.where(BadgeRule.target_type == target_type)
        if status:
            stmt = stmt.where(BadgeRule.status == status)
        rows = (await self.db.execute(stmt)).scalars().all()
        out = []
        for r in rows:
            d = r.to_dict()
            d["badge"] = (await self._get_badge(r.badge_id)).to_dict()
            d["criteria"] = [c.to_dict() for c in await self._get_criteria(r.id)]
            d["removal_criteria"] = [c.to_dict() for c in await self._get_removal_criteria(r.id)]
            out.append(d)
        return out

    async def get_badge_rule(self, rule_id: uuid.UUID) -> dict:
        r = await self._get_badge_rule(rule_id)
        d = r.to_dict()
        d["badge"] = (await self._get_badge(r.badge_id)).to_dict()
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
        await self._get_badge(badge_id)
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

        r = BadgeRule(
            rule_key=rule_key, badge_id=badge_id, target_type=data.get("target_type") or (await self._get_badge(badge_id)).target_type,
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
            await self._get_badge(badge_id)
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
        self._audit("badge_rule.simulated", target_type="badge_rule", target_id=rule_id, new_value=result)
        await self.db.commit()
        return result

    async def manual_award_badge(self, badge_id: uuid.UUID, target_type: str, target_id: uuid.UUID,
                                  reason: str, expires_at: datetime | None = None) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "reason is required for a manual badge award.")
        await self._get_badge(badge_id)
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
            if a.expires_at and a.expires_at < now:
                continue
            if audience == "customer" and not b.customer_visible:
                continue
            if audience == "provider" and not (b.tenant_visible or b.customer_visible):
                continue
            earned = a.earned_at.isoformat() if a.earned_at else None
            prev = by_key.get(b.badge_key)
            if prev and (prev["earned_at"] or "") <= (earned or ""):
                continue  # keep the earlier assignment
            by_key[b.badge_key] = {
                "assignment_id": str(a.id), "badge_key": b.badge_key, "name": b.name,
                "description": b.description, "icon": b.icon, "color": b.color,
                "customer_visible": b.customer_visible, "tenant_visible": b.tenant_visible,
                "award_source": a.award_source, "earned_at": earned,
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
        # Most-recently earned first.
        return sorted(by_key.values(), key=lambda x: x["earned_at"] or "", reverse=True)

    async def recalculate_badges_for_target(self, target_type: str, target_id: uuid.UUID, metrics: dict) -> list[dict]:
        """Evaluate all active auto-award rules for target_type against metrics; award/revoke as needed."""
        rules = (await self.db.execute(
            select(BadgeRule).where(BadgeRule.target_type == target_type, BadgeRule.status == "active",
                                     BadgeRule.auto_award == True)  # noqa: E712
        )).scalars().all()
        results = []
        for r in rules:
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
        stmt = select(HealthFormula)
        if target_type:
            stmt = stmt.where(HealthFormula.target_type == target_type)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [f.to_dict() for f in rows]

    async def _get_formula(self, formula_id: uuid.UUID) -> HealthFormula:
        f = await self.db.get(HealthFormula, formula_id)
        if not f:
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
        if status == "active" and components and abs(total_weight - 100.0) > 0.01:
            raise ServiceOSException("VALIDATION_ERROR", f"Total component weights must equal 100% (got {total_weight}%).")

        bands = data.get("bands", [])
        if status == "active":
            self._validate_bands(bands)

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
        for field in ("name", "scope_type", "scope_id", "base_score", "min_score", "max_score", "status"):
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
        base = float(formula.base_score)
        breakdown = []
        weighted_sum = 0.0
        contributing_weight = 0.0
        for c in components:
            raw = metrics.get(c.metric_key)
            if raw is None:
                if c.is_required:
                    raw = 0
                else:
                    continue
            contributing_weight += float(c.weight_percent)
            norm = float(raw)
            lo = float(c.min_value) if c.min_value is not None else 0.0
            hi = float(c.max_value) if c.max_value is not None else 100.0
            if hi > lo:
                norm = max(0.0, min(1.0, (norm - lo) / (hi - lo))) * 100.0
            if c.direction == "negative":
                norm = 100.0 - norm
            contribution = norm * float(c.weight_percent) / 100.0
            weighted_sum += contribution
            breakdown.append({"metric_key": c.metric_key, "raw_value": raw, "normalized": norm,
                               "weight_percent": float(c.weight_percent), "contribution": contribution})

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

        if not components or contributing_weight <= 0:
            score = base
        else:
            score = weighted_sum * 100.0 / contributing_weight
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

    async def simulate_health_formula(self, formula_id: uuid.UUID, metrics: dict) -> dict:
        f = await self._get_formula(formula_id)
        components = await self._get_components(formula_id)
        penalties = await self._get_penalties(formula_id)
        bonuses = await self._get_bonuses(formula_id)
        bands = await self._get_bands(formula_id)
        result = self._calc_score(f, components, penalties, bonuses, bands, metrics)
        result["formula_id"] = str(formula_id)
        self._audit("health_formula.simulated", target_type="health_formula", target_id=formula_id, new_value=result)
        await self.db.commit()
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
        self._audit("health_score.calculated", target_type=target_type, target_id=target_id, new_value=hs.to_dict())
        await self.db.commit()
        return hs.to_dict()

    # ── Risk Scoring (simple) ────────────────────────────────────────────────

    async def recalculate_risk_for_target(self, target_type: str, target_id: uuid.UUID, metrics: dict) -> dict:
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
        self._audit("risk_score.calculated", target_type=target_type, target_id=target_id, new_value=rs.to_dict())
        await self.db.commit()
        return rs.to_dict()

    # ── Recalculation Job (synchronous phase-1 runner) ──────────────────────

    async def _enumerate_targets(self, target_type: str, scope_type: str,
                                  scope_id: uuid.UUID | None) -> list[uuid.UUID]:
        """The rows a job of this target_type has to re-score.

        Returns [] for a target_type with no entity table behind it (e.g.
        "service_quality", which scores an offering rather than an actor) — such
        a formula is skipped rather than counted as a failure.
        """
        sql = _TARGET_SOURCE_SQL.get(target_type)
        if not sql:
            return []
        params: dict = {}
        if scope_type == "tenant" and scope_id is not None:
            col = "id" if target_type in ("tenant", "tenant_provider") else "tenant_id"
            sql += f" AND {col} = :scope_id"
            params["scope_id"] = str(scope_id)
        rows = (await self.db.execute(text(sql), params)).scalars().all()
        return [r if isinstance(r, uuid.UUID) else uuid.UUID(str(r)) for r in rows]

    async def _gather_metrics(self, target_type: str, target_id: uuid.UUID) -> dict:
        """Compute a target's live metrics from the operational tables.

        Only metrics with a real source are returned. A metric with no source is
        left OUT rather than defaulted, because a criterion that reads a missing
        metric evaluates false — which correctly withholds a badge instead of
        awarding one off a fabricated number.
        """
        m: dict = {}

        if target_type in ("tenant", "tenant_provider"):
            job_col, review_col, complaint_col = "tenant_id", "tenant_id", "tenant_id"
        elif target_type == "technician":
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

        if target_type in ("tenant", "tenant_provider"):
            v = (await self.db.execute(
                text("SELECT verification_status FROM tenants WHERE id = :t"),
                {"t": str(target_id)})).scalar_one_or_none()
            verified = v == "verified"
            m["document_verified"] = verified
            m["owner_verified"] = verified
            m["document_verification_score"] = 100.0 if verified else 0.0

        return m

    async def run_recalculation_job(self, job_type: str, scope_type: str = "all",
                                     scope_id: uuid.UUID | None = None,
                                     triggered_by: str = "manual") -> dict:
        """Re-score every in-scope target against the active rules.

        This runs the badge, health and risk engines for real: it enumerates the
        targets, gathers each one's live metrics, and applies the rules. The job
        row's counts are the true number of targets processed.
        """
        if job_type not in ("badges", "health", "risk", "all"):
            raise ServiceOSException("VALIDATION_ERROR", "job_type must be one of badges|health|risk|all")
        job = TrustQualityRecalculationJob(
            job_type=job_type, scope_type=scope_type, scope_id=scope_id, status="running",
            triggered_by=triggered_by, triggered_by_user_id=self.actor_id,
            started_at=_now(), created_at=_now(), updated_at=_now(),
        )
        self.db.add(job)
        await self.db.flush()

        kinds = ("badges", "health", "risk") if job_type == "all" else (job_type,)

        # (kind, target_type, formula) units of work, deduped by target so a
        # target is counted once even when several rules cover it.
        units: list[tuple[str, str, HealthFormula | None]] = []
        if "badges" in kinds:
            for tt in (await self.db.execute(
                select(BadgeRule.target_type).where(
                    BadgeRule.status == "active",
                    BadgeRule.auto_award == True,  # noqa: E712
                ).distinct())).scalars().all():
                units.append(("badges", tt, None))
        if "health" in kinds:
            for f in (await self.db.execute(
                select(HealthFormula).where(HealthFormula.status == "active"))).scalars().all():
                units.append(("health", f.target_type, f))
        if "risk" in kinds:
            for tt in (await self.db.execute(
                select(RiskRule.target_type).where(RiskRule.status == "active").distinct()
            )).scalars().all():
                units.append(("risk", tt, None))

        processed = failed = 0
        errors: list[str] = []
        metrics_cache: dict[tuple[str, uuid.UUID], dict] = {}

        for kind, target_type, formula in units:
            for target_id in await self._enumerate_targets(target_type, scope_type, scope_id):
                key = (target_type, target_id)
                try:
                    if key not in metrics_cache:
                        metrics_cache[key] = await self._gather_metrics(target_type, target_id)
                    metrics = metrics_cache[key]
                    if kind == "badges":
                        await self.recalculate_badges_for_target(target_type, target_id, metrics)
                    elif kind == "health":
                        await self.recalculate_health_for_target(
                            formula.id, target_type, target_id, metrics)
                    else:
                        await self.recalculate_risk_for_target(target_type, target_id, metrics)
                    processed += 1
                except Exception as exc:  # one bad target must not sink the run
                    failed += 1
                    if len(errors) < 10:
                        errors.append(f"{kind}/{target_type}/{target_id}: {exc}")

        job.total_count = processed + failed
        job.processed_count = processed
        job.failed_count = failed
        job.error_summary = "; ".join(errors) or None
        job.status = "completed" if failed == 0 else "completed_with_errors"
        job.completed_at = _now()
        job.updated_at = _now()
        self._audit("recalculation_job.completed", target_type="recalculation_job", target_id=job.id, new_value=job.to_dict())
        await self.db.commit()
        return job.to_dict()

    async def list_recalculation_jobs(self) -> list[dict]:
        rows = (await self.db.execute(
            select(TrustQualityRecalculationJob).order_by(TrustQualityRecalculationJob.created_at.desc())
        )).scalars().all()
        return [j.to_dict() for j in rows]

    async def list_audit_logs(self, target_type: str | None = None, limit: int = 100) -> list[dict]:
        stmt = select(TrustQualityAuditLog).order_by(TrustQualityAuditLog.created_at.desc()).limit(limit)
        if target_type:
            stmt = stmt.where(TrustQualityAuditLog.target_type == target_type)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [r.to_dict() for r in rows]

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

        self._audit("trust_quality.seed_defaults", new_value=created)
        await self.db.commit()
        return created


# ── Default seed specs (Home Services baseline; extended per-vertical in later phases) ──

# icon values are lucide names the frontends render (see BADGE_ICONS in the admin
# page and the shared badge components); color is the accent hex.
_DEFAULT_BADGES = [
    {"badge_key": "verified_provider", "name": "Verified Provider", "target_type": "tenant", "customer_visible": True, "icon": "shield-check", "color": "#3b82f6"},
    {"badge_key": "top_rated_provider", "name": "Top Rated Provider", "target_type": "tenant", "customer_visible": True, "icon": "star", "color": "#f59e0b"},
    {"badge_key": "fast_response", "name": "Fast Response", "target_type": "tenant", "customer_visible": True, "icon": "zap", "color": "#14b8a6"},
    {"badge_key": "low_complaint_provider", "name": "Low Complaint Provider", "target_type": "tenant", "customer_visible": False, "icon": "thumbs-up", "color": "#10b981"},
    {"badge_key": "verified_technician", "name": "Verified Technician", "target_type": "technician", "customer_visible": True, "icon": "badge-check", "color": "#3b82f6"},
    {"badge_key": "top_technician", "name": "Top Technician", "target_type": "technician", "customer_visible": True, "icon": "medal", "color": "#f59e0b"},
    {"badge_key": "frequent_booker", "name": "Frequent Booker", "target_type": "customer", "customer_visible": True, "icon": "heart", "color": "#ec4899"},
    {"badge_key": "popular_service", "name": "Popular Service", "target_type": "service", "customer_visible": True, "icon": "flame", "color": "#f97316"},
]

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
        "rule_key": "rule_verified_technician", "badge_key": "verified_technician", "target_type": "technician",
        "rule_type": "verification_based",
        "criteria": [{"metric_key": "document_verified", "operator": "equals", "value": True}],
    },
    {
        "rule_key": "rule_top_technician", "badge_key": "top_technician", "target_type": "technician",
        "rule_type": "quality_based",
        "criteria": [
            {"metric_key": "average_rating", "operator": "greater_than_or_equal", "value": 4.7},
            {"metric_key": "job_completion_rate", "operator": "greater_than_or_equal", "value": 95},
        ],
    },
]

_DEFAULT_HEALTH_FORMULAS = [
    {
        "formula_key": "provider_business_health_default", "name": "Provider Business Health",
        "target_type": "tenant_provider",
        "components": [
            {"metric_key": "profile_completion_percent", "weight_percent": 10},
            {"metric_key": "document_verification_score", "weight_percent": 10},
            {"metric_key": "security_deposit_score", "weight_percent": 10},
            {"metric_key": "package_credit_score", "weight_percent": 10},
            {"metric_key": "job_completion_rate", "weight_percent": 15},
            {"metric_key": "response_sla_score", "weight_percent": 10},
            {"metric_key": "rating_score", "weight_percent": 15},
            {"metric_key": "complaint_dispute_score", "weight_percent": 10, "direction": "negative"},
            {"metric_key": "cancellation_rate", "weight_percent": 5, "direction": "negative"},
            {"metric_key": "staff_availability_score", "weight_percent": 5},
        ],
        "penalties": [
            {"metric_key": "tenant_status", "operator": "equals", "value": "suspended", "penalty_points": 0, "hard_override_score": 0},
            {"metric_key": "security_deposit_missing", "operator": "equals", "value": True, "penalty_points": 20},
            {"metric_key": "package_expired", "operator": "equals", "value": True, "penalty_points": 20},
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
            {"metric_key": "job_completion_rate", "weight_percent": 25},
            {"metric_key": "average_rating", "weight_percent": 25},
            {"metric_key": "on_time_arrival_rate", "weight_percent": 20},
            {"metric_key": "complaint_rate", "weight_percent": 15, "direction": "negative"},
            {"metric_key": "response_time_score", "weight_percent": 10},
            {"metric_key": "attendance_score", "weight_percent": 5},
        ],
        "bands": [
            {"band_key": "excellent", "band_name": "Excellent", "min_score": 90, "max_score": 100},
            {"band_key": "good", "band_name": "Good", "min_score": 75, "max_score": 89.99},
            {"band_key": "average", "band_name": "Average", "min_score": 60, "max_score": 74.99},
            {"band_key": "watchlist", "band_name": "Watchlist", "min_score": 40, "max_score": 59.99},
            {"band_key": "blocked", "band_name": "Blocked", "min_score": 0, "max_score": 39.99, "bookable_allowed": False},
        ],
    },
    {
        "formula_key": "customer_account_health_default", "name": "Customer Account Health",
        "target_type": "customer_account",
        "components": [
            {"metric_key": "account_verification_score", "weight_percent": 20},
            {"metric_key": "completed_bookings_score", "weight_percent": 20},
            {"metric_key": "repeat_booking_rate", "weight_percent": 15},
            {"metric_key": "cancellation_rate", "weight_percent": 15, "direction": "negative"},
            {"metric_key": "no_show_rate", "weight_percent": 15, "direction": "negative"},
            {"metric_key": "dispute_abuse_score", "weight_percent": 10, "direction": "negative"},
            {"metric_key": "payment_issue_score", "weight_percent": 5, "direction": "negative"},
        ],
        "bands": [
            {"band_key": "gold", "band_name": "Gold", "min_score": 90, "max_score": 100},
            {"band_key": "healthy", "band_name": "Healthy", "min_score": 70, "max_score": 89.99},
            {"band_key": "watchlist", "band_name": "Watchlist", "min_score": 50, "max_score": 69.99},
            {"band_key": "at_risk", "band_name": "At Risk", "min_score": 30, "max_score": 49.99},
            {"band_key": "blocked", "band_name": "Blocked", "min_score": 0, "max_score": 29.99, "bookable_allowed": False},
        ],
    },
    {
        "formula_key": "service_quality_health_default", "name": "Service Quality Health",
        "target_type": "service_quality",
        "components": [
            {"metric_key": "booking_volume_score", "weight_percent": 15},
            {"metric_key": "job_completion_rate", "weight_percent": 20},
            {"metric_key": "average_rating", "weight_percent": 25},
            {"metric_key": "complaint_rate", "weight_percent": 20, "direction": "negative"},
            {"metric_key": "cancellation_rate", "weight_percent": 10, "direction": "negative"},
            {"metric_key": "sla_success_rate", "weight_percent": 10},
        ],
        "bands": [
            {"band_key": "excellent", "band_name": "Excellent", "min_score": 85, "max_score": 100},
            {"band_key": "good", "band_name": "Good", "min_score": 65, "max_score": 84.99},
            {"band_key": "average", "band_name": "Average", "min_score": 45, "max_score": 64.99},
            {"band_key": "needs_review", "band_name": "Needs Review", "min_score": 20, "max_score": 44.99},
            {"band_key": "disabled", "band_name": "Disabled", "min_score": 0, "max_score": 19.99, "bookable_allowed": False},
        ],
    },
]
