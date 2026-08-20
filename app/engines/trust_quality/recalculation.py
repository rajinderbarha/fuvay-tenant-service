"""Batched, set-based execution of a Trust & Quality recalculation job.

The per-target path in `TrustQualityService` is correct but is shaped for ONE
target: it issues four metric queries, re-reads a rule's criteria, and commits,
every time it is called. Sweeping the platform through it costs a handful of
round trips and a commit *per provider per engine* — at a million providers that
is tens of millions of round trips inside a single HTTP request, which no
gateway will hold open and no connection pool will survive.

This module runs the same rules with the same semantics, but organised the other
way round: configuration is loaded ONCE per job, targets are walked in keyset
batches so memory stays flat however many rows exist, metrics for a whole batch
are gathered in a fixed number of set-based queries, and the batch commits once.
Cost per batch is a constant ~8 queries instead of ~2000.

Two deliberate differences from the single-target path, both required at scale:

* No per-target audit row. A platform sweep would otherwise write one
  `trust_quality_audit_logs` row per target per engine — three million rows for
  one button press, burying the human decisions the audit trail exists to record.
  The job row itself is the audit record for a sweep; individual admin actions
  (manual award, revoke, rule activation) still write their own entries.
* Progress is committed as it goes, so a job that dies halfway leaves a truthful
  processed count behind rather than silently rolling back.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.trust_quality.models import (
    BadgeAssignment, BadgeDefinition, BadgeRule, BadgeRuleCriteria, BadgeRuleRemovalCriteria,
    HealthBandRule, HealthBonusRule, HealthFormula, HealthFormulaComponent,
    HealthPenaltyRule, HealthScore, RiskRule, RiskScore,
)
from app.engines.trust_quality.service import (
    _JOB_CANCELLED_STATUSES, _JOB_DONE_STATUSES, _TARGET_SOURCE_SQL,
    FIXED_BADGE_BY_KEY, FIXED_BADGE_KEYS, _evaluate_operator, calc_health_score,
)

log = structlog.get_logger("trust_quality.recalculation")

# Targets per batch. Large enough that fixed per-batch query cost is amortised,
# small enough that one batch's metrics and ORM objects stay comfortably in
# memory and the transaction it commits stays short.
BATCH_SIZE = 500


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Preloaded configuration ──────────────────────────────────────────────────

@dataclass
class BadgeRuleCfg:
    rule: BadgeRule
    criteria: list[BadgeRuleCriteria]
    removal: list[BadgeRuleRemovalCriteria]


@dataclass
class HealthFormulaCfg:
    formula: HealthFormula
    components: list[HealthFormulaComponent]
    penalties: list[HealthPenaltyRule]
    bonuses: list[HealthBonusRule]
    bands: list[HealthBandRule]


@dataclass
class Ruleset:
    """Every rule a job needs, read once, grouped by the target_type it applies to."""
    badge_rules: dict[str, list[BadgeRuleCfg]] = field(default_factory=dict)
    health_formulas: dict[str, list[HealthFormulaCfg]] = field(default_factory=dict)
    risk_rules: dict[str, list[RiskRule]] = field(default_factory=dict)

    def target_types(self) -> list[str]:
        """Every target_type any loaded rule touches, in a stable order."""
        seen = list(self.badge_rules) + list(self.health_formulas) + list(self.risk_rules)
        return sorted(set(seen))


async def load_ruleset(db: AsyncSession, job_type: str) -> Ruleset:
    """Read the active rules for this job once, up front.

    Criteria/components are fetched with one query per kind for ALL rules and
    grouped in Python, rather than one query per rule, so adding rules does not
    add round trips.
    """
    kinds = ("badges", "health") if job_type == "all" else (job_type,)
    rs = Ruleset()

    if "badges" in kinds:
        rows = (await db.execute(
            select(BadgeRule, BadgeDefinition)
            .join(BadgeDefinition, BadgeDefinition.id == BadgeRule.badge_id)
            .where(
                BadgeRule.status == "active",
                BadgeRule.auto_award.is_(True),
                BadgeDefinition.badge_key.in_(FIXED_BADGE_KEYS),
            )
        )).all()
        rules = [
            r for r, b in rows
            if FIXED_BADGE_BY_KEY[b.badge_key]["target_type"] == r.target_type
        ]
        rule_ids = [r.id for r in rules]
        crit: dict[uuid.UUID, list[BadgeRuleCriteria]] = {}
        rem: dict[uuid.UUID, list[BadgeRuleRemovalCriteria]] = {}
        if rule_ids:
            for c in (await db.execute(select(BadgeRuleCriteria).where(
                    BadgeRuleCriteria.badge_rule_id.in_(rule_ids)))).scalars().all():
                crit.setdefault(c.badge_rule_id, []).append(c)
            for c in (await db.execute(select(BadgeRuleRemovalCriteria).where(
                    BadgeRuleRemovalCriteria.badge_rule_id.in_(rule_ids)))).scalars().all():
                rem.setdefault(c.badge_rule_id, []).append(c)
        for r in rules:
            rs.badge_rules.setdefault(r.target_type, []).append(
                BadgeRuleCfg(r, crit.get(r.id, []), rem.get(r.id, [])))

    if "health" in kinds:
        formulas = list((await db.execute(
            select(HealthFormula).where(HealthFormula.status == "active"))).scalars().all())
        fids = [f.id for f in formulas]
        comps: dict[uuid.UUID, list] = {}
        pens: dict[uuid.UUID, list] = {}
        bons: dict[uuid.UUID, list] = {}
        bands: dict[uuid.UUID, list] = {}
        if fids:
            for model, bucket in (
                (HealthFormulaComponent, comps), (HealthPenaltyRule, pens),
                (HealthBonusRule, bons), (HealthBandRule, bands),
            ):
                for row in (await db.execute(
                        select(model).where(model.formula_id.in_(fids)))).scalars().all():
                    bucket.setdefault(row.formula_id, []).append(row)
        for f in formulas:
            rs.health_formulas.setdefault(f.target_type, []).append(HealthFormulaCfg(
                f, comps.get(f.id, []), pens.get(f.id, []),
                bons.get(f.id, []), bands.get(f.id, [])))

    if "risk" in kinds:
        for r in (await db.execute(
                select(RiskRule).where(RiskRule.status == "active"))).scalars().all():
            rs.risk_rules.setdefault(r.target_type, []).append(r)

    return rs


# ── Target enumeration (keyset, never the whole table in memory) ─────────────

async def count_targets(db: AsyncSession, target_type: str, scope_type: str,
                        scope_id: uuid.UUID | None) -> int:
    """How many rows this target_type covers, for the job's total_count."""
    sql = _TARGET_SOURCE_SQL.get(target_type)
    if not sql:
        return 0
    inner, params = _scoped_sql(sql, target_type, scope_type, scope_id)
    return int((await db.execute(
        text(f"SELECT count(*) FROM ({inner}) s"), params)).scalar_one())


def _scoped_sql(sql: str, target_type: str, scope_type: str,
                scope_id: uuid.UUID | None) -> tuple[str, dict]:
    params: dict = {}
    if scope_type == "tenant" and scope_id is not None:
        col = "id" if target_type in ("tenant", "tenant_provider") else "tenant_id"
        sql += f" AND {col} = CAST(:scope_id AS uuid)"
        params["scope_id"] = str(scope_id)
    return sql, params


async def enumerate_batch(db: AsyncSession, target_type: str, scope_type: str,
                          scope_id: uuid.UUID | None, after_id: uuid.UUID | None,
                          limit: int = BATCH_SIZE) -> list[uuid.UUID]:
    """The next `limit` target ids after `after_id`, ordered by id.

    Keyset rather than OFFSET: OFFSET re-scans everything it skips, so the last
    page of a million-row sweep would cost a million rows to reach. Ordering by
    the primary key also makes the walk stable while rows are being inserted
    underneath it.
    """
    sql = _TARGET_SOURCE_SQL.get(target_type)
    if not sql:
        return []
    sql, params = _scoped_sql(sql, target_type, scope_type, scope_id)
    if after_id is not None:
        sql += " AND id > CAST(:after_id AS uuid)"
        params["after_id"] = str(after_id)
    sql += f" ORDER BY id LIMIT {int(limit)}"
    rows = (await db.execute(text(sql), params)).scalars().all()
    return [r if isinstance(r, uuid.UUID) else uuid.UUID(str(r)) for r in rows]


# ── Set-based metric gathering ───────────────────────────────────────────────

_METRIC_COLUMNS = {
    "tenant":           ("tenant_id", "tenant_id", "tenant_id"),
    "tenant_provider":  ("tenant_id", "tenant_id", "tenant_id"),
    "staff":            ("assigned_staff_id", "staff_member_id", None),
    "tenant_staff":     ("assigned_staff_id", "staff_member_id", None),
    "technician":       ("assigned_staff_id", "staff_member_id", None),
    "customer_account": ("customer_id", "customer_id", "customer_id"),
}


async def gather_metrics_bulk(db: AsyncSession, target_type: str,
                              ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Live metrics for a whole batch, in a fixed number of queries.

    Semantics are identical to `TrustQualityService._gather_metrics` — including
    which metrics are omitted rather than defaulted, because a criterion reading
    a missing metric evaluates false, which correctly withholds a badge instead
    of awarding one off a fabricated number. The only change is that the whole
    batch is aggregated in one GROUP BY per source table.
    """
    cols = _METRIC_COLUMNS.get(target_type)
    if not cols or not ids:
        return {t: {} for t in ids}
    job_col, review_col, complaint_col = cols
    str_ids = [str(i) for i in ids]
    out: dict[uuid.UUID, dict] = {t: {} for t in ids}
    terminal_by_target: dict[uuid.UUID, int] = {}

    def _key(v) -> uuid.UUID | None:
        if v is None:
            return None
        return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))

    # 1. Job outcomes — one grouped scan for the batch.
    done_list = ", ".join(f"'{s}'" for s in _JOB_DONE_STATUSES)
    cancel_list = ", ".join(f"'{s}'" for s in _JOB_CANCELLED_STATUSES)
    rows = (await db.execute(text(
        f"SELECT {job_col} AS target_key, "
        f"       count(*) FILTER (WHERE status IN ({done_list})) AS done, "
        f"       count(*) FILTER (WHERE status IN ({cancel_list})) AS cancelled "
        f"FROM service_jobs WHERE {job_col} = ANY(CAST(:ids AS uuid[])) "
        f"GROUP BY {job_col}"), {"ids": str_ids})).mappings().all()
    for row in rows:
        t = _key(row["target_key"])
        if t not in out:
            continue
        done, cancelled = int(row["done"] or 0), int(row["cancelled"] or 0)
        terminal = done + cancelled
        terminal_by_target[t] = terminal
        out[t]["completed_jobs_count"] = done
        if terminal:
            out[t]["job_completion_rate"] = round(done * 100.0 / terminal, 2)
            out[t]["cancellation_rate"] = round(cancelled * 100.0 / terminal, 2)
    # A target with no job rows at all still reports a real zero.
    for t in ids:
        out[t].setdefault("completed_jobs_count", 0)

    # 2. Reviews.
    rows = (await db.execute(text(
        f"SELECT {review_col} AS target_key, avg(overall_rating) AS avg_rating, count(*) AS n "
        f"FROM customer_reviews "
        f"WHERE {review_col} = ANY(CAST(:ids AS uuid[])) AND hidden_at IS NULL "
        f"GROUP BY {review_col}"), {"ids": str_ids})).mappings().all()
    seen_reviews = set()
    for row in rows:
        t = _key(row["target_key"])
        if t not in out:
            continue
        seen_reviews.add(t)
        out[t]["review_count"] = int(row["n"] or 0)
        if row["avg_rating"] is not None:
            out[t]["average_rating"] = round(float(row["avg_rating"]), 2)
            # Formulas score out of 100, ratings are out of 5.
            out[t]["rating_score"] = round(float(row["avg_rating"]) * 20.0, 2)
    for t in ids:
        if t not in seen_reviews:
            out[t]["review_count"] = 0

    # 3. Complaints. Provider complaints are directly tenant-scoped. Staff
    # complaints are attributed through the job assignment so both the
    # single-target and batch paths use the same operational source.
    if complaint_col:
        rows = (await db.execute(text(
            f"SELECT {complaint_col} AS target_key, count(*) AS n, "
            f"       count(*) FILTER (WHERE sla_status = 'breached') AS breached "
            f"FROM customer_complaints "
            f"WHERE {complaint_col} = ANY(CAST(:ids AS uuid[])) "
            f"GROUP BY {complaint_col}"), {"ids": str_ids})).mappings().all()
        for row in rows:
            t = _key(row["target_key"])
            if t not in out:
                continue
            n, breached = int(row["n"] or 0), int(row["breached"] or 0)
            terminal = terminal_by_target.get(t, 0)
            if terminal:
                rate = round(n * 100.0 / terminal, 2)
                out[t]["complaint_rate"] = rate
                out[t]["complaint_dispute_score"] = rate
            if n:
                # Share of complaints answered inside the SLA.
                sla = round((n - breached) * 100.0 / n, 2)
                out[t]["response_sla_score"] = sla
                out[t]["sla_success_rate"] = sla
    elif target_type in ("staff", "technician", "tenant_staff"):
        rows = (await db.execute(text(
            "SELECT sj.assigned_staff_id AS target_key, count(*) AS n, "
            "       count(*) FILTER (WHERE cc.sla_status = 'breached') AS breached "
            "FROM customer_complaints cc "
            "JOIN service_jobs sj ON sj.id = cc.job_id "
            "WHERE sj.assigned_staff_id = ANY(CAST(:ids AS uuid[])) "
            "GROUP BY sj.assigned_staff_id"), {"ids": str_ids})).mappings().all()
        for row in rows:
            t = _key(row["target_key"])
            if t not in out:
                continue
            n, breached = int(row["n"] or 0), int(row["breached"] or 0)
            terminal = terminal_by_target.get(t, 0)
            if terminal:
                rate = round(n * 100.0 / terminal, 2)
                out[t]["complaint_rate"] = rate
                out[t]["complaint_dispute_score"] = rate
            if n:
                sla = round((n - breached) * 100.0 / n, 2)
                out[t]["response_sla_score"] = sla
                out[t]["sla_success_rate"] = sla

    # 4. Platform verification and target-specific operational signals.
    if target_type in ("tenant", "tenant_provider"):
        rows = (await db.execute(text(
            "SELECT id AS target_key, status, verification_status, business_name, "
            "       email, phone, address_line1, city, state, zipcode, business_type "
            "FROM tenants "
            "WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": str_ids})).mappings().all()
        for row in rows:
            t = _key(row["target_key"])
            if t not in out:
                continue
            verified = row["verification_status"] == "verified"
            out[t]["document_verified"] = verified
            out[t]["owner_verified"] = verified
            out[t]["document_verification_score"] = 100.0 if verified else 0.0
            profile_fields = (
                "business_name", "email", "phone", "address_line1",
                "city", "state", "zipcode", "business_type",
            )
            out[t]["profile_completion_percent"] = round(
                sum(bool(row[key]) for key in profile_fields) * 100.0 / len(profile_fields), 2
            )
            out[t]["tenant_status"] = row["status"]

        # Latest Home Services finance readiness per provider. DISTINCT ON
        # keeps this one set-based query even if legacy tenants have revisions.
        rows = (await db.execute(text(
            "SELECT DISTINCT ON (tenant_id) tenant_id AS target_key, credit_balance, "
            "       security_deposit_paid, security_deposit_amount "
            "FROM tenant_billing "
            "WHERE tenant_id = ANY(CAST(:ids AS uuid[])) "
            "  AND vertical_key = 'home_services' "
            "ORDER BY tenant_id, updated_at DESC NULLS LAST"), {"ids": str_ids})).mappings().all()
        for row in rows:
            t = _key(row["target_key"])
            if t not in out:
                continue
            deposit_required = float(row["security_deposit_amount"] or 0) > 0
            deposit_ready = not deposit_required or bool(row["security_deposit_paid"])
            out[t]["security_deposit_score"] = 100.0 if deposit_ready else 0.0
            out[t]["security_deposit_missing"] = not deposit_ready
            credit_ready = float(row["credit_balance"] or 0) > 0
            out[t]["usage_credit_score"] = 100.0 if credit_ready else 0.0
            out[t]["usage_credit_depleted"] = not credit_ready

        rows = (await db.execute(text(
            "SELECT tenant_id AS target_key, count(*) AS active_staff "
            "FROM users WHERE tenant_id = ANY(CAST(:ids AS uuid[])) "
            "  AND role = 'staff' AND is_active IS TRUE AND deleted_at IS NULL "
            "GROUP BY tenant_id"), {"ids": str_ids})).mappings().all()
        active_staff_by_target = {
            _key(row["target_key"]): int(row["active_staff"] or 0) for row in rows
        }
        for t in ids:
            out[t]["staff_availability_score"] = (
                100.0 if active_staff_by_target.get(t, 0) > 0 else 0.0
            )

        rows = (await db.execute(text(
            "SELECT tenant_id AS target_key, "
            "       avg(EXTRACT(EPOCH FROM (provider_responded_at - created_at)) / 60.0) "
            "           AS response_minutes "
            "FROM customer_complaints "
            "WHERE tenant_id = ANY(CAST(:ids AS uuid[])) "
            "  AND provider_responded_at IS NOT NULL "
            "GROUP BY tenant_id"), {"ids": str_ids})).mappings().all()
        for row in rows:
            t = _key(row["target_key"])
            if t in out and row["response_minutes"] is not None:
                out[t]["response_time_minutes"] = round(float(row["response_minutes"]), 2)
    elif target_type in ("staff", "technician", "tenant_staff"):
        rows = (await db.execute(text(
            "SELECT id AS target_key, is_verified FROM users "
            "WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": str_ids})).mappings().all()
        for row in rows:
            t = _key(row["target_key"])
            if t not in out:
                continue
            verified = bool(row["is_verified"])
            out[t]["document_verified"] = verified
            out[t]["document_verification_score"] = 100.0 if verified else 0.0

        rows = (await db.execute(text(
            "SELECT staff_member_id AS target_key, "
            "       count(*) FILTER (WHERE punctuality_rating >= 4) AS on_time, "
            "       count(punctuality_rating) AS measured "
            "FROM customer_reviews "
            "WHERE staff_member_id = ANY(CAST(:ids AS uuid[])) AND hidden_at IS NULL "
            "GROUP BY staff_member_id"), {"ids": str_ids})).mappings().all()
        for row in rows:
            t = _key(row["target_key"])
            measured = int(row["measured"] or 0)
            if t in out and measured:
                out[t]["on_time_arrival_rate"] = round(
                    int(row["on_time"] or 0) * 100.0 / measured, 2
                )

    return out


# ── Per-engine batch application ─────────────────────────────────────────────

async def apply_badges_batch(db: AsyncSession, cfgs: list[BadgeRuleCfg], target_type: str,
                             metrics_by_target: dict[uuid.UUID, dict]) -> int:
    """Award/withdraw badges for a batch. Two queries regardless of batch size."""
    if not cfgs or not metrics_by_target:
        return 0
    ids = list(metrics_by_target)
    badge_ids = [c.rule.badge_id for c in cfgs]

    existing_rows = (await db.execute(
        select(BadgeAssignment).where(
            BadgeAssignment.target_type == target_type,
            BadgeAssignment.target_id.in_(ids),
            BadgeAssignment.badge_id.in_(badge_ids),
            BadgeAssignment.status == "active",
        )
    )).scalars().all()
    existing: dict[tuple[uuid.UUID, uuid.UUID], BadgeAssignment] = {}
    for a in existing_rows:
        existing.setdefault((a.target_id, a.badge_id), a)

    changes = 0
    now = _now()
    for target_id, metrics in metrics_by_target.items():
        for cfg in cfgs:
            r = cfg.rule
            eligible = bool(cfg.criteria) and all(
                _evaluate_operator(metrics.get(c.metric_key), c.operator, c.value_json)
                for c in cfg.criteria if c.is_required)
            would_remove = any(
                _evaluate_operator(metrics.get(c.metric_key), c.operator, c.value_json)
                for c in cfg.removal)
            held = existing.get((target_id, r.badge_id))

            if eligible and not would_remove and not held:
                db.add(BadgeAssignment(
                    badge_id=r.badge_id, badge_rule_id=r.id, target_type=target_type,
                    target_id=target_id, status="active", award_source="auto_rule",
                    earned_at=now,
                    expires_at=now + timedelta(days=r.expiry_days)
                    if r.expiry_enabled and r.expiry_days else None,
                    created_at=now, updated_at=now,
                ))
                changes += 1
            elif held and (would_remove or not eligible):
                held.status = "revoked" if would_remove else "expired"
                held.revoked_at = now
                held.revoked_reason = ("auto: removal criteria matched" if would_remove
                                       else "auto: no longer eligible")
                held.updated_at = now
                changes += 1
    return changes


async def apply_health_batch(db: AsyncSession, cfg: HealthFormulaCfg, target_type: str,
                             metrics_by_target: dict[uuid.UUID, dict]) -> int:
    """Score a batch against one formula. One query regardless of batch size."""
    if not metrics_by_target:
        return 0
    ids = list(metrics_by_target)
    existing = {
        s.target_id: s for s in (await db.execute(
            select(HealthScore).where(
                HealthScore.target_type == target_type,
                HealthScore.target_id.in_(ids),
                HealthScore.formula_id == cfg.formula.id,
            )
        )).scalars().all()
    }
    now = _now()
    for target_id, metrics in metrics_by_target.items():
        result = calc_health_score(cfg.formula, cfg.components, cfg.penalties,
                                   cfg.bonuses, cfg.bands, metrics)
        row = existing.get(target_id)
        if row is None:
            row = HealthScore(
                target_type=target_type, target_id=target_id, formula_id=cfg.formula.id,
                score=result["score"], created_at=now, calculated_at=now, updated_at=now)
            db.add(row)
        row.score = result["score"]
        row.band_key = result["band_key"]
        row.component_breakdown_json = result["component_breakdown"]
        row.penalties_json = result["penalties_applied"]
        row.bonuses_json = result["bonuses_applied"]
        row.recommended_actions_json = result["recommended_actions"]
        row.calculated_at = now
        row.updated_at = now
    return len(metrics_by_target)


_RISK_LEVEL_RANK = {lvl: i for i, lvl in enumerate(
    ["normal", "watchlist", "high_risk", "finance_blocked", "quality_blocked", "suspended"])}


async def apply_risk_batch(db: AsyncSession, rules: list[RiskRule], target_type: str,
                           metrics_by_target: dict[uuid.UUID, dict]) -> int:
    """Risk-score a batch. One query regardless of batch size."""
    if not metrics_by_target:
        return 0
    ids = list(metrics_by_target)
    existing = {
        s.target_id: s for s in (await db.execute(
            select(RiskScore).where(
                RiskScore.target_type == target_type,
                RiskScore.target_id.in_(ids),
            )
        )).scalars().all()
    }
    now = _now()
    for target_id, metrics in metrics_by_target.items():
        reasons: list[str] = []
        actions: list = []
        score_delta = 0.0
        risk_level = "normal"
        for r in rules:
            cond = r.condition_json or {}
            actual = metrics.get(cond.get("metric_key"))
            if _evaluate_operator(actual, cond.get("operator"), cond.get("value")):
                score_delta += float(r.risk_score_delta)
                reasons.append(r.name)
                actions.extend(r.recommended_actions_json or [])
                if _RISK_LEVEL_RANK.get(r.risk_level, 0) > _RISK_LEVEL_RANK.get(risk_level, 0):
                    risk_level = r.risk_level

        row = existing.get(target_id)
        if row is None:
            row = RiskScore(target_type=target_type, target_id=target_id,
                            risk_score=score_delta, risk_level=risk_level,
                            created_at=now, calculated_at=now, updated_at=now)
            db.add(row)
        row.risk_score = score_delta
        row.risk_level = risk_level
        row.reasons_json = reasons
        row.recommended_actions_json = actions
        row.bookable_impact = risk_level in ("high_risk", "quality_blocked", "suspended")
        row.finance_impact = risk_level in ("finance_blocked", "suspended")
        row.calculated_at = now
        row.updated_at = now
    return len(metrics_by_target)


# ── The job runner ───────────────────────────────────────────────────────────

async def estimate_total(db: AsyncSession, ruleset: Ruleset, scope_type: str,
                         scope_id: uuid.UUID | None) -> int:
    """Total units of work, so progress can be reported as a fraction.

    A unit is one (engine, target) pair, which is what `processed` counts — so a
    provider covered by badges, health and risk contributes three.
    """
    total = 0
    counts: dict[str, int] = {}
    for tt in ruleset.target_types():
        counts[tt] = await count_targets(db, tt, scope_type, scope_id)
    for tt, cfgs in ruleset.badge_rules.items():
        if cfgs:
            total += counts.get(tt, 0)
    for tt, fcfgs in ruleset.health_formulas.items():
        total += counts.get(tt, 0) * len(fcfgs)
    for tt, rules in ruleset.risk_rules.items():
        if rules:
            total += counts.get(tt, 0)
    return total
