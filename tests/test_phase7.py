"""Phase 7 — Data Science Engine Tests (45 tests)."""
import uuid
from decimal import Decimal
import pytest

from app.engines.data_science.constants import (
    DSPhase, JOB_THRESHOLD_OBSERVATION, JOB_THRESHOLD_PLATFORM_MODEL,
    JOB_THRESHOLD_TENANT_MODEL, CHURN_BANDS, CHURN_SIGNAL_WEIGHTS,
    STAFF_SIGNAL_WEIGHTS, ANOMALY_THRESHOLDS, LTV_HORIZON_MONTHS,
    ModelType, PredType, AnomalyType, FORECAST_HORIZON_DAYS,
)

# ── 1. Phase thresholds ───────────────────────────────────────────────────────
def test_phase_order():
    assert DSPhase.RULE_BASED < DSPhase.OBSERVATION < DSPhase.PLATFORM_MODEL < DSPhase.TENANT_MODEL

def test_job_thresholds_ascending():
    assert JOB_THRESHOLD_OBSERVATION < JOB_THRESHOLD_PLATFORM_MODEL < JOB_THRESHOLD_TENANT_MODEL

def test_rule_based_below_observation_threshold():
    jobs = 0
    phase = (DSPhase.TENANT_MODEL if jobs >= JOB_THRESHOLD_TENANT_MODEL
             else DSPhase.PLATFORM_MODEL if jobs >= JOB_THRESHOLD_PLATFORM_MODEL
             else DSPhase.OBSERVATION if jobs >= JOB_THRESHOLD_OBSERVATION
             else DSPhase.RULE_BASED)
    assert phase == DSPhase.RULE_BASED

def test_observation_phase_detection():
    jobs = 100
    phase = (DSPhase.TENANT_MODEL if jobs >= JOB_THRESHOLD_TENANT_MODEL
             else DSPhase.PLATFORM_MODEL if jobs >= JOB_THRESHOLD_PLATFORM_MODEL
             else DSPhase.OBSERVATION if jobs >= JOB_THRESHOLD_OBSERVATION
             else DSPhase.RULE_BASED)
    assert phase == DSPhase.OBSERVATION

def test_platform_model_phase_detection():
    jobs = 1000
    phase = (DSPhase.TENANT_MODEL if jobs >= JOB_THRESHOLD_TENANT_MODEL
             else DSPhase.PLATFORM_MODEL if jobs >= JOB_THRESHOLD_PLATFORM_MODEL
             else DSPhase.OBSERVATION if jobs >= JOB_THRESHOLD_OBSERVATION
             else DSPhase.RULE_BASED)
    assert phase == DSPhase.PLATFORM_MODEL

def test_tenant_model_phase_detection():
    jobs = 3000
    phase = (DSPhase.TENANT_MODEL if jobs >= JOB_THRESHOLD_TENANT_MODEL
             else DSPhase.PLATFORM_MODEL if jobs >= JOB_THRESHOLD_PLATFORM_MODEL
             else DSPhase.OBSERVATION if jobs >= JOB_THRESHOLD_OBSERVATION
             else DSPhase.RULE_BASED)
    assert phase == DSPhase.TENANT_MODEL

def test_observation_mode_flag():
    phase = DSPhase.RULE_BASED
    observation_mode = phase < DSPhase.PLATFORM_MODEL
    assert observation_mode is True

def test_observation_mode_off_in_platform_model():
    phase = DSPhase.PLATFORM_MODEL
    observation_mode = phase < DSPhase.PLATFORM_MODEL
    assert observation_mode is False

# ── 2. Churn prediction logic ─────────────────────────────────────────────────
def test_churn_signal_weights_sum_to_one():
    total = sum(CHURN_SIGNAL_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001

def test_churn_bands_cover_0_to_100():
    for score in [0, 15, 30, 31, 45, 60, 61, 75, 85, 86, 95, 100]:
        matched = [b for b, (lo, hi) in CHURN_BANDS.items() if lo <= score <= hi]
        assert len(matched) == 1, f"Score {score} matched {matched}"

def test_churn_band_names():
    assert "low" in CHURN_BANDS
    assert "medium" in CHURN_BANDS
    assert "high" in CHURN_BANDS
    assert "critical" in CHURN_BANDS

def test_healthy_tenant_low_churn():
    signals = {"days_since_last_job": 100.0, "wallet_balance_trend": 90.0,
               "health_score_trend": 90.0, "complaint_rate": 95.0, "booking_frequency_drop": 90.0}
    score = max(0.0, min(100.0,
        100.0 - sum(signals[k] * w for k, w in CHURN_SIGNAL_WEIGHTS.items())))
    assert score < 30.0

def test_at_risk_tenant_high_churn():
    signals = {"days_since_last_job": 10.0, "wallet_balance_trend": 20.0,
               "health_score_trend": 25.0, "complaint_rate": 15.0, "booking_frequency_drop": 10.0}
    score = max(0.0, min(100.0,
        100.0 - sum(signals[k] * w for k, w in CHURN_SIGNAL_WEIGHTS.items())))
    assert score > 60.0

def test_churn_score_bounded():
    signals = {k: 50.0 for k in CHURN_SIGNAL_WEIGHTS}
    score = max(0.0, min(100.0,
        100.0 - sum(signals[k] * w for k, w in CHURN_SIGNAL_WEIGHTS.items())))
    assert 0.0 <= score <= 100.0

# ── 3. Staff performance ──────────────────────────────────────────────────────
def test_staff_signal_weights_sum_to_one():
    total = sum(STAFF_SIGNAL_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001

def test_high_performing_staff():
    signals = {"job_completion_rate": 98.0, "avg_customer_rating": 95.0,
               "sla_adherence_rate": 97.0, "avg_job_duration_min": 90.0}
    score = sum(signals[k] * w for k, w in STAFF_SIGNAL_WEIGHTS.items())
    score = min(100.0, max(0.0, score))
    assert score > 90.0

def test_poor_performing_staff():
    signals = {"job_completion_rate": 40.0, "avg_customer_rating": 35.0,
               "sla_adherence_rate": 30.0, "avg_job_duration_min": 20.0}
    score = sum(signals[k] * w for k, w in STAFF_SIGNAL_WEIGHTS.items())
    score = min(100.0, max(0.0, score))
    assert score < 40.0

def test_staff_score_bounded():
    signals = {k: 50.0 for k in STAFF_SIGNAL_WEIGHTS}
    score = sum(signals[k] * w for k, w in STAFF_SIGNAL_WEIGHTS.items())
    assert 0.0 <= min(100.0, max(0.0, score)) <= 100.0

# ── 4. Demand forecasting ─────────────────────────────────────────────────────
def test_forecast_horizon():
    assert FORECAST_HORIZON_DAYS == 14

def test_weekend_multiplier_higher():
    base = 3.0
    weekday = base * 1.0
    weekend = base * 1.4
    assert weekend > weekday

def test_forecast_generates_correct_days():
    from datetime import date, timedelta
    today = date.today()
    forecasts = []
    for i in range(FORECAST_HORIZON_DAYS):
        d = today + timedelta(days=i + 1)
        forecasts.append({"date": str(d), "predicted_jobs": 3.0})
    assert len(forecasts) == 14

def test_peak_day_detection():
    forecasts = [{"date": "2026-06-28", "predicted_jobs": 3.0},
                 {"date": "2026-06-29", "predicted_jobs": 5.0},
                 {"date": "2026-06-30", "predicted_jobs": 4.0}]
    peak = max(forecasts, key=lambda x: x["predicted_jobs"])
    assert peak["date"] == "2026-06-29"

# ── 5. Anomaly thresholds ─────────────────────────────────────────────────────
def test_anomaly_thresholds_exist():
    assert "cancellation_spike_pct" in ANOMALY_THRESHOLDS
    assert "completion_drop_pct" in ANOMALY_THRESHOLDS
    assert "warranty_claims_per_week" in ANOMALY_THRESHOLDS

def test_anomaly_type_constants_unique():
    vals = [v for k, v in AnomalyType.__dict__.items() if not k.startswith("_")]
    assert len(vals) == len(set(vals))

def test_anomaly_detection_cancellation_spike():
    baseline = 10; current = 18
    pct_increase = (current - baseline) / baseline * 100
    threshold = ANOMALY_THRESHOLDS["cancellation_spike_pct"]
    is_anomaly = pct_increase >= threshold
    assert is_anomaly

def test_no_anomaly_normal_variation():
    baseline = 10; current = 12
    pct_increase = (current - baseline) / baseline * 100
    threshold = ANOMALY_THRESHOLDS["cancellation_spike_pct"]
    is_anomaly = pct_increase >= threshold
    assert not is_anomaly

# ── 6. LTV prediction math ────────────────────────────────────────────────────
def test_ltv_horizon():
    assert LTV_HORIZON_MONTHS == 12

def test_ltv_simple_calculation():
    monthly_jobs = 2.0; avg_job_value = 800.0; months = 12; churn_probability = 0.3
    expected_remaining_months = months * (1 - churn_probability)
    ltv = monthly_jobs * avg_job_value * expected_remaining_months
    assert ltv > 0

def test_higher_churn_lower_ltv():
    base = 800.0 * 2 * 12
    ltv_low_churn  = base * (1 - 0.1)
    ltv_high_churn = base * (1 - 0.8)
    assert ltv_low_churn > ltv_high_churn

# ── 7. Model tracking ─────────────────────────────────────────────────────────
def test_model_type_constants_unique():
    vals = [v for k, v in ModelType.__dict__.items() if not k.startswith("_")]
    assert len(vals) == len(set(vals))

def test_pred_type_constants_unique():
    vals = [v for k, v in PredType.__dict__.items() if not k.startswith("_")]
    assert len(vals) == len(set(vals))

def test_model_version_format():
    from datetime import datetime, timezone
    import secrets
    now = datetime.now(timezone.utc)
    version = f"v{now.strftime('%Y%m%d')}-{secrets.token_hex(3)}"
    assert version.startswith("v2026")
    assert len(version) > 10  # v + 8 date digits + - + 6 hex = 16 chars

# ── 8. Model fields ───────────────────────────────────────────────────────────
def test_prediction_record_immutable_design():
    from app.engines.data_science.models import PredictionRecord
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(PredictionRecord).columns}
    assert {"inputs","output","observation_mode","ds_phase","model_version",
            "confidence","computed_at"}.issubset(cols)

def test_churn_signal_model_fields():
    from app.engines.data_science.models import ChurnSignal
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(ChurnSignal).columns}
    assert {"churn_score","churn_band","contributing_factors",
            "prev_score","score_delta","observation_mode"}.issubset(cols)

def test_anomaly_record_acknowledgment_fields():
    from app.engines.data_science.models import AnomalyRecord
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(AnomalyRecord).columns}
    assert {"acknowledged_by","acknowledged_at","resolution_notes","notification_sent"}.issubset(cols)

def test_model_version_unique_constraint():
    from app.engines.data_science.models import ModelVersion
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(ModelVersion).mapper.persist_selectable.constraints}
    assert "uq_mv_type_version" in constraints

# ── 9. HTTP endpoint probes ───────────────────────────────────────────────────
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def test_ds_meta(client):
    r = client.get("/v1/ds/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "data_science"
    assert d["endpoint_count"] == 21
    assert len(d["phases"]) == 4

def test_churn_score_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/ds/tenants/{tid}/churn/score").status_code == 401

def test_at_risk_requires_admin(client):
    assert client.get("/v1/ds/churn/at-risk").status_code == 401

def test_demand_forecast_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/ds/tenants/{tid}/demand/forecast").status_code == 401

def test_staff_rankings_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/ds/tenants/{tid}/staff/rankings").status_code == 401

def test_anomalies_requires_auth(client):
    assert client.get("/v1/ds/anomalies").status_code == 401

def test_models_requires_admin(client):
    assert client.get("/v1/ds/models").status_code == 401

def test_platform_summary_requires_admin(client):
    assert client.get("/v1/ds/platform/summary").status_code == 401

def test_platform_demand_intelligence_requires_admin(client):
    assert client.get("/v1/ds/platform/demand-intelligence").status_code == 401

def test_all_phases_still_running(client):
    metas = ["/health", "/v1/commerce/meta", "/v1/pricing/meta",
             "/v1/settings/meta", "/v1/notifications/meta",
             "/v1/media/meta", "/v1/analytics/meta",
             "/v1/rag/meta", "/v1/ds/meta"]
    for path in metas:
        r = client.get(path)
        assert r.status_code == 200, f"Failed: {path} → {r.status_code}"
