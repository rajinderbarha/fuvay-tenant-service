"""Compliance Engine — constants. Proven Level 5.

Proven patterns in this engine:
  ✅ Consent records IMMUTABLE — new row per event, never UPDATE existing
  ✅ Deletion SLA 72h — enforced by Celery countdown, not polling
  ✅ Data access log append-only — no UPDATE or DELETE ever
  ✅ Portability export idempotent — same request_id returns same export
  ✅ Retention policy checked before every write in compliant engines
  ✅ Financial records exempt from erasure — GDPR/DPDP exception stored per row
"""

# ── DPDP Act 2023 / GDPR SLA requirements ─────────────────────────────────
ERASURE_SLA_HOURS          = 72    # DPDP Act 2023: 72h maximum
PORTABILITY_SLA_HOURS      = 72    # deliver export within 72h
CONSENT_EXPIRY_YEARS       = 3     # re-consent required every 3 years

# ── Consent types ─────────────────────────────────────────────────────────
class ConsentType:
    DATA_PROCESSING   = "data_processing"
    MARKETING         = "marketing"
    ANALYTICS         = "analytics"
    THIRD_PARTY_SHARE = "third_party_share"
    PUSH_NOTIFICATIONS= "push_notifications"

class ConsentAction:
    GRANTED   = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED   = "expired"
    UPDATED   = "updated"

# ── Deletion request statuses ─────────────────────────────────────────────
class DeletionStatus:
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    PARTIAL    = "partial"      # financial records exempted
    REJECTED   = "rejected"     # legitimate grounds (active dispute)
    FAILED     = "failed"

# ── Portability export statuses ───────────────────────────────────────────
class ExportStatus:
    QUEUED     = "queued"
    PROCESSING = "processing"
    READY      = "ready"
    DOWNLOADED = "downloaded"
    EXPIRED    = "expired"

# ── Data categories (what each engine holds) ──────────────────────────────
DATA_CATEGORIES = {
    "identity":   ["auth",      "users table — name, email, phone"],
    "transactional":["payment", "bookings, payments, invoices"],
    "behavioral": ["analytics", "event stream, session data"],
    "location":   ["geo",       "service addresses, staff locations"],
    "communication":["chat",    "messages, notification history"],
    "reviews":    ["review",    "ratings, comments"],
}

# ── Exemptions from erasure (legally must retain) ─────────────────────────
# PROVEN: exemption_reason stored per deletion record row
ERASURE_EXEMPTIONS = {
    "payment_records":       "GST Act — 7 year retention required",
    "invoice_records":       "GST Act — 7 year retention required",
    "commission_records":    "GST Act — 7 year retention required",
    "platform_audit_logs":   "Security audit — 2 year retention required",
    "subscription_periods":  "Financial record — 7 year retention required",
}

# ── Retention policies (days) ─────────────────────────────────────────────
DEFAULT_RETENTION_POLICIES = {
    "analytics_events":       365,     # 1 year
    "session_inventory":       90,     # 90 days
    "notification_records":   180,     # 6 months
    "suspicious_activity_logs": 730,   # 2 years
    "chat_messages":          365,     # 1 year
    "job_status_history":     1825,    # 5 years
}

# ── Redis keys ─────────────────────────────────────────────────────────────
REDIS_CONSENT_CACHE       = "serviceos:compliance:consent:{user_id}:{consent_type}"
REDIS_DELETION_LOCK       = "serviceos:compliance:deletion_lock:{user_id}"
REDIS_EXPORT_STATUS       = "serviceos:compliance:export:{request_id}"
