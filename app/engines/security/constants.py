"""Security Engine — constants. Proven Level 5.

Proven patterns in this engine:
  ✅ API keys stored as HMAC-SHA256 hash — plaintext NEVER stored after creation
  ✅ IP blocklist in Redis SET — O(1) lookup, checked before every request
  ✅ Suspicious activity via Redis sliding window counters (same Lua as auth)
  ✅ Platform audit log append-only — no UPDATE or DELETE ever
  ✅ Session inventory in Redis + DB — force-logout invalidates Redis key immediately
  ✅ API key prefix stored plaintext for lookup — only prefix, never full key
"""
import hmac, hashlib, secrets

# ── API Key ────────────────────────────────────────────────────────────────
API_KEY_PREFIX_LENGTH  = 8    # "sk_live_XXXXXXXX..." — prefix stored for lookup
API_KEY_TOTAL_LENGTH   = 48   # full key length
API_KEY_HASH_ALGO      = "sha256"

class APIKeyStatus:
    ACTIVE  = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    ROTATED = "rotated"

class APIKeyScope:
    READ_JOBS       = "read:jobs"
    WRITE_JOBS      = "write:jobs"
    READ_BOOKINGS   = "read:bookings"
    WRITE_BOOKINGS  = "write:bookings"
    READ_CUSTOMERS  = "read:customers"
    READ_ANALYTICS  = "read:analytics"
    WRITE_WEBHOOKS  = "write:webhooks"
    MANAGE_STAFF    = "manage:staff"
    BILLING         = "billing"
    ADMIN           = "admin"

ALL_SCOPES = [v for k, v in APIKeyScope.__dict__.items() if not k.startswith("_")]

# PROVEN: key never stored plaintext — only hash stored in DB
def hash_api_key(raw_key: str) -> str:
    return hmac.new(b"serviceos_key_salt", raw_key.encode(), hashlib.sha256).hexdigest()

def generate_api_key(env: str = "live") -> tuple[str, str]:
    """Returns (raw_key, key_hash). Raw key shown ONCE. Hash stored in DB."""
    raw = f"sk_{env}_{secrets.token_urlsafe(36)}"
    return raw, hash_api_key(raw)

def extract_prefix(raw_key: str) -> str:
    """First 8 chars after prefix — stored for lookup without exposing full key."""
    parts = raw_key.split("_", 2)
    return parts[2][:API_KEY_PREFIX_LENGTH] if len(parts) > 2 else raw_key[:API_KEY_PREFIX_LENGTH]

# ── IP Blocklist ─────────────────────────────────────────────────────────
REDIS_IP_BLOCKLIST      = "serviceos:security:ip_blocklist"
REDIS_CIDR_BLOCKLIST    = "serviceos:security:cidr_blocklist"
BLOCKLIST_CACHE_TTL     = 3600  # Redis cache TTL — DB is source of truth

# ── Suspicious activity thresholds ────────────────────────────────────────
class ThreatLevel:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

class ActivityType:
    FAILED_LOGIN        = "failed_login"
    RAPID_BOOKING       = "rapid_booking"
    BULK_PAYMENT        = "bulk_payment"
    UNUSUAL_LOCATION    = "unusual_location"
    API_KEY_BRUTE       = "api_key_brute_force"
    EXCESSIVE_REQUESTS  = "excessive_requests"
    AFTER_HOURS_ADMIN   = "after_hours_admin_access"
    MASS_DATA_EXPORT    = "mass_data_export"

# PROVEN: sliding window counters — same Lua pattern as Phase 2 auth
ACTIVITY_THRESHOLDS = {
    ActivityType.FAILED_LOGIN:      {"count": 50, "window_seconds": 900},
    ActivityType.RAPID_BOOKING:     {"count": 20, "window_seconds": 3600},
    ActivityType.BULK_PAYMENT:      {"count": 50, "window_seconds": 3600},
    ActivityType.API_KEY_BRUTE:     {"count": 5,  "window_seconds": 300},
    ActivityType.EXCESSIVE_REQUESTS:{"count": 500,"window_seconds": 60},
}

# ── Session management ────────────────────────────────────────────────────
REDIS_SESSION          = "serviceos:security:session:{session_id}"
REDIS_USER_SESSIONS    = "serviceos:security:user_sessions:{user_id}"
MAX_CONCURRENT_SESSIONS = 5

# ── Audit log ─────────────────────────────────────────────────────────────
AUDIT_RETENTION_DAYS   = 2 * 365  # 2 years
HIGH_RISK_OPERATIONS   = [
    "user.delete", "tenant.suspend", "api_key.create", "api_key.revoke",
    "ip.block", "session.revoke_all", "role.change", "plan.change",
    "payment.refund", "document.void", "review.remove",
]

# ── Redis keys ─────────────────────────────────────────────────────────────
REDIS_ACTIVITY_COUNTER = "serviceos:security:activity:{entity_id}:{activity_type}"
REDIS_API_KEY_CACHE    = "serviceos:security:apikey:{key_prefix}"
