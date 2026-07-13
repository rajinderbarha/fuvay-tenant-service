"""Auth Engine — constants and configuration values."""

# Token settings
ACCESS_TOKEN_EXPIRE_MINUTES = 480
REFRESH_TOKEN_EXPIRE_DAYS = 7
MFA_CHALLENGE_TOKEN_EXPIRE_MINUTES = 5
IMPERSONATION_TOKEN_EXPIRE_MINUTES = 60
GUEST_SESSION_EXPIRE_HOURS = 2

# OTP
OTP_EXPIRE_MINUTES = 10
OTP_MAX_ATTEMPTS = 3
OTP_SEND_RATE_LIMIT_PER_HOUR = 3

# Account lockout
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
HARD_LOCKOUT_ATTEMPTS = 10

# Password
BCRYPT_ROUNDS = 12
PASSWORD_HISTORY_COUNT = 5
MIN_PASSWORD_LENGTH = 8

# MFA backup codes
BACKUP_CODE_COUNT = 8

# API key
API_KEY_PREFIX_LIVE = "svc_live_"
API_KEY_PREFIX_TEST = "svc_test_"
API_KEY_RANDOM_BYTES = 32

# Rate limits
LOGIN_RATE_LIMIT_ATTEMPTS = 100
LOGIN_RATE_LIMIT_WINDOW_MINUTES = 15

# ── Canonical system-role vocabulary ──────────────────────────────────────────
# MODULE-L5-01D (BLK-01D-1 decision, Option A): the single authoritative role
# registry is app/core/permissions.py::ROLE_PERMISSIONS. These constants are a
# convenience mirror of that enforced set and MUST stay in sync with it (the
# canonical_role_registry_guard enforces this). This list was previously a stale
# 5-role vocabulary (missing `technician` and the four least-privilege platform
# admin roles), which MODULE-L5-01C flagged as a competing registry. It is now
# reconciled to the enforced canonical set. Scope/authority is NOT defined here —
# it lives in ROLE_PERMISSIONS; this is only names + advisory audience/hierarchy.
ROLES = [
    "super_admin",
    "admin_operations",
    "admin_finance",
    "admin_security",
    "admin_readonly",
    "tenant_owner",
    "staff",
    "technician",
    "customer",
    "guest",
]

# Advisory only (no authorization decision is made from this map; canonical
# authority is permissions.py). Platform-scoped admin roles rank below super_admin
# and above tenant roles; scope (platform vs tenant) — not this linear rank — is
# the real boundary and is enforced in permissions.py / require_platform_staff.
ROLE_HIERARCHY = {
    "super_admin": 4,
    "admin_security": 3,
    "admin_finance": 3,
    "admin_operations": 3,
    "admin_readonly": 3,
    "tenant_owner": 3,
    "staff": 2,
    "technician": 2,
    "customer": 1,
    "guest": 0,
}

# Token audience per app. Consumed by utils.create_access_token via
# AUDIENCE.get(role, "serviceos:customer"). Before this sprint `technician` and
# the four admin_* roles were absent and silently fell back to the CUSTOMER
# audience on their tokens; they are added here so each role's token carries a
# correct audience. (decode_token uses verify_aud=False, so this is a
# correctness/clarity fix, not a validation-behavior change.)
AUDIENCE = {
    "super_admin": "serviceos:admin",
    "admin_operations": "serviceos:admin",
    "admin_finance": "serviceos:admin",
    "admin_security": "serviceos:admin",
    "admin_readonly": "serviceos:admin",
    "tenant_owner": "serviceos:tenant",
    "staff": "serviceos:staff",
    "technician": "serviceos:staff",
    "customer": "serviceos:customer",
    "guest": "serviceos:customer",
}

# Redis key prefixes
REDIS_BLACKLIST_PREFIX = "serviceos:auth:blacklist:"
REDIS_LOCKOUT_PREFIX = "serviceos:auth:lockout:"
REDIS_FAILED_ATTEMPTS_PREFIX = "serviceos:auth:failed:"
REDIS_OTP_PREFIX = "serviceos:otp:"
REDIS_MFA_CHALLENGE_PREFIX = "serviceos:mfa:challenge:"
REDIS_IMPERSONATION_PREFIX = "serviceos:impersonation:"
