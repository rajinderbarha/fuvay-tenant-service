"""Settings Engine — constants."""
from decimal import Decimal

# ── Setting tiers ──────────────────────────────────────────────────────────
class SettingTier:
    PLATFORM = "platform"   # super admin sets
    PLAN     = "plan"       # per plan type
    TENANT   = "tenant"     # per tenant override

# ── Setting types ──────────────────────────────────────────────────────────
class SettingType:
    BOOLEAN  = "boolean"
    INTEGER  = "integer"
    DECIMAL  = "decimal"
    STRING   = "string"
    JSON     = "json"

# ── Well-known setting keys ────────────────────────────────────────────────
class SK:
    WARRANTY_PERIOD_DAYS        = "warranty_period_days"
    AUTO_CLOSE_JOB_HOURS        = "auto_close_job_hours"
    MAX_STAFF_PER_SHIFT         = "max_staff_per_shift"
    NOTIFICATION_EMAIL_ENABLED  = "notification_email_enabled"
    NOTIFICATION_SMS_ENABLED    = "notification_sms_enabled"
    NOTIFICATION_PUSH_ENABLED   = "notification_push_enabled"
    BOOKING_ADVANCE_DAYS        = "booking_advance_days"
    COMMISSION_REVIEW_HOURS     = "commission_review_hours"
    STORAGE_QUOTA_GB            = "storage_quota_gb"
    MAX_MEDIA_SIZE_MB           = "max_media_size_mb"
    CUSTOMER_REVIEW_REQUIRED    = "customer_review_required"
    SLA_BREACH_ALERT_HOURS      = "sla_breach_alert_hours"

# ── Platform defaults (fallback when no override exists) ───────────────────
PLATFORM_DEFAULTS: dict[str, object] = {
    SK.WARRANTY_PERIOD_DAYS:       30,
    SK.AUTO_CLOSE_JOB_HOURS:       48,
    SK.MAX_STAFF_PER_SHIFT:        10,
    SK.NOTIFICATION_EMAIL_ENABLED: True,
    SK.NOTIFICATION_SMS_ENABLED:   True,
    SK.NOTIFICATION_PUSH_ENABLED:  True,
    SK.BOOKING_ADVANCE_DAYS:       30,
    SK.COMMISSION_REVIEW_HOURS:    24,
    SK.STORAGE_QUOTA_GB:           5,
    SK.MAX_MEDIA_SIZE_MB:          50,
    SK.CUSTOMER_REVIEW_REQUIRED:   False,
    SK.SLA_BREACH_ALERT_HOURS:     2,
}

# Resolution order: TENANT → PLAN → PLATFORM → code_default
RESOLUTION_ORDER = [SettingTier.TENANT, SettingTier.PLAN, SettingTier.PLATFORM]

REDIS_SETTING = "serviceos:settings:{tenant_id}:{key}"
REDIS_PLATFORM_SETTING = "serviceos:settings:platform:{key}"
