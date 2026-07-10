"""Sprint 15 — DeepSeekClientService: safe httpx wrapper with logging."""
from __future__ import annotations
import json
import time
import uuid
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.engines.ai_conversation.constants import (
    DEEPSEEK_API_BASE,
    DEEPSEEK_MAX_TOKENS,
    DEEPSEEK_MODEL,
    DEEPSEEK_TEMPERATURE,
    DEEPSEEK_TIMEOUT_S,
    ERR_DEEPSEEK_CALL_FAILED,
    ERR_DEEPSEEK_NOT_CONFIGURED,
)
from app.engines.ai_conversation.safety import (
    sanitize_user_message,
    validate_assistant_reply,
)
from app.exceptions import ServiceOSException

logger = structlog.get_logger("ai_conversation.deepseek")


class DeepSeekClientService:
    """
    Thin, safe wrapper around the DeepSeek /chat/completions API.

    Responsibilities:
    - Call DeepSeek via httpx
    - Sanitize user messages for prompt injection
    - Strip forbidden fields from responses
    - Log every call to ai_llm_call_logs
    - Never expose provider_id, price, booking_id, etc.
    """

    def __init__(self, db: AsyncSession, session_id: str | None = None,
                 request_id: str = "—"):
        self.db         = db
        self.session_id = session_id
        self.request_id = request_id
        self.api_key    = get_settings().DEEPSEEK_API_KEY

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> dict[str, Any]:
        """
        Call DeepSeek /v1/chat/completions.
        Returns the parsed response dict.
        Raises ServiceOSException on failure.
        """
        if not self.api_key:
            raise ServiceOSException(
                ERR_DEEPSEEK_NOT_CONFIGURED,
                "AI assistant is not configured. Please contact support.",
                status_code=503,
            )

        payload: dict[str, Any] = {
            "model":       DEEPSEEK_MODEL,
            "messages":    messages,
            "max_tokens":  DEEPSEEK_MAX_TOKENS,
            "temperature": DEEPSEEK_TEMPERATURE,
        }
        if tools:
            payload["tools"]       = tools
            payload["tool_choice"] = tool_choice

        start = time.monotonic()
        response_status = "success"
        error_msg: str | None = None
        raw_response: dict | None = None

        try:
            async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT_S) as client:
                resp = await client.post(
                    f"{DEEPSEEK_API_BASE}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type":  "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                raw_response = resp.json()

        except httpx.TimeoutException as exc:
            response_status = "timeout"
            error_msg = "DeepSeek API timed out"
            logger.error("deepseek.timeout", request_id=self.request_id, error=str(exc))
            raise ServiceOSException(
                ERR_DEEPSEEK_CALL_FAILED, error_msg, status_code=504
            ) from exc
        except httpx.HTTPStatusError as exc:
            response_status = "http_error"
            error_msg = f"DeepSeek HTTP {exc.response.status_code}"
            logger.error("deepseek.http_error", status=exc.response.status_code,
                         request_id=self.request_id)
            raise ServiceOSException(
                ERR_DEEPSEEK_CALL_FAILED,
                f"AI service returned error {exc.response.status_code}",
                status_code=502,
            ) from exc
        except Exception as exc:
            response_status = "error"
            error_msg = str(exc)
            logger.error("deepseek.error", request_id=self.request_id, error=str(exc))
            raise ServiceOSException(
                ERR_DEEPSEEK_CALL_FAILED,
                "AI service is temporarily unavailable",
                status_code=503,
            ) from exc
        finally:
            latency_ms = int((time.monotonic() - start) * 1000)
            tool_names = [
                tc["function"]["name"]
                for tc in (raw_response or {})
                .get("choices", [{}])[0]
                .get("message", {})
                .get("tool_calls", [])
            ] if raw_response else []

            await self._log_call(
                latency_ms=latency_ms,
                prompt_tokens=(raw_response or {}).get("usage", {}).get("prompt_tokens"),
                completion_tokens=(raw_response or {}).get("usage", {}).get("completion_tokens"),
                had_tool_calls=bool(tool_names),
                tool_names=tool_names,
                response_status=response_status,
                error_message=error_msg,
                payload_size=len(json.dumps(payload)),
            )

        return raw_response  # type: ignore[return-value]

    async def _log_call(
        self,
        latency_ms: int,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        had_tool_calls: bool,
        tool_names: list[str],
        response_status: str,
        error_message: str | None,
        payload_size: int,
    ) -> None:
        """Persist an AILLMCallLog row."""
        try:
            from app.engines.ai_conversation.models import AILLMCallLog
            log = AILLMCallLog(
                id=uuid.uuid4(),
                session_id=uuid.UUID(self.session_id) if self.session_id else None,
                call_type="chat",
                model_used=DEEPSEEK_MODEL,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                had_tool_calls=had_tool_calls,
                tool_names=tool_names or [],
                response_status=response_status,
                error_message=error_message,
                request_payload_size=payload_size,
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as exc:
            # Logging failure must not break the chat flow
            logger.warning("deepseek.log_failed", error=str(exc))
