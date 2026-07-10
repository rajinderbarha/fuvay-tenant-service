"""Sprint 29 — AIResponseValidationService.

Validates the structured JSON output from DeepSeek against the AI safety contract.

Contract:
{
  "intent": "home_service_booking",
  "confidence": 0.91,
  "customer_message": "...",
  "required_next_action": "ask_question",
  "collected_fields": {},
  "missing_fields": [],
  "backend_action_request": {
    "action": "update_draft",
    "draft_type": "home_service_booking",
    "payload": {}
  },
  "safety": {
    "contains_price_claim": false,
    "contains_provider_claim": false,
    "needs_backend_validation": true
  }
}
"""
from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.engines.ai_conversation.sprint29_constants import (
    ALLOWED_BACKEND_ACTIONS,
    ALLOWED_NEXT_ACTIONS,
    BLOCKED_AI_ACTIONS,
    PRICE_CLAIM_PATTERNS,
    PROVIDER_CLAIM_PATTERNS,
    AI_CONTRACT_REQUIRED_KEYS,
    AI_SAFE_FALLBACK_MESSAGE,
    AI_ACTION_BLOCKED,
    AI_ACTION_FAILED,
    ERR_AI_RESPONSE_INVALID,
    ERR_AI_ACTION_BLOCKED,
)
from app.engines.ai_conversation.constants import VALID_INTENTS

logger = structlog.get_logger("ai_conversation.validation")


class AIResponseValidationService:
    """Validates and sanitizes the structured AI response contract."""

    # ── 1. Validate schema ────────────────────────────────────────────────────

    def validate_ai_response_schema(self, raw_response: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Check that required keys are present and types are correct.
        Returns (is_valid, list_of_errors).
        """
        errors: list[str] = []

        for key in AI_CONTRACT_REQUIRED_KEYS:
            if key not in raw_response:
                errors.append(f"Missing required key: {key}")

        # Type checks on optional but important fields
        if "confidence" in raw_response:
            try:
                conf = float(raw_response["confidence"])
                if not 0.0 <= conf <= 1.0:
                    errors.append("confidence must be 0.0–1.0")
            except (TypeError, ValueError):
                errors.append("confidence must be a number")

        if "required_next_action" in raw_response:
            if raw_response["required_next_action"] not in ALLOWED_NEXT_ACTIONS:
                errors.append(
                    f"required_next_action '{raw_response['required_next_action']}' not in allowed set"
                )

        if "backend_action_request" in raw_response:
            bar = raw_response["backend_action_request"]
            if not isinstance(bar, dict):
                errors.append("backend_action_request must be a dict")
            elif "action" in bar and bar["action"] not in (ALLOWED_BACKEND_ACTIONS | BLOCKED_AI_ACTIONS):
                errors.append(f"backend_action_request.action '{bar['action']}' is unknown")

        return len(errors) == 0, errors

    # ── 2. Validate intent ────────────────────────────────────────────────────

    def validate_allowed_intent(self, intent: str) -> bool:
        return intent in VALID_INTENTS or intent in {
            "home_service_booking", "coaching_appointment",
            "real_estate_lead", "unsupported",
        }

    # ── 3. Validate backend action ────────────────────────────────────────────

    def validate_allowed_backend_action(self, action: str) -> tuple[bool, str | None]:
        """
        Returns (is_allowed, failure_code).
        BLOCKED_AI_ACTIONS are never allowed regardless of other validation.
        """
        if action in BLOCKED_AI_ACTIONS:
            logger.warning("ai_validation.blocked_action", action=action)
            return False, ERR_AI_ACTION_BLOCKED
        if action not in ALLOWED_BACKEND_ACTIONS:
            return False, ERR_AI_RESPONSE_INVALID
        return True, None

    # ── 4. Detect forbidden claims ────────────────────────────────────────────

    def detect_forbidden_claims(self, response: dict[str, Any]) -> dict[str, list[str]]:
        """
        Scan customer_message for hallucinated price/provider claims.
        Returns {"price_claims": [...], "provider_claims": [...]}.
        """
        message = response.get("customer_message", "")
        lower   = message.lower()

        price_hits    = [p for p in PRICE_CLAIM_PATTERNS    if re.search(p, lower)]
        provider_hits = [p for p in PROVIDER_CLAIM_PATTERNS if re.search(p, lower)]

        if price_hits:
            logger.warning("ai_validation.price_claim_detected", patterns=price_hits,
                           preview=message[:80])
        if provider_hits:
            logger.warning("ai_validation.provider_claim_detected", patterns=provider_hits,
                           preview=message[:80])

        return {"price_claims": price_hits, "provider_claims": provider_hits}

    # ── 5. Validate required fields for flow ──────────────────────────────────

    def validate_required_fields_for_flow(
        self, intent: str, collected_fields: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Check that collected_fields contains the minimum required for the flow.
        Returns (is_complete, list_of_missing_fields).
        """
        required_map: dict[str, list[str]] = {
            "home_service_booking": ["city"],
            "coaching_appointment": ["student_name", "target_exam"],
            "real_estate_lead":     ["lead_intent", "city"],
        }
        required = required_map.get(intent, [])
        missing  = [f for f in required if not collected_fields.get(f)]
        return len(missing) == 0, missing

    # ── 6. Sanitize customer message ──────────────────────────────────────────

    def sanitize_customer_message(self, message: str) -> str:
        """
        Replace hallucinated price figures with a safe placeholder.
        Provider claims are replaced with a backend-routing message.
        """
        # Replace ₹NNN / Rs NNN patterns with a safe placeholder
        sanitized = re.sub(
            r"(₹|rs\.?|inr)\s*[\d,]+(\.\d+)?",
            "[price from backend]",
            message,
            flags=re.IGNORECASE,
        )
        # Replace explicit provider assignment claims
        sanitized = re.sub(
            r"(i have assigned|your technician is|booked with)\s+[a-z ]+",
            "our team will assign the right professional",
            sanitized,
            flags=re.IGNORECASE,
        )
        return sanitized

    # ── 7. Build safe fallback response ───────────────────────────────────────

    def build_safe_fallback_response(self, error: str | None = None) -> dict[str, Any]:
        """Return a safe structured response when AI output is invalid/blocked."""
        return {
            "intent":                 "unknown",
            "confidence":             0.0,
            "customer_message":       AI_SAFE_FALLBACK_MESSAGE,
            "required_next_action":   "error_recovery",
            "collected_fields":       {},
            "missing_fields":         [],
            "backend_action_request": {"action": "none", "draft_type": None, "payload": {}},
            "safety": {
                "contains_price_claim":    False,
                "contains_provider_claim": False,
                "needs_backend_validation": True,
                "fallback_reason":         error or ERR_AI_RESPONSE_INVALID,
            },
            "_is_fallback": True,
        }

    # ── Full validation pipeline ──────────────────────────────────────────────

    def validate_and_sanitize(
        self, raw_response: dict[str, Any]
    ) -> tuple[dict[str, Any], bool, list[str]]:
        """
        Full pipeline: schema → action → claims → sanitize.
        Returns (final_response, is_safe, list_of_violations).
        """
        violations: list[str] = []

        # 1. Schema
        is_valid, schema_errors = self.validate_ai_response_schema(raw_response)
        if not is_valid:
            return self.build_safe_fallback_response("; ".join(schema_errors)), False, schema_errors

        # 2. Backend action
        bar    = raw_response.get("backend_action_request") or {}
        action = bar.get("action", ALLOWED_BACKEND_ACTIONS.__iter__().__next__())
        if action:
            allowed, fail_code = self.validate_allowed_backend_action(action)
            if not allowed:
                violations.append(f"blocked_action:{action}")
                blocked = self.build_safe_fallback_response(fail_code)
                return blocked, False, violations

        # 3. Forbidden claims
        claims = self.detect_forbidden_claims(raw_response)
        if claims["price_claims"] or claims["provider_claims"]:
            violations.extend(claims["price_claims"] + claims["provider_claims"])
            # Sanitize rather than full block — message continues but safe
            raw_response = dict(raw_response)
            raw_response["customer_message"] = self.sanitize_customer_message(
                raw_response.get("customer_message", "")
            )
            if raw_response.get("safety") and isinstance(raw_response["safety"], dict):
                raw_response["safety"]["contains_price_claim"]    = bool(claims["price_claims"])
                raw_response["safety"]["contains_provider_claim"] = bool(claims["provider_claims"])

        return raw_response, len(violations) == 0, violations
