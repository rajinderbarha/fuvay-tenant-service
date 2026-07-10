"""Sprint 15 — AI Safety: forbidden field stripping + prompt injection detection."""
from __future__ import annotations
import json
import re
from typing import Any

import structlog

from app.engines.ai_conversation.constants import (
    FORBIDDEN_OUTPUT_FIELDS,
    FORBIDDEN_PROMPT_PATTERNS,
    AUDIT_SAFETY_VIOLATION,
    AUDIT_FORBIDDEN_FIELD,
    AUDIT_PROMPT_INJECTION,
    SEVERITY_WARNING,
    SEVERITY_ERROR,
)

logger = structlog.get_logger("ai_conversation.safety")


def detect_prompt_injection(text: str) -> list[str]:
    """Return list of detected injection patterns (empty = safe)."""
    lower = text.lower()
    return [p for p in FORBIDDEN_PROMPT_PATTERNS if p in lower]


def strip_forbidden_fields(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Recursively remove forbidden fields from a dict.
    Returns (cleaned_dict, list_of_stripped_field_names).
    """
    stripped: list[str] = []

    def _clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k in FORBIDDEN_OUTPUT_FIELDS:
                    stripped.append(k)
                    logger.warning("ai_safety.field_stripped", field=k)
                else:
                    result[k] = _clean(v)
            return result
        if isinstance(obj, list):
            return [_clean(item) for item in obj]
        return obj

    cleaned = _clean(data)
    return cleaned, stripped


def validate_assistant_reply(reply: str) -> tuple[str, list[str]]:
    """
    Scan assistant text reply for forbidden field names embedded in JSON-like patterns.
    Strips any JSON blocks that contain forbidden fields.
    Returns (safe_reply, violations).
    """
    violations: list[str] = []

    # Check for forbidden fields in JSON code blocks
    json_block_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
    inline_json_pattern = re.compile(r"(\{[^{}]*\})", re.DOTALL)

    def _sanitize_json_text(match: re.Match) -> str:
        raw = match.group(1) if match.lastindex else match.group(0)
        try:
            parsed = json.loads(raw)
            cleaned, found = strip_forbidden_fields(parsed)
            if found:
                violations.extend(found)
                return f"```json\n{json.dumps(cleaned, indent=2)}\n```"
        except (json.JSONDecodeError, ValueError):
            pass
        return match.group(0)

    safe_reply = json_block_pattern.sub(_sanitize_json_text, reply)
    return safe_reply, violations


def sanitize_user_message(message: str) -> tuple[str, list[str]]:
    """
    Check user message for prompt injection attempts.
    Returns (original_message, detected_patterns).
    The message is NOT modified — we log and audit but pass through.
    """
    patterns = detect_prompt_injection(message)
    if patterns:
        logger.warning("ai_safety.prompt_injection_detected",
                       patterns=patterns, message_preview=message[:100])
    return message, patterns


def build_audit_event(
    event_type: str,
    session_id: str | None,
    event_data: dict | None,
    severity: str = SEVERITY_WARNING,
) -> dict[str, Any]:
    """Build a structured audit log event dict."""
    return {
        "session_id": session_id,
        "event_type": event_type,
        "event_data": event_data or {},
        "severity":   severity,
    }
