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

# Roles hierarchy
ROLES = ["super_admin", "tenant_owner", "staff", "customer", "guest"]
ROLE_HIERARCHY = {
    "super_admin": 4,
    "tenant_owner": 3,
    "staff": 2,
    "customer": 1,
    "guest": 0,
}

# Token audience per app
AUDIENCE = {
    "super_admin": "serviceos:admin",
    "tenant_owner": "serviceos:tenant",
    "staff": "serviceos:staff",
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
