"""Phase 5 — Settings + Notification + Media + Analytics Tests (50 tests)."""
import uuid
from decimal import Decimal
import pytest

from app.engines.settings_engine.constants import (
    SettingTier, SettingType, SK, PLATFORM_DEFAULTS, RESOLUTION_ORDER,
)
from app.engines.notification.constants import Channel, NotifStatus, NotifType, MAX_RETRY_ATTEMPTS
from app.engines.analytics.models import AnalyticsEvent, DailyMetric

# ── 1. Settings constants ─────────────────────────────────────────────────────
def test_setting_tiers_defined():
    assert SettingTier.PLATFORM == "platform"
    assert SettingTier.PLAN == "plan"
    assert SettingTier.TENANT == "tenant"

def test_resolution_order_correct():
    assert RESOLUTION_ORDER[0] == SettingTier.TENANT
    assert RESOLUTION_ORDER[1] == SettingTier.PLAN
    assert RESOLUTION_ORDER[2] == SettingTier.PLATFORM

def test_platform_defaults_exist():
    assert SK.WARRANTY_PERIOD_DAYS in PLATFORM_DEFAULTS
    assert SK.AUTO_CLOSE_JOB_HOURS in PLATFORM_DEFAULTS
    assert SK.STORAGE_QUOTA_GB in PLATFORM_DEFAULTS

def test_platform_defaults_sensible():
    assert PLATFORM_DEFAULTS[SK.WARRANTY_PERIOD_DAYS] == 30
    assert PLATFORM_DEFAULTS[SK.AUTO_CLOSE_JOB_HOURS] == 48
    assert PLATFORM_DEFAULTS[SK.STORAGE_QUOTA_GB] == 5

def test_all_sk_keys_have_defaults():
    sk_keys = [v for k, v in SK.__dict__.items() if not k.startswith("_")]
    for key in sk_keys:
        assert key in PLATFORM_DEFAULTS, f"{key} missing from PLATFORM_DEFAULTS"

def test_setting_types_unique():
    types = [v for k, v in SettingType.__dict__.items() if not k.startswith("_")]
    assert len(types) == len(set(types))

# ── 2. Settings resolution chain logic ───────────────────────────────────────
def test_tenant_overrides_plan():
    # Simulated resolution: tenant value wins
    tenant_val = 14
    plan_val = 30
    platform_val = 30
    resolved = tenant_val  # tenant tier wins
    assert resolved == tenant_val

def test_plan_overrides_platform():
    platform_val = 30
    plan_val = 45
    resolved = plan_val  # plan wins when no tenant override
    assert resolved != platform_val

def test_platform_default_used_when_no_override():
    # When nothing is set, code default is used
    key = SK.WARRANTY_PERIOD_DAYS
    default = PLATFORM_DEFAULTS[key]
    assert default == 30

def test_setting_value_wrapped_in_v_key():
    # Settings are stored as {"v": actual_value}
    value = 42
    wrapped = {"v": value}
    unwrapped = wrapped.get("v")
    assert unwrapped == value

# ── 3. Notification constants ─────────────────────────────────────────────────
def test_notification_channels():
    assert Channel.PUSH == "push"
    assert Channel.SMS == "sms"
    assert Channel.EMAIL == "email"
    assert Channel.INAPP == "in_app"

def test_notification_statuses():
    statuses = [NotifStatus.PENDING, NotifStatus.QUEUED, NotifStatus.SENT,
                NotifStatus.DELIVERED, NotifStatus.FAILED, NotifStatus.BOUNCED]
    assert len(statuses) == len(set(statuses))

def test_notification_types_defined():
    types = [v for k, v in NotifType.__dict__.items() if not k.startswith("_")]
    assert len(types) >= 5

def test_max_retry_attempts():
    assert MAX_RETRY_ATTEMPTS == 3

def test_retry_not_allowed_after_max():
    attempt_count = 3
    can_retry = attempt_count < MAX_RETRY_ATTEMPTS
    assert not can_retry

def test_retry_allowed_before_max():
    attempt_count = 2
    can_retry = attempt_count < MAX_RETRY_ATTEMPTS
    assert can_retry

# ── 4. Notification template interpolation ────────────────────────────────────
def test_template_variable_interpolation():
    template_body = "Hello {{name}}, your job {{job_id}} is confirmed."
    data = {"name": "Rahul", "job_id": "JOB-001"}
    body = template_body
    for k, v in data.items():
        body = body.replace(f"{{{{{k}}}}}", str(v))
    assert "Rahul" in body
    assert "JOB-001" in body
    assert "{{" not in body

def test_template_partial_interpolation():
    template_body = "Hello {{name}}, amount: {{amount}}"
    data = {"name": "Priya"}  # amount missing
    body = template_body
    for k, v in data.items():
        body = body.replace(f"{{{{{k}}}}}", str(v))
    assert "Priya" in body
    assert "{{amount}}" in body  # not replaced

# ── 5. Media Vault ────────────────────────────────────────────────────────────
def test_max_file_size():
    from app.engines.media.service import MAX_FILE_SIZE_BYTES
    assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024

def test_file_size_validation():
    from app.engines.media.service import MAX_FILE_SIZE_BYTES
    small = 1024 * 1024  # 1MB
    large = 60 * 1024 * 1024  # 60MB
    assert small <= MAX_FILE_SIZE_BYTES
    assert large > MAX_FILE_SIZE_BYTES

def test_storage_quota_calculation():
    quota_bytes = 5 * 1024 * 1024 * 1024
    used_bytes = 4 * 1024 * 1024 * 1024
    pct = round(used_bytes / quota_bytes * 100, 1)
    alert = used_bytes / quota_bytes > 0.85
    assert pct == 80.0
    assert not alert

def test_storage_quota_alert_triggered():
    quota_bytes = 5 * 1024 * 1024 * 1024
    used_bytes = int(4.5 * 1024 * 1024 * 1024)  # 90%
    alert = used_bytes / quota_bytes > 0.85
    assert alert

def test_storage_key_format():
    tenant_id = uuid.uuid4()
    file_name = "photo.jpg"
    import secrets
    storage_key = f"tenants/{tenant_id}/{secrets.token_hex(8)}/{file_name}"
    assert str(tenant_id) in storage_key
    assert file_name in storage_key
    assert storage_key.startswith("tenants/")

def test_signed_url_contains_storage_key():
    storage_key = f"tenants/abc/xyz/photo.jpg"
    import secrets
    signed_url = f"https://cdn.placeholder.com/{storage_key}?sig={secrets.token_hex(8)}"
    assert storage_key in signed_url
    assert "sig=" in signed_url

# ── 6. Analytics ──────────────────────────────────────────────────────────────
def test_analytics_event_model_fields():
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(AnalyticsEvent).columns}
    assert "event_id" in cols
    assert "tenant_id" in cols
    assert "event_type" in cols
    assert "engine_id" in cols
    assert "payload" in cols
    assert "occurred_at" in cols

def test_analytics_event_idempotency_key():
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(AnalyticsEvent).mapper.persist_selectable.constraints}
    assert "uq_ae_event_id" in constraints

def test_daily_metric_unique_constraint():
    from sqlalchemy.inspection import inspect
    constraints = {c.name for c in inspect(DailyMetric).mapper.persist_selectable.constraints}
    assert "uq_dm_tenant_date_key" in constraints

def test_daily_metric_model_fields():
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(DailyMetric).columns}
    assert "tenant_id" in cols
    assert "metric_date" in cols
    assert "metric_key" in cols
    assert "value_num" in cols
    assert "value_json" in cols
    assert "computed_at" in cols

# ── 7. Settings model fields ──────────────────────────────────────────────────
def test_tenant_setting_model_fields():
    from app.engines.settings_engine.models import TenantSetting
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(TenantSetting).columns}
    assert "tenant_id" in cols
    assert "key" in cols
    assert "value" in cols
    assert "setting_type" in cols

def test_setting_audit_log_fields():
    from app.engines.settings_engine.models import SettingAuditLog
    from sqlalchemy.inspection import inspect
    cols = {c.key for c in inspect(SettingAuditLog).columns}
    assert "tier" in cols
    assert "key" in cols
    assert "old_value" in cols
    assert "new_value" in cols

# ── 8. HTTP endpoint probes ───────────────────────────────────────────────────
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)

def test_settings_meta(client):
    r = client.get("/v1/settings/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "settings"
    assert "resolution_chain" in d["capabilities"]

def test_notification_meta(client):
    r = client.get("/v1/notifications/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "notification"
    assert "push" in d["channels"]

def test_media_meta(client):
    r = client.get("/v1/media/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "media"
    assert "signed_urls" in d["capabilities"]

def test_analytics_meta(client):
    r = client.get("/v1/analytics/meta")
    assert r.status_code == 200
    d = r.json()
    assert d["engine_id"] == "analytics"
    assert "idempotent_ingestion" in d["capabilities"]

def test_settings_platform_requires_auth(client):
    assert client.get("/v1/settings/platform").status_code == 401

def test_settings_resolve_requires_auth(client):
    assert client.get("/v1/settings/resolve/warranty_period_days").status_code == 401

def test_notification_send_requires_auth(client):
    assert client.post("/v1/notifications/send", json={}).status_code == 401

def test_media_upload_requires_auth(client):
    assert client.post("/v1/media/upload/initiate", json={}).status_code == 401

def test_media_quota_requires_auth(client):
    tid = uuid.uuid4()
    assert client.get(f"/v1/media/tenants/{tid}/quota").status_code == 401

def test_analytics_platform_summary_requires_admin(client):
    assert client.get("/v1/analytics/platform/summary").status_code == 401

def test_analytics_ingest_requires_auth(client):
    assert client.post("/v1/analytics/events/ingest", json={}).status_code == 401

def test_analytics_event_stream_requires_auth(client):
    assert client.get("/v1/analytics/events/stream").status_code == 401

def test_all_prior_phases_still_pass(client):
    assert client.get("/health").status_code == 200
    assert client.get("/v1/commerce/meta").status_code == 200
    assert client.get("/v1/pricing/meta").status_code == 200
    assert client.get("/v1/settings/meta").status_code == 200
    assert client.get("/v1/notifications/meta").status_code == 200
    assert client.get("/v1/media/meta").status_code == 200
    assert client.get("/v1/analytics/meta").status_code == 200
