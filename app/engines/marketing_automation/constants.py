"""Sprint 29 — Marketing Automation Engine constants."""

# ── Campaign types ─────────────────────────────────────────────────────────────
CAMPAIGN_TYPE_ANNOUNCEMENT          = "announcement"
CAMPAIGN_TYPE_PROMOTION             = "promotion"
CAMPAIGN_TYPE_REACTIVATION          = "reactivation"
CAMPAIGN_TYPE_PROVIDER_BOOST        = "provider_boost"
CAMPAIGN_TYPE_CATEGORY_LAUNCH       = "category_launch"
CAMPAIGN_TYPE_WALLET_REMINDER       = "wallet_reminder"
CAMPAIGN_TYPE_SUBSCRIPTION_REMINDER = "subscription_reminder"
CAMPAIGN_TYPE_REVIEW_REQUEST        = "review_request"
CAMPAIGN_TYPE_COMPLAINT_FOLLOWUP    = "complaint_followup"

VALID_CAMPAIGN_TYPES = {
    CAMPAIGN_TYPE_ANNOUNCEMENT, CAMPAIGN_TYPE_PROMOTION, CAMPAIGN_TYPE_REACTIVATION,
    CAMPAIGN_TYPE_PROVIDER_BOOST, CAMPAIGN_TYPE_CATEGORY_LAUNCH, CAMPAIGN_TYPE_WALLET_REMINDER,
    CAMPAIGN_TYPE_SUBSCRIPTION_REMINDER, CAMPAIGN_TYPE_REVIEW_REQUEST,
    CAMPAIGN_TYPE_COMPLAINT_FOLLOWUP,
}

# ── Campaign statuses ──────────────────────────────────────────────────────────
CAMP_STATUS_DRAFT      = "draft"
CAMP_STATUS_SCHEDULED  = "scheduled"
CAMP_STATUS_RUNNING    = "running"
CAMP_STATUS_PAUSED     = "paused"
CAMP_STATUS_COMPLETED  = "completed"
CAMP_STATUS_CANCELLED  = "cancelled"
CAMP_STATUS_FAILED     = "failed"

VALID_CAMPAIGN_STATUSES = {
    CAMP_STATUS_DRAFT, CAMP_STATUS_SCHEDULED, CAMP_STATUS_RUNNING,
    CAMP_STATUS_PAUSED, CAMP_STATUS_COMPLETED, CAMP_STATUS_CANCELLED,
    CAMP_STATUS_FAILED,
}

# Statuses that can be run
RUNNABLE_STATUSES  = {CAMP_STATUS_DRAFT, CAMP_STATUS_SCHEDULED, CAMP_STATUS_PAUSED}
# Statuses that can be paused
PAUSABLE_STATUSES  = {CAMP_STATUS_RUNNING, CAMP_STATUS_SCHEDULED}
# Statuses that can be cancelled
CANCELLABLE_STATUSES = {CAMP_STATUS_DRAFT, CAMP_STATUS_SCHEDULED, CAMP_STATUS_RUNNING, CAMP_STATUS_PAUSED}

# ── Target audiences ───────────────────────────────────────────────────────────
AUDIENCE_CUSTOMERS = "customers"
AUDIENCE_PROVIDERS = "providers"
AUDIENCE_STAFF     = "staff"
AUDIENCE_ADMINS    = "admins"

VALID_AUDIENCES = {AUDIENCE_CUSTOMERS, AUDIENCE_PROVIDERS, AUDIENCE_STAFF, AUDIENCE_ADMINS}

# ── Campaign rule types ────────────────────────────────────────────────────────
RULE_SEGMENT  = "segment"
RULE_TRIGGER  = "trigger"
RULE_SCHEDULE = "schedule"
RULE_LIMIT    = "limit"
RULE_CHANNEL  = "channel"

VALID_RULE_TYPES = {RULE_SEGMENT, RULE_TRIGGER, RULE_SCHEDULE, RULE_LIMIT, RULE_CHANNEL}

# ── Campaign event types ───────────────────────────────────────────────────────
EVENT_TARGETED  = "targeted"
EVENT_SENT      = "sent"
EVENT_DELIVERED = "delivered"
EVENT_OPENED    = "opened"
EVENT_CLICKED   = "clicked"
EVENT_CONVERTED = "converted"
EVENT_FAILED    = "failed"
EVENT_SKIPPED   = "skipped"

VALID_EVENT_TYPES = {
    EVENT_TARGETED, EVENT_SENT, EVENT_DELIVERED, EVENT_OPENED,
    EVENT_CLICKED, EVENT_CONVERTED, EVENT_FAILED, EVENT_SKIPPED,
}

# ── Channels ──────────────────────────────────────────────────────────────────
CHANNEL_IN_APP   = "in_app"
CHANNEL_EMAIL    = "email"
CHANNEL_SMS      = "sms"
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_PUSH     = "push"

VALID_CHANNELS = {CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_PUSH}

# ── Automation trigger keys ────────────────────────────────────────────────────
TRIGGER_ABANDONED_BOOKING_DRAFT      = "abandoned_booking_draft"
TRIGGER_ABANDONED_APPOINTMENT_DRAFT  = "abandoned_appointment_draft"
TRIGGER_ABANDONED_REAL_ESTATE_DRAFT  = "abandoned_real_estate_lead_draft"
TRIGGER_WALLET_LOW_BALANCE           = "wallet_low_balance"
TRIGGER_REVIEW_REQUEST               = "review_request_after_completion"
TRIGGER_COMPLAINT_FOLLOWUP           = "complaint_followup_after_resolution"
TRIGGER_PROVIDER_INACTIVE            = "provider_inactive"
TRIGGER_CATEGORY_LAUNCH              = "category_launch"

VALID_TRIGGERS = {
    TRIGGER_ABANDONED_BOOKING_DRAFT,
    TRIGGER_ABANDONED_APPOINTMENT_DRAFT,
    TRIGGER_ABANDONED_REAL_ESTATE_DRAFT,
    TRIGGER_WALLET_LOW_BALANCE,
    TRIGGER_REVIEW_REQUEST,
    TRIGGER_COMPLAINT_FOLLOWUP,
    TRIGGER_PROVIDER_INACTIVE,
    TRIGGER_CATEGORY_LAUNCH,
}

# ── Cooldown windows (hours) ──────────────────────────────────────────────────
COOLDOWN_HOURS: dict[str, int] = {
    TRIGGER_ABANDONED_BOOKING_DRAFT:     24,
    TRIGGER_ABANDONED_APPOINTMENT_DRAFT: 24,
    TRIGGER_ABANDONED_REAL_ESTATE_DRAFT: 48,
    TRIGGER_WALLET_LOW_BALANCE:          72,
    TRIGGER_REVIEW_REQUEST:              168,  # 7 days
    TRIGGER_COMPLAINT_FOLLOWUP:          48,
    TRIGGER_PROVIDER_INACTIVE:           168,
    TRIGGER_CATEGORY_LAUNCH:             720,  # 30 days
}

# ── Segment preview cap ───────────────────────────────────────────────────────
SEGMENT_PREVIEW_MAX = 10

# ── Error codes ───────────────────────────────────────────────────────────────
ERR_CAMPAIGN_NOT_FOUND           = "MARKETING_CAMPAIGN_NOT_FOUND"
ERR_CAMPAIGN_ACCESS_DENIED       = "MARKETING_CAMPAIGN_ACCESS_DENIED"
ERR_CAMPAIGN_INVALID_STATUS      = "MARKETING_CAMPAIGN_INVALID_STATUS"
ERR_CAMPAIGN_ALREADY_RUNNING     = "MARKETING_CAMPAIGN_ALREADY_RUNNING"
ERR_CAMPAIGN_NOT_SCHEDULED       = "MARKETING_CAMPAIGN_NOT_SCHEDULED"
ERR_SEGMENT_INVALID              = "MARKETING_SEGMENT_INVALID"
ERR_SEGMENT_TOO_LARGE            = "MARKETING_SEGMENT_TOO_LARGE"
ERR_MESSAGE_REQUIRED             = "MARKETING_MESSAGE_REQUIRED"
ERR_CHANNEL_DISABLED             = "MARKETING_CHANNEL_DISABLED"
ERR_PREFERENCE_DISABLED          = "MARKETING_PREFERENCE_DISABLED"
ERR_RATE_LIMITED                 = "MARKETING_RATE_LIMITED"
ERR_TRIGGER_NOT_FOUND            = "MARKETING_TRIGGER_NOT_FOUND"
ERR_TRIGGER_NOT_ALLOWED          = "MARKETING_TRIGGER_NOT_ALLOWED"
