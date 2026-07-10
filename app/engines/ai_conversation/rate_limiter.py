"""Sprint 29 — AI Rate Limiter (in-process, Redis-free).

Uses a simple in-memory counter dict keyed by customer_id.
For production, swap the store for Redis with TTL.

Rules:
- MAX 10 messages per customer per minute
- MAX 5 new sessions per customer per hour
- MAX 8000 chars prompt input
- MAX 4000 chars AI response
- After 5 consecutive failures → 10-minute cooldown
"""
from __future__ import annotations
import time
from collections import defaultdict
from threading import Lock
from typing import Any

import structlog

from app.engines.ai_conversation.sprint29_constants import (
    AI_RATE_LIMIT_MESSAGES_PER_MINUTE,
    AI_RATE_LIMIT_SESSIONS_PER_HOUR,
    AI_MAX_PROMPT_CHARS,
    AI_MAX_RESPONSE_CHARS,
    AI_FAILURE_COOLDOWN_COUNT,
    AI_FAILURE_COOLDOWN_MINUTES,
    ERR_AI_RATE_LIMIT_EXCEEDED,
    ERR_AI_PROMPT_TOO_LARGE,
)

logger = structlog.get_logger("ai_conversation.rate_limiter")

# ── In-process store ──────────────────────────────────────────────────────────
_lock           = Lock()
_msg_windows:   dict[str, list[float]] = defaultdict(list)   # customer_id → [timestamps]
_sess_windows:  dict[str, list[float]] = defaultdict(list)   # customer_id → [timestamps]
_failure_counts: dict[str, int]         = defaultdict(int)
_cooldown_until: dict[str, float]       = defaultdict(float)


def _purge(timestamps: list[float], window_seconds: float, now: float) -> list[float]:
    return [t for t in timestamps if now - t < window_seconds]


class AIRateLimiter:
    """Singleton-safe rate limiter for AI operations."""

    # ── Check message rate ────────────────────────────────────────────────────

    def check_message_rate(self, customer_id: str) -> tuple[bool, str | None]:
        """
        Allow up to AI_RATE_LIMIT_MESSAGES_PER_MINUTE messages per minute.
        Returns (is_allowed, error_code).
        """
        now = time.monotonic()
        key = str(customer_id)

        with _lock:
            # Cooldown check
            if _cooldown_until[key] > now:
                remaining = int(_cooldown_until[key] - now)
                logger.warning("ai_rate_limiter.cooldown_active",
                               customer_id=key, remaining_seconds=remaining)
                return False, ERR_AI_RATE_LIMIT_EXCEEDED

            window = _purge(_msg_windows[key], 60.0, now)
            if len(window) >= AI_RATE_LIMIT_MESSAGES_PER_MINUTE:
                logger.warning("ai_rate_limiter.message_rate_exceeded", customer_id=key)
                return False, ERR_AI_RATE_LIMIT_EXCEEDED

            window.append(now)
            _msg_windows[key] = window
            return True, None

    # ── Check session creation rate ───────────────────────────────────────────

    def check_session_rate(self, customer_id: str) -> tuple[bool, str | None]:
        """Allow up to AI_RATE_LIMIT_SESSIONS_PER_HOUR new sessions per hour."""
        now = time.monotonic()
        key = str(customer_id)

        with _lock:
            window = _purge(_sess_windows[key], 3600.0, now)
            if len(window) >= AI_RATE_LIMIT_SESSIONS_PER_HOUR:
                logger.warning("ai_rate_limiter.session_rate_exceeded", customer_id=key)
                return False, ERR_AI_RATE_LIMIT_EXCEEDED

            window.append(now)
            _sess_windows[key] = window
            return True, None

    # ── Validate prompt size ──────────────────────────────────────────────────

    def check_prompt_size(self, prompt: str) -> tuple[bool, str | None]:
        if len(prompt) > AI_MAX_PROMPT_CHARS:
            logger.warning("ai_rate_limiter.prompt_too_large", size=len(prompt))
            return False, ERR_AI_PROMPT_TOO_LARGE
        return True, None

    # ── Validate response size ────────────────────────────────────────────────

    def check_response_size(self, response: str) -> bool:
        return len(response) <= AI_MAX_RESPONSE_CHARS

    # ── Record failure + trigger cooldown ─────────────────────────────────────

    def record_failure(self, customer_id: str) -> None:
        key = str(customer_id)
        with _lock:
            _failure_counts[key] += 1
            if _failure_counts[key] >= AI_FAILURE_COOLDOWN_COUNT:
                _cooldown_until[key] = time.monotonic() + (AI_FAILURE_COOLDOWN_MINUTES * 60)
                _failure_counts[key] = 0
                logger.warning("ai_rate_limiter.cooldown_set", customer_id=key,
                               minutes=AI_FAILURE_COOLDOWN_MINUTES)

    # ── Reset on success ──────────────────────────────────────────────────────

    def record_success(self, customer_id: str) -> None:
        key = str(customer_id)
        with _lock:
            _failure_counts[key] = 0

    # ── Stats (for admin metrics) ─────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        now = time.monotonic()
        with _lock:
            return {
                "active_customers_in_msg_window": sum(
                    1 for k, v in _msg_windows.items() if _purge(v, 60.0, now)
                ),
                "customers_in_cooldown": sum(
                    1 for v in _cooldown_until.values() if v > now
                ),
            }


# Module-level singleton
_rate_limiter = AIRateLimiter()


def get_rate_limiter() -> AIRateLimiter:
    return _rate_limiter
