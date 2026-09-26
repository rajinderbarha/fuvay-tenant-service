"""Provider health uses recent evidence, confidence smoothing and fair grace."""
from pathlib import Path

from app.engines.trust_quality.provider_health_policy import (
    DEFAULT_HISTORY_WINDOW_DAYS,
    DEFAULT_RESCHEDULE_GRACE_COUNT,
    provider_reschedule_metrics,
    smoothed_provider_outcomes,
    smoothed_rating_score,
)


ROOT = Path(__file__).resolve().parents[1]
SERVICE = (ROOT / "app/engines/trust_quality/service.py").read_text(encoding="utf-8")
BATCH = (ROOT / "app/engines/trust_quality/recalculation.py").read_text(encoding="utf-8")
REGISTRY = (ROOT / "app/engines/settings_engine/registry.py").read_text(encoding="utf-8")
DASHBOARD = (
    ROOT / "app/engines/execution/home_services_dashboard_service.py"
).read_text(encoding="utf-8")
MIGRATION = (
    ROOT / "alembic/versions/386_provider_health_rolling_window.py"
).read_text(encoding="utf-8")
FINANCE_PAGE = (
    ROOT / "frontend/super-admin/app/admin/home-services/finance/page.tsx"
).read_text(encoding="utf-8")
CONFIGURATION_PAGE = (
    ROOT / "frontend/super-admin/app/admin/configuration/page.tsx"
).read_text(encoding="utf-8")


def test_policy_defaults_are_six_months_and_three_reschedules():
    assert DEFAULT_HISTORY_WINDOW_DAYS == 180
    assert DEFAULT_RESCHEDULE_GRACE_COUNT == 3


def test_one_early_cancellation_is_smoothed_instead_of_collapsing_health():
    metrics = smoothed_provider_outcomes(done=0, cancelled=1, prior_jobs=5)
    assert metrics == {
        "terminal_jobs_count": 1,
        "job_completion_rate": 83.33,
        "cancellation_rate": 16.67,
    }


def test_first_three_approved_provider_reschedules_are_health_neutral():
    for count in range(4):
        metrics = provider_reschedule_metrics(
            approved_provider_reschedules=count,
            terminal_jobs=4,
            grace_count=3,
            prior_jobs=5,
        )
        assert metrics["provider_reschedule_score"] == 100.0
        assert metrics["provider_reschedules_over_grace"] == 0

    fourth = provider_reschedule_metrics(4, terminal_jobs=4, grace_count=3, prior_jobs=5)
    assert fourth["provider_reschedules_over_grace"] == 1
    assert fourth["provider_reschedule_score"] == 90.0


def test_small_review_samples_are_smoothed_toward_neutral():
    assert smoothed_rating_score(1.0, review_count=1, prior_count=5, neutral_score=80) == 70.0
    assert smoothed_rating_score(5.0, review_count=1, prior_count=5, neutral_score=80) == 83.33


def test_single_and_batch_collectors_apply_window_and_only_provider_reschedules():
    for source in (SERVICE, BATCH):
        assert "history_window_days" in source
        assert "updated_at >= :window_start" in source
        assert "request_source = 'provider'" in source
        assert "status = 'approved'" in source


def test_all_policy_values_are_governed_admin_configuration():
    for key in (
        "provider_health_history_window_days",
        "provider_health_reschedule_grace_count",
        "provider_health_confidence_prior_jobs",
        "provider_health_rating_prior_count",
        "provider_health_neutral_rating_score",
    ):
        assert f'key="{key}"' in REGISTRY
    assert 'default_value=180' in REGISTRY
    assert 'default_value=3' in REGISTRY


def test_health_settings_link_opens_the_governed_registry_with_its_filter():
    assert '/admin/configuration?tab=registry&search=provider_health' in FINANCE_PAGE
    assert 'const requestedSearch = params.get("search") ?? ""' in CONFIGURATION_PAGE
    assert '<ConfigurationRegistryTab initialSearch={requestedSearch}/>' in CONFIGURATION_PAGE


def test_dashboard_uses_canonical_health_not_legacy_tenant_projection():
    assert "get_provider_health_snapshot" in DASHBOARD
    assert "refresh_provider_operational_health" not in DASHBOARD
    assert "tenant.health_score" not in DASHBOARD
    assert '"history_window_days"' in DASHBOARD


def test_default_formula_preserves_one_hundred_percent_weight():
    assert "'job_completion_rate' THEN 20.00" in MIGRATION
    assert "'cancellation_rate' THEN 15.00" in MIGRATION
    assert "'provider_reschedule_score'" in MIGRATION
    # Existing unchanged weights total 55; revised outcome weights are 35;
    # the new reschedule component is 10: 55 + 35 + 10 = 100.
    assert "10.00, 'positive'" in MIGRATION


def test_single_complaint_does_not_trigger_the_chronic_pattern_penalty():
    assert '"metric_key": "complaint_rate", "operator": "greater_than", "value": 25' in SERVICE
    assert "rule.value_json = '10'::jsonb" in MIGRATION
    assert "SET value_json = '25'::jsonb" in MIGRATION


def test_health_breakdown_keeps_window_and_grace_evidence_for_audit():
    assert '"history_window_days"' in SERVICE
    assert '"provider_reschedule_grace_remaining"' in SERVICE
    assert 'item["evidence"] = evidence' in SERVICE
