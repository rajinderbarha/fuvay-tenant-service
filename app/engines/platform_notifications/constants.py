"""Sprint 27 — Platform Notifications, Chat, and Audit constants."""

# ── Notification error codes ──────────────────────────────────────────────────
ERR_NOTIF_EVENT_NOT_FOUND         = "NOTIFICATION_EVENT_NOT_FOUND"
ERR_NOTIF_TEMPLATE_NOT_FOUND      = "NOTIFICATION_TEMPLATE_NOT_FOUND"
ERR_NOTIF_TEMPLATE_RENDER_FAILED  = "NOTIFICATION_TEMPLATE_RENDER_FAILED"
ERR_NOTIF_RECIPIENT_NOT_FOUND     = "NOTIFICATION_RECIPIENT_NOT_FOUND"
ERR_NOTIF_OUTBOX_NOT_FOUND        = "NOTIFICATION_OUTBOX_NOT_FOUND"
ERR_NOTIF_OUTBOX_ACCESS_DENIED    = "NOTIFICATION_OUTBOX_ACCESS_DENIED"
ERR_NOTIF_CHANNEL_NOT_CONFIGURED  = "NOTIFICATION_CHANNEL_NOT_CONFIGURED"
ERR_NOTIF_DELIVERY_FAILED         = "NOTIFICATION_DELIVERY_FAILED"
ERR_NOTIF_RETRY_NOT_ALLOWED       = "NOTIFICATION_RETRY_NOT_ALLOWED"
ERR_NOTIF_PREFERENCE_DISABLED     = "NOTIFICATION_PREFERENCE_DISABLED"
ERR_IN_APP_NOT_FOUND              = "IN_APP_NOTIFICATION_NOT_FOUND"
ERR_IN_APP_ACCESS_DENIED          = "IN_APP_NOTIFICATION_ACCESS_DENIED"

# ── Chat error codes ──────────────────────────────────────────────────────────
ERR_CHAT_THREAD_NOT_FOUND         = "CHAT_THREAD_NOT_FOUND"
ERR_CHAT_THREAD_ACCESS_DENIED     = "CHAT_THREAD_ACCESS_DENIED"
ERR_CHAT_THREAD_CLOSED            = "CHAT_THREAD_CLOSED"
ERR_CHAT_PARTICIPANT_NOT_FOUND    = "CHAT_PARTICIPANT_NOT_FOUND"
ERR_CHAT_MESSAGE_REQUIRED         = "CHAT_MESSAGE_REQUIRED"
ERR_CHAT_MESSAGE_NOT_FOUND        = "CHAT_MESSAGE_NOT_FOUND"
ERR_CHAT_MESSAGE_ACCESS_DENIED    = "CHAT_MESSAGE_ACCESS_DENIED"
ERR_CHAT_RECORD_ACCESS_DENIED     = "CHAT_RECORD_ACCESS_DENIED"
ERR_CHAT_RECORD_NOT_FOUND         = "CHAT_RECORD_NOT_FOUND"
ERR_CHAT_CANNOT_SEND              = "CHAT_CANNOT_SEND"

# ── Audit error codes ─────────────────────────────────────────────────────────
ERR_AUDIT_LOG_NOT_FOUND           = "AUDIT_LOG_NOT_FOUND"
ERR_AUDIT_LOG_ACCESS_DENIED       = "AUDIT_LOG_ACCESS_DENIED"
ERR_AUDIT_EXPORT_NOT_ALLOWED      = "AUDIT_EXPORT_NOT_ALLOWED"
ERR_AUDIT_PAYLOAD_REDACTED        = "AUDIT_PAYLOAD_REDACTED"

# ── Notification statuses ─────────────────────────────────────────────────────
NOTIF_EVENT_CREATED    = "created"
NOTIF_EVENT_PROCESSED  = "processed"
NOTIF_EVENT_FAILED     = "failed"
NOTIF_EVENT_IGNORED    = "ignored"

DELIVERY_PENDING                = "pending"
DELIVERY_QUEUED                 = "queued"
DELIVERY_SENT                   = "sent"
DELIVERY_DELIVERED              = "delivered"
DELIVERY_FAILED                 = "failed"
DELIVERY_SKIPPED                = "skipped"
DELIVERY_PROVIDER_NOT_CONFIGURED= "provider_not_configured"
DELIVERY_PREFERENCE_DISABLED    = "preference_disabled"

READ_UNREAD   = "unread"
READ_READ     = "read"
READ_ARCHIVED = "archived"

# ── Channels ──────────────────────────────────────────────────────────────────
CHANNEL_IN_APP    = "in_app"
CHANNEL_EMAIL     = "email"
CHANNEL_SMS       = "sms"
CHANNEL_WHATSAPP  = "whatsapp"
CHANNEL_PUSH      = "push"
ALL_CHANNELS = [CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_PUSH]

# ── Recipient types ───────────────────────────────────────────────────────────
RECIP_CUSTOMER = "customer"
RECIP_PROVIDER = "provider"
RECIP_STAFF    = "staff"
RECIP_ADMIN    = "admin"
RECIP_SYSTEM   = "system"

# ── Severity ──────────────────────────────────────────────────────────────────
SEV_INFO     = "info"
SEV_SUCCESS  = "success"
SEV_WARNING  = "warning"
SEV_CRITICAL = "critical"

# ── Chat thread statuses ──────────────────────────────────────────────────────
THREAD_OPEN     = "open"
THREAD_CLOSED   = "closed"
THREAD_ARCHIVED = "archived"
THREAD_BLOCKED  = "blocked"
TERMINAL_THREAD_STATUSES = {THREAD_CLOSED, THREAD_ARCHIVED, THREAD_BLOCKED}

# ── Chat record types ─────────────────────────────────────────────────────────
RECORD_SERVICE_BOOKING    = "service_booking"
RECORD_SERVICE_JOB        = "service_job"
RECORD_COACHING_APPOINTMENT = "coaching_appointment"
RECORD_REAL_ESTATE_LEAD   = "real_estate_lead"
RECORD_COMPLAINT          = "complaint"
RECORD_SUPPORT_CASE       = "support_case"
RECORD_ADMIN_INTERNAL     = "admin_internal"

# ── Message visibility ────────────────────────────────────────────────────────
VIS_THREAD        = "thread"
VIS_ADMIN_ONLY    = "admin_only"
VIS_PROVIDER_ONLY = "provider_only"
VIS_CUSTOMER_ONLY = "customer_only"

# ── Message types ─────────────────────────────────────────────────────────────
MSG_TEXT     = "text"
MSG_MEDIA    = "media"
MSG_SYSTEM   = "system"
MSG_TEMPLATE = "template"

# ── Message delivery ──────────────────────────────────────────────────────────
MSG_SENT      = "sent"
MSG_DELIVERED = "delivered"
MSG_READ      = "read"
MSG_FAILED    = "failed"

# ── Sensitive fields to redact from audit logs ────────────────────────────────
SENSITIVE_FIELDS = {
    "password", "password_hash", "access_token", "refresh_token",
    "otp", "secret", "api_key", "private_key", "payment_card",
    "authorization_header", "cookie", "token", "auth", "key_hash",
}

# ── Notification event keys ───────────────────────────────────────────────────
# Home Service
EVT_BOOKING_CONFIRMED     = "booking.confirmed"
EVT_JOB_CREATED           = "job.created"
EVT_JOB_ASSIGNED          = "job.assigned"
EVT_JOB_ACCEPTED          = "job.accepted"
EVT_JOB_REJECTED          = "job.rejected"
EVT_JOB_SCHEDULED         = "job.scheduled"
EVT_JOB_ON_THE_WAY        = "job.on_the_way"
EVT_JOB_REACHED_SITE      = "job.reached_site"
EVT_JOB_INSPECTION_STARTED= "job.inspection_started"
EVT_JOB_QUOTE_REQUIRED    = "job.quote_required"
EVT_JOB_WORK_DONE         = "job.work_done"
EVT_JOB_COMPLETED         = "job.completed"
# Quote
EVT_QUOTE_SENT            = "quote.sent_to_customer"
EVT_QUOTE_APPROVED        = "quote.customer_approved"
EVT_QUOTE_REJECTED        = "quote.customer_rejected"
EVT_QUOTE_REVISION        = "quote.revision_requested"
# Invoice / Payment
EVT_INVOICE_ISSUED        = "invoice.issued"
EVT_PAYMENT_COLLECTED     = "payment.collected"
EVT_COMMISSION_DEDUCTED   = "commission.deducted"
EVT_COMMISSION_FAILED     = "commission.failed"
EVT_WALLET_LOW            = "wallet.low_balance"
EVT_WALLET_EXHAUSTED      = "wallet.exhausted"
# Coaching
EVT_APPT_CONFIRMED        = "appointment.confirmed"
EVT_APPT_ACCEPTED         = "appointment.accepted"
EVT_APPT_STARTED          = "appointment.started"
EVT_APPT_COMPLETED        = "appointment.completed"
EVT_APPT_NO_SHOW          = "appointment.no_show"
# Real Estate
EVT_LEAD_CREATED          = "lead.created"
EVT_LEAD_ACCEPTED         = "lead.accepted"
EVT_LEAD_CONTACTED        = "lead.contacted"
EVT_LEAD_FOLLOW_UP        = "lead.follow_up_scheduled"
EVT_LEAD_SITE_VISIT       = "lead.site_visit_planned"
# Review
EVT_REVIEW_SUBMITTED      = "review.submitted"
EVT_REVIEW_APPROVED       = "review.approved"
EVT_REVIEW_REJECTED       = "review.rejected"
EVT_REVIEW_FLAGGED        = "review.flagged"
EVT_REVIEW_REPLY          = "review.reply_submitted"
# Complaint
EVT_COMPLAINT_CREATED     = "complaint.created"
EVT_COMPLAINT_RESPONDED   = "complaint.provider_responded"
EVT_COMPLAINT_RESOLUTION  = "complaint.resolution_proposed"
EVT_COMPLAINT_REWORK      = "complaint.rework_approved"
EVT_COMPLAINT_REFUND      = "complaint.refund_approved"
EVT_COMPLAINT_RESOLVED    = "complaint.resolved"
# System / Admin
EVT_AUTH_LOGIN_SUCCESS    = "auth.login_success"
EVT_AUTH_LOGIN_FAILED     = "auth.login_failed"
EVT_TENANT_VERIFIED       = "tenant.verified"
EVT_TENANT_SUSPENDED      = "tenant.suspended"
EVT_ENGINE_ENABLED        = "engine.enabled"
EVT_ENGINE_DISABLED       = "engine.disabled"
EVT_CATEGORY_ENABLED      = "category.enabled"
EVT_CATEGORY_DISABLED     = "category.disabled"
# Chat
EVT_CHAT_NEW_MESSAGE      = "chat.new_message"

MAX_RETRY_COUNT = 3
