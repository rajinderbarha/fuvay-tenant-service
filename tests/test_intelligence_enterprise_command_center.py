"""Enterprise contracts for the Home Services intelligence command center."""
from pathlib import Path


ROOT = Path(__file__).parent.parent
SERVICE = (ROOT / "app/engines/analytics/intelligence_service.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "app/engines/analytics/intelligence_router.py").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend/super-admin/app/admin/intelligence/page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
MIGRATION = (ROOT / "alembic/versions/286_intelligence_command_center_scale_indexes.py").read_text(encoding="utf-8")
TIMESTAMP_MIGRATION = (ROOT / "alembic/versions/287_intelligence_risk_timestamp_contract.py").read_text(encoding="utf-8")


def test_risk_scoring_is_set_based_and_not_limited_to_first_100_providers():
    scoring = SERVICE[SERVICE.index("async def create_prediction_job"):SERVICE.index("async def get_prediction_job")]
    assert "ON CONFLICT (entity_type, entity_id)" in scoring
    assert "LIMIT 100" not in scoring
    assert "vertical = 'home_services'" in scoring


def test_current_risk_scores_are_unique_and_indexed_for_directories():
    assert "uq_intel_risk_current_entity" in MIGRATION
    assert "ix_intel_risk_level_score" in MIGRATION
    assert "ix_intel_anomaly_status_detected" in MIGRATION
    assert "ix_platform_audit_engine_created" in MIGRATION
    assert '"updated_at"' in TIMESTAMP_MIGRATION


def test_data_quality_checks_use_current_home_services_tables_and_real_queries():
    assert "FROM service_groups GROUP BY code" in SERVICE
    assert "FROM usage_credit_ledger" in SERVICE
    assert "FROM bookings" in SERVICE
    assert "stale_health_scores" not in SERVICE[SERVICE.index("DEFAULT_CHECKS"):SERVICE.index("RETIRED_CHECK_KEYS")]


def test_control_plane_writes_are_mirrored_to_append_only_audit():
    assert "record_platform_audit" in ROUTER
    assert 'engine_id="intelligence"' in ROUTER
    for action in ["intelligence.prediction.run", "intelligence.anomaly.scan", "intelligence.data_quality.run", "intelligence.model.activate"]:
        assert action in ROUTER


def test_all_high_volume_tabs_use_server_pagination_and_filters():
    for endpoint in ["getRiskEntities", "getAnomalies", "getModels", "getPredictionJobs", "getAiUsageLogs", "getAuditLogs", "getEventFailures"]:
        assert f"{endpoint}({{" in PAGE
    assert PAGE.count("<Pager") >= 8
    assert "useDebounced" in PAGE
    assert "page_size: PAGE_SIZE" in PAGE


def test_operator_lifecycle_actions_are_available_from_the_ui_client():
    for action in ["investigateAnomaly", "resolveAnomaly", "markAnomalyFalsePositive", "retryPredictionJob", "runDQCheck", "recomputeRisk", "evaluateModel"]:
        assert action in API
        assert action in PAGE


def test_overview_uses_backend_health_instead_of_hardcoded_operational_state():
    assert "s?.engine_health" in PAGE
    assert 'status: "operational"' not in PAGE
    assert "safeNum(s?.rag_queries) >= 0" not in PAGE


def test_event_pipeline_reads_real_analytics_events():
    event_section = SERVICE[SERVICE.index("async def get_event_summary"):SERVICE.index("async def get_risk_summary")]
    assert "FROM analytics_events" in event_section
    assert "total_events_today" in PAGE
    assert "failure_signals_today" in PAGE
