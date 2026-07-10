"""
AI Chat Engine — AIChatService
Orchestrates DeepSeek LLM calls + tool execution loop.
DeepSeek is OpenAI-API-compatible; we use httpx directly (already a project dep).
"""
from __future__ import annotations
import json
import uuid
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.engines.ai_chat.constants import (
    DEEPSEEK_API_BASE, DEEPSEEK_MODEL, DEEPSEEK_MAX_TOKENS,
    DEEPSEEK_TEMPERATURE, MAX_TOOL_ITERATIONS, SYSTEM_PROMPT, TOOLS,
)
from app.engines.ai_chat.tools import ToolExecutor
from app.exceptions import ServiceOSException

logger = structlog.get_logger("ai_chat.service")


class AIChatService:
    """
    Manages one conversational turn with the DeepSeek LLM.
    Flow:
      1. Build messages with system prompt + history + new user message
      2. Call DeepSeek /chat/completions
      3. If tool_calls in response → execute each via ToolExecutor → loop
      4. Return final assistant text reply
    """

    def __init__(self, db: AsyncSession, customer_id: uuid.UUID,
                 request_id: str = "—"):
        self.db          = db
        self.customer_id = customer_id
        self.request_id  = request_id
        self.api_key     = get_settings().DEEPSEEK_API_KEY
        self.executor    = ToolExecutor(db=db, customer_id=customer_id)

    # ── Public API ────────────────────────────────────────────────────────────
    async def chat(
        self,
        user_message: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        Process one customer message and return the AI reply.
        Args:
            user_message: The latest message from the customer.
            history:      Previous [{role, content}] turns (max 20).
        Returns:
            {"reply": str, "tools_called": [str]}
        """
        if not self.api_key:
            raise ServiceOSException(
                "DEEPSEEK_NOT_CONFIGURED",
                "AI assistant is not configured. Please set DEEPSEEK_API_KEY.",
                status_code=503,
            )

        # Build message list
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in (history or [])[-20:]:   # cap history at 20 turns
            if turn.get("role") in ("user", "assistant"):
                messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message.strip()})

        tools_called: list[str] = []

        # ── Tool-calling loop ─────────────────────────────────────────────────
        for iteration in range(MAX_TOOL_ITERATIONS):
            response = await self._call_deepseek(messages)
            choice   = response["choices"][0]
            msg      = choice["message"]

            # Add assistant message to history
            messages.append(msg)

            # No tool calls → we have the final answer
            if not msg.get("tool_calls"):
                reply = msg.get("content") or ""
                logger.info("ai_chat.reply", request_id=self.request_id,
                            turns=iteration + 1, tools=tools_called)
                return {"reply": reply, "tools_called": tools_called}

            # Execute each tool call
            for tc in msg["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"] or "{}")
                tools_called.append(fn_name)

                logger.info("ai_chat.tool_call", tool=fn_name,
                            request_id=self.request_id, iteration=iteration)

                result = await self.executor.execute(fn_name, fn_args)

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "name":         fn_name,
                    "content":      result,
                })

        # Safety fallback if we exhaust iterations
        return {
            "reply":       "I'm sorry, I couldn't complete that request. Please try again or contact our support team.",
            "tools_called": tools_called,
        }

    # ── Private helpers ───────────────────────────────────────────────────────
    async def _call_deepseek(self, messages: list[dict]) -> dict[str, Any]:
        """POST to DeepSeek /chat/completions and return parsed JSON."""
        payload = {
            "model":       DEEPSEEK_MODEL,
            "messages":    messages,
            "tools":       TOOLS,
            "tool_choice": "auto",
            "max_tokens":  DEEPSEEK_MAX_TOKENS,
            "temperature": DEEPSEEK_TEMPERATURE,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{DEEPSEEK_API_BASE}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type":  "application/json",
                    },
                    json=payload,
                )
            if r.status_code != 200:
                raise ServiceOSException(
                    "DEEPSEEK_API_ERROR",
                    f"DeepSeek returned HTTP {r.status_code}",
                    status_code=502,
                    context={"body": r.text[:500]},
                )
            return r.json()
        except httpx.TimeoutException:
            raise ServiceOSException(
                "DEEPSEEK_TIMEOUT",
                "AI assistant timed out. Please try again.",
                status_code=504,
            )
        except httpx.RequestError as e:
            raise ServiceOSException(
                "DEEPSEEK_UNREACHABLE",
                "AI assistant is temporarily unavailable.",
                status_code=503,
                context={"error": str(e)},
            )
