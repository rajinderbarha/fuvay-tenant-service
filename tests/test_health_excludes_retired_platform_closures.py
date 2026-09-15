"""Platform-closed jobs must not count as a provider's cancellations.

The retired provider-assignment sweep cancelled unassigned jobs itself with
"Closed because no alternative provider was available...". On staging, two
providers whose only history was those closures scored 18.18, landed in the
non-bookable "blocked" band, and every Instagram booking in pincode 140412
answered "No service is currently available".
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.engines.trust_quality import recalculation
from app.engines.trust_quality.service import (
    _COUNTED_JOB_OUTCOME_SQL,
    TrustQualityService,
    calc_health_score,
)


def _recording_db():
    result = MagicMock()
    result.all.return_value = []
    result.mappings.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


def _job_outcome_sql(db) -> str:
    statements = [str(call.args[0]) for call in db.execute.await_args_list]
    return next(sql for sql in statements if "FROM service_jobs" in sql)


async def test_batch_metrics_exclude_retired_platform_closures():
    db = _recording_db()
    await recalculation.gather_metrics_bulk(db, "tenant_provider", [uuid.uuid4()])
    assert _COUNTED_JOB_OUTCOME_SQL in _job_outcome_sql(db)


async def test_single_target_metrics_exclude_retired_platform_closures():
    db = _recording_db()
    await TrustQualityService(db).gather_live_metrics("tenant_provider", uuid.uuid4())
    assert _COUNTED_JOB_OUTCOME_SQL in _job_outcome_sql(db)


def test_predicate_targets_only_the_retired_closure_reason():
    assert "failure_reason" in _COUNTED_JOB_OUTCOME_SQL
    assert "NOT LIKE 'Closed because no alternative provider%'" in _COUNTED_JOB_OUTCOME_SQL


def _provider_formula():
    """Shape of migration 350's provider_business_health_default formula."""
    formula = SimpleNamespace(base_score=100, min_score=0, max_score=100)
    components = [
        SimpleNamespace(metric_key=key, weight_percent=weight, direction=direction,
                        min_value=0, max_value=100, is_required=False)
        for key, weight, direction in (
            ("job_completion_rate", 25, "positive"),
            ("rating_score", 20, "positive"),
            ("complaint_dispute_score", 15, "negative"),
            ("cancellation_rate", 20, "negative"),
            ("response_sla_score", 10, "positive"),
            ("document_verification_score", 10, "positive"),
        )
    ]
    bands = [
        SimpleNamespace(band_key=key, min_score=lo, max_score=hi, recommended_action=None)
        for key, lo, hi in (
            ("platinum", 90, 100), ("gold", 75, 89.99), ("silver", 60, 74.99),
            ("watchlist", 50, 59.99), ("at_risk", 20, 49.99), ("blocked", 0, 19.99),
        )
    ]
    return formula, components, bands


def test_counting_platform_closures_reproduces_the_blocked_score():
    formula, components, bands = _provider_formula()
    metrics = {"job_completion_rate": 0.0, "cancellation_rate": 100.0,
               "document_verification_score": 100.0}
    result = calc_health_score(formula, components, [], [], bands, metrics)
    assert result["score"] == 18.18
    assert result["band_key"] == "blocked"


def test_provider_with_only_platform_closures_is_unassessed():
    formula, components, bands = _provider_formula()
    # With those jobs excluded there is no terminal job, so no rate metrics.
    metrics = {"completed_jobs_count": 0, "review_count": 0,
               "document_verification_score": 100.0}
    result = calc_health_score(formula, components, [], [], bands, metrics)
    assert result["insufficient_data"] is True
    assert result["band_key"] is None
