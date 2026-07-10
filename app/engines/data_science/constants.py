"""Data Science Engine — constants."""
from decimal import Decimal

# ── Operational phase thresholds ───────────────────────────────────────────
class DSPhase:
    RULE_BASED     = 0   # < 50 jobs
    OBSERVATION    = 1   # 50–500 jobs
    PLATFORM_MODEL = 2   # 500–2000 jobs
    TENANT_MODEL   = 3   # 2000+ jobs

JOB_THRESHOLD_OBSERVATION    = 50
JOB_THRESHOLD_PLATFORM_MODEL = 500
JOB_THRESHOLD_TENANT_MODEL   = 2000

# ── Churn risk bands ───────────────────────────────────────────────────────
CHURN_BANDS = {
    "low":      (0,  30),
    "medium":   (31, 60),
    "high":     (61, 85),
    "critical": (86, 100),
}

# ── Churn signal weights ───────────────────────────────────────────────────
CHURN_SIGNAL_WEIGHTS = {
    "days_since_last_job":    0.30,
    "wallet_balance_trend":   0.25,
    "health_score_trend":     0.20,
    "complaint_rate":         0.15,
    "booking_frequency_drop": 0.10,
}

# ── Demand forecast settings ───────────────────────────────────────────────
FORECAST_HORIZON_DAYS   = 14
FORECAST_LOOKBACK_DAYS  = 90
MIN_DATA_POINTS_PROPHET = 30

# ── Staff performance signal weights ──────────────────────────────────────
STAFF_SIGNAL_WEIGHTS = {
    "job_completion_rate":  0.35,
    "avg_customer_rating":  0.30,
    "sla_adherence_rate":   0.20,
    "avg_job_duration_min": 0.15,
}

# ── Anomaly thresholds ─────────────────────────────────────────────────────
ANOMALY_THRESHOLDS = {
    "cancellation_spike_pct":   50.0,
    "completion_drop_pct":      30.0,
    "warranty_claims_per_week":  5,
    "response_time_spike_min":  60,
    "wallet_burn_spike_pct":    100.0,
}

# ── LTV settings ──────────────────────────────────────────────────────────
LTV_HORIZON_MONTHS   = 12
LTV_DISCOUNT_RATE    = Decimal("0.10")

# ── Model identifiers ──────────────────────────────────────────────────────
class ModelType:
    CHURN_PLATFORM  = "churn_platform"
    CHURN_TENANT    = "churn_tenant"
    DEMAND_PROPHET  = "demand_prophet"
    STAFF_XGBOOST   = "staff_xgboost"
    LTV_REGRESSION  = "ltv_regression"
    ANOMALY_ZSCORE  = "anomaly_zscore"

# ── Prediction types ───────────────────────────────────────────────────────
class PredType:
    CHURN      = "churn"
    DEMAND     = "demand"
    PRICING    = "pricing"
    STAFF      = "staff_performance"
    LTV        = "customer_ltv"
    ANOMALY    = "anomaly"

# ── Anomaly types ──────────────────────────────────────────────────────────
class AnomalyType:
    CANCELLATION_SPIKE  = "cancellation_spike"
    COMPLETION_DROP     = "completion_drop"
    WARRANTY_SURGE      = "warranty_surge"
    RESPONSE_TIME_SPIKE = "response_time_spike"
    WALLET_BURN_SPIKE   = "wallet_burn_spike"
    CHURN_RISK_JUMP     = "churn_risk_jump"

# ── Redis keys ─────────────────────────────────────────────────────────────
REDIS_CHURN_SCORE    = "serviceos:ds:churn:{tenant_id}"
REDIS_DEMAND_CAST    = "serviceos:ds:demand:{tenant_id}"
REDIS_DS_PHASE       = "serviceos:ds:phase:{tenant_id}"
REDIS_MODEL_META     = "serviceos:ds:model:{model_type}:meta"
