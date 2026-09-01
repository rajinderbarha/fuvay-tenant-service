"""Regression coverage for Trust & Quality health formula semantics."""

from types import SimpleNamespace

from app.engines.trust_quality.service import calc_health_score


def _formula():
    return SimpleNamespace(base_score=0, min_score=0, max_score=100)


def _component(key: str, weight: float, *, direction: str = "positive", required: bool = True):
    return SimpleNamespace(
        metric_key=key,
        weight_percent=weight,
        direction=direction,
        min_value=0,
        max_value=100,
        is_required=required,
    )


def _bands():
    return [
        SimpleNamespace(min_score=0, max_score=49.99, band_key="low", recommended_action=None),
        SimpleNamespace(min_score=50, max_score=100, band_key="healthy", recommended_action=None),
    ]


def test_missing_required_negative_metric_never_improves_score():
    result = calc_health_score(
        _formula(),
        [_component("completion", 50), _component("complaints", 50, direction="negative")],
        [], [], _bands(),
        {},
    )

    assert result["score"] == 0
    assert result["coverage_percent"] == 0
    assert result["band_key"] is None
    assert all(row["missing"] for row in result["component_breakdown"])


def test_complete_formula_normalizes_positive_and_negative_metrics():
    result = calc_health_score(
        _formula(),
        [_component("completion", 60), _component("complaints", 40, direction="negative")],
        [], [], _bands(),
        {"completion": 90, "complaints": 10},
    )

    assert result["score"] == 90
    assert result["coverage_percent"] == 100
    assert result["band_key"] == "healthy"


def test_insufficient_real_metric_coverage_remains_unassessed():
    result = calc_health_score(
        _formula(),
        [_component("known", 40), _component("unknown", 60)],
        [], [], _bands(),
        {"known": 100},
    )

    assert result["score"] == 40
    assert result["coverage_percent"] == 40
    assert result["band_key"] is None


def test_bulk_metric_path_contains_every_live_formula_signal():
    from app.engines.trust_quality import recalculation

    source = open(recalculation.__file__, encoding="utf-8").read()
    expected = {
        "profile_completion_percent",
        "usage_credit_score",
        "staff_availability_score",
        "response_time_minutes",
        "on_time_arrival_rate",
        "complaint_dispute_score",
        "document_verification_score",
        "job_completion_rate",
        "rating_score",
    }
    assert expected.issubset(set(source.split('"')))
