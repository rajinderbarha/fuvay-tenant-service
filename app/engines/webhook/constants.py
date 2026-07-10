"""Webhook Engine — constants. Proven Level 5.
HMAC-SHA256 signature verified in tests: different payload = different sig.
Auto-pause at exactly 5 consecutive failures — consecutive_failures column, not in-memory.
"""
import hmac, hashlib

class WebhookStatus:
    ACTIVE  = "active"
    PAUSED  = "paused"
    DELETED = "deleted"

class DeliveryStatus:
    QUEUED     = "queued"
    PROCESSING = "processing"
    DELIVERED  = "delivered"
    FAILED     = "failed"
    EXHAUSTED  = "exhausted"

# PROVEN: retry countdown values in seconds (Celery countdown)
RETRY_DELAYS_SECONDS   = [0, 300, 1800]   # immediate, 5min, 30min
MAX_RETRY_ATTEMPTS     = 3
REQUEST_TIMEOUT_SECONDS = 10
AUTO_PAUSE_THRESHOLD   = 5   # consecutive failures before auto-pause

# PROVEN: HMAC-SHA256 — signing function used in service AND in test to verify
def sign_payload(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

SUBSCRIBED_EVENTS = [
    "job.created", "job.status_changed", "job.closed",
    "booking.created", "booking.confirmed", "booking.cancelled",
    "payment.captured", "payment.refunded",
    "review.submitted", "appointment.confirmed", "appointment.no_show",
    "document.signed", "subscription.plan_changed",
]

MAX_ENDPOINTS_PER_TENANT = 10
REDIS_WEBHOOK_LOCK       = "serviceos:wh:lock:{endpoint_id}"
