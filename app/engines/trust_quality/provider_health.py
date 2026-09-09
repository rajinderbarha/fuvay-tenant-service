"""Canonical provider health snapshots for runtime decisions.

Trust & Quality owns the score. Consumers may choose their own freshness
window, but must never fall back to ``tenants.health_score`` because that
legacy projection cannot distinguish an earned result from an old default.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.trust_quality.models import HealthBandRule, HealthFormula, HealthScore


UNASSESSED_PROVIDER_HEALTH_SCORE = 65.0


async def get_provider_health_snapshot(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    max_age_days: int = 30,
) -> dict:
    """Return the newest active-formula provider score, or a neutral prior.

    Missing, stale and unbanded scores never cause a financial penalty. The
    caller receives a reason so the decision can be persisted and audited.
    """
    row = (await db.execute(
        select(
            HealthScore.id.label("health_score_id"),
            HealthScore.formula_id,
            HealthFormula.formula_key,
            HealthFormula.version.label("formula_version"),
            HealthScore.score,
            HealthScore.band_key,
            HealthScore.calculated_at,
            HealthBandRule.id.label("health_band_rule_id"),
            HealthBandRule.bookable_allowed,
        )
        .join(HealthFormula, HealthFormula.id == HealthScore.formula_id)
        .outerjoin(HealthBandRule, and_(
            HealthBandRule.formula_id == HealthScore.formula_id,
            HealthBandRule.band_key == HealthScore.band_key,
        ))
        .where(
            HealthScore.target_type == "tenant",
            HealthScore.target_id == tenant_id,
            HealthFormula.status == "active",
        )
        .order_by(HealthScore.calculated_at.desc())
        .limit(1)
    )).first()

    neutral = {
        "score": UNASSESSED_PROVIDER_HEALTH_SCORE,
        "band_key": None,
        "source": "unassessed_default",
        "reason": "missing_health_score",
        "health_score_id": None,
        "formula_id": None,
        "formula_key": None,
        "formula_version": None,
        "calculated_at": None,
        "bookable_allowed": True,
    }
    if row is None:
        return neutral

    calculated_at = row.calculated_at
    if calculated_at is None:
        return {**neutral, "reason": "health_score_missing_timestamp"}
    calculated_utc = (
        calculated_at.replace(tzinfo=timezone.utc)
        if calculated_at.tzinfo is None else calculated_at.astimezone(timezone.utc)
    )
    if datetime.now(timezone.utc) - calculated_utc > timedelta(days=max_age_days):
        return {
            **neutral,
            "reason": "stale_health_score",
            "health_score_id": str(row.health_score_id),
            "formula_id": str(row.formula_id),
            "formula_key": row.formula_key,
            "formula_version": row.formula_version,
            "calculated_at": calculated_utc.isoformat(),
        }
    if row.band_key is None:
        return {
            **neutral,
            "reason": "unbanded_health_score",
            "health_score_id": str(row.health_score_id),
            "formula_id": str(row.formula_id),
            "formula_key": row.formula_key,
            "formula_version": row.formula_version,
            "calculated_at": calculated_utc.isoformat(),
        }
    if row.health_band_rule_id is None:
        return {
            **neutral,
            "reason": "missing_health_band_rule",
            "health_score_id": str(row.health_score_id),
            "formula_id": str(row.formula_id),
            "formula_key": row.formula_key,
            "formula_version": row.formula_version,
            "calculated_at": calculated_utc.isoformat(),
        }

    return {
        "score": float(row.score),
        "band_key": row.band_key,
        "source": "canonical",
        "reason": None,
        "health_score_id": str(row.health_score_id),
        "formula_id": str(row.formula_id),
        "formula_key": row.formula_key,
        "formula_version": row.formula_version,
        "calculated_at": calculated_utc.isoformat(),
        "bookable_allowed": bool(row.bookable_allowed),
    }
