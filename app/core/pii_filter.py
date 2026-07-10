"""
ServiceOS — Structlog PII Filter
Masks sensitive fields in all log output before emission.
Applied as a structlog processor — works for console + JSON renderers.
"""
from __future__ import annotations
import re

# Field names whose VALUES should be masked
_MASK_KEYS = frozenset({
    "password", "token", "access_token", "refresh_token", "secret",
    "authorization", "phone", "email", "aadhaar", "pan", "api_key",
    "otp", "cvv", "card_number", "account_number", "ifsc",
    "deepseek_api_key", "sentry_dsn", "secret_key",
})

# Regex patterns for values that look like secrets (even in unknown keys)
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),        # DeepSeek / OpenAI keys
    re.compile(r"Bearer [A-Za-z0-9._-]{20,}"),  # Bearer tokens
    re.compile(r"\b[6-9]\d{9}\b"),           # Indian phone numbers
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # Email
]

MASK = "***"


def mask_pii_processor(logger, method, event_dict: dict) -> dict:
    """
    Structlog processor that masks PII in log events.
    Add to structlog.configure(processors=[..., mask_pii_processor, ...]).
    """
    return _walk(event_dict)


def _walk(obj):
    if isinstance(obj, dict):
        return {k: MASK if k.lower() in _MASK_KEYS else _walk(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(i) for i in obj]
    if isinstance(obj, str):
        return _mask_patterns(obj)
    return obj


def _mask_patterns(value: str) -> str:
    for pat in _SECRET_PATTERNS:
        value = pat.sub(MASK, value)
    return value
