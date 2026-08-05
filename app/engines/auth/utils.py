"""
Auth Engine — Utilities
JWT encode/decode, password hashing, OTP generation, device fingerprinting
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.engines.auth.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    API_KEY_PREFIX_LIVE,
    API_KEY_PREFIX_TEST,
    API_KEY_RANDOM_BYTES,
    BCRYPT_ROUNDS,
    BACKUP_CODE_COUNT,
    MFA_CHALLENGE_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    IMPERSONATION_TOKEN_EXPIRE_MINUTES,
    AUDIENCE,
)

# ── Password ──────────────────────────────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=BCRYPT_ROUNDS,
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    # A malformed/unidentifiable stored hash (corrupt seed data, a bad
    # migration, manual DB tampering) must fail auth cleanly, never crash
    # the request with a raw 500 -- found live during this pass: a seeded
    # technician's hashed_password wasn't a real passlib hash and every
    # login attempt for that account 500'd instead of returning 401.
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

_SPECIAL_CHARS = set(r"""!@#$%^&*()_+-=[]{}|;':",.<>?/`~\\""")

def validate_password_strength(password: str, user_name: str = "", user_email: str = "") -> list[str]:
    errors = []
    if len(password) < 8:
        errors.append("PASSWORD_TOO_SHORT: Password must be at least 8 characters.")
    if not any(c.isupper() for c in password):
        errors.append("PASSWORD_REQUIRES_UPPERCASE: Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        errors.append("PASSWORD_REQUIRES_LOWERCASE: Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("PASSWORD_REQUIRES_NUMBER: Password must contain at least one number.")
    if not any(c in _SPECIAL_CHARS for c in password):
        errors.append("PASSWORD_REQUIRES_SPECIAL: Password must contain at least one special character (!@#$%^&* etc.).")
    name_lower = user_name.lower()
    email_local = user_email.split("@")[0].lower() if "@" in user_email else user_email.lower()
    if name_lower and len(name_lower) > 2 and name_lower in password.lower():
        errors.append("PASSWORD_CONTAINS_NAME: Password cannot contain your name.")
    if email_local and len(email_local) > 2 and email_local in password.lower():
        errors.append("PASSWORD_CONTAINS_EMAIL: Password cannot contain your email address.")
    return errors

# ── JWT ───────────────────────────────────────────────────────────────────────
def _settings():
    return get_settings()

def create_access_token(
    user_id: str,
    email: str,
    role: str,
    tenant_id: str | None,
    tenant_name: str | None,
    plan_type: str | None,
    session_id: str,
    device_id: str,
    is_mfa_enabled: bool,
    onboarding_complete: bool,
    enabled_engines: list[str],
    extra_claims: dict | None = None,
) -> tuple[str, str]:
    """Returns (token, jti)"""
    s = _settings()
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    aud = AUDIENCE.get(role, "serviceos:customer")
    payload = {
        "sub": user_id,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": "serviceos",
        "aud": aud,
        "email": email,
        "role": role,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "plan_type": plan_type,
        "session_id": session_id,
        "device_id": device_id,
        "mfa_enabled": is_mfa_enabled,
        "onboarding_complete": onboarding_complete,
        "engines": enabled_engines,
        **(extra_claims or {}),
    }
    token = jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)
    return token, jti

def create_refresh_token() -> tuple[str, str, str]:
    """Returns (raw_token, jti, hashed_token)"""
    raw = secrets.token_urlsafe(64)
    jti = str(uuid.uuid4())
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, jti, hashed

def create_mfa_challenge_token(user_id: str, email: str) -> str:
    s = _settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=MFA_CHALLENGE_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "purpose": "mfa_challenge",
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)

def create_impersonation_token(
    impersonator_id: str,
    impersonation_session_id: str,
    target_user_id: str,
    target_email: str,
    target_role: str,
    tenant_id: str | None,
    tenant_name: str | None,
    plan_type: str | None,
    enabled_engines: list[str],
) -> tuple[str, str]:
    """Returns (token, jti). Non-refreshable. 1-hour max."""
    s = _settings()
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=IMPERSONATION_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": target_user_id,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": "serviceos",
        "aud": AUDIENCE.get(target_role, "serviceos:tenant"),
        "email": target_email,
        "role": target_role,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "plan_type": plan_type,
        "engines": enabled_engines,
        "impersonator_id": impersonator_id,
        "impersonation_session_id": impersonation_session_id,
        "is_impersonation": True,
        "session_id": impersonation_session_id,
        "device_id": "impersonation",
        "mfa_enabled": False,
        "onboarding_complete": True,
    }
    token = jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)
    return token, jti

def decode_token(token: str) -> dict:
    """Raises JWTError on invalid token."""
    s = _settings()
    return jwt.decode(
        token,
        s.JWT_SECRET_KEY,
        algorithms=[s.JWT_ALGORITHM],
        options={"verify_aud": False},
    )

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

# ── OTP ───────────────────────────────────────────────────────────────────────
def generate_otp() -> tuple[str, str]:
    """Returns (plain_otp_6_digit, hashed_otp)"""
    otp = str(secrets.randbelow(900000) + 100000)
    hashed = hashlib.sha256(otp.encode()).hexdigest()
    return otp, hashed

def verify_otp(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.encode()).hexdigest() == hashed

def hash_recipient(recipient: str) -> str:
    return hashlib.sha256(recipient.lower().encode()).hexdigest()

# ── MFA / TOTP ────────────────────────────────────────────────────────────────
def generate_totp_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str, issuer: str = "ServiceOS") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

def generate_backup_codes() -> tuple[list[str], list[str]]:
    """Returns (plain_codes, hashed_codes)"""
    plain = [secrets.token_hex(4).upper() for _ in range(BACKUP_CODE_COUNT)]
    hashed = [hashlib.sha256(c.encode()).hexdigest() for c in plain]
    return plain, hashed

def verify_backup_code(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.upper().encode()).hexdigest() == hashed

# ── API Keys ──────────────────────────────────────────────────────────────────
def generate_api_key(test_mode: bool = False) -> tuple[str, str, str]:
    """Returns (full_key, prefix_8_chars, hashed_key)"""
    prefix = API_KEY_PREFIX_TEST if test_mode else API_KEY_PREFIX_LIVE
    raw = secrets.token_urlsafe(API_KEY_RANDOM_BYTES)
    full_key = f"{prefix}{raw}"
    key_prefix = full_key[:16]
    hashed = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_prefix, hashed

def verify_api_key(full_key: str, hashed: str) -> bool:
    return hashlib.sha256(full_key.encode()).hexdigest() == hashed

# ── Device fingerprinting ─────────────────────────────────────────────────────
def parse_device_info(user_agent: str | None) -> tuple[str, str]:
    """Returns (device_name, device_type) from user agent."""
    if not user_agent:
        return "Unknown Device", "unknown"
    ua = user_agent.lower()
    if "iphone" in ua:
        return "iPhone", "mobile"
    if "ipad" in ua:
        return "iPad", "tablet"
    if "android" in ua and "mobile" in ua:
        return "Android Phone", "mobile"
    if "android" in ua:
        return "Android Tablet", "tablet"
    if "mac" in ua:
        return "Mac", "desktop"
    if "windows" in ua:
        return "Windows PC", "desktop"
    if "linux" in ua:
        return "Linux PC", "desktop"
    return "Unknown Device", "unknown"
