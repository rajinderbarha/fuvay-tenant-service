"""Sprint 15 — AIConversationService: persistent sessions + DeepSeek orchestration."""
from __future__ import annotations
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.ai_conversation.constants import (
    AUDIT_SESSION_CLOSE,
    AUDIT_SESSION_START,
    AUDIT_SAFETY_VIOLATION,
    AUDIT_FORBIDDEN_FIELD,
    AUDIT_PROMPT_INJECTION,
    BACKEND_TOOLS,
    BASE_SYSTEM_PROMPT,
    ERR_SESSION_NOT_FOUND,
    ERR_SESSION_CLOSED,
    ERR_SESSION_MAX_TURNS,
    ERR_TEMPLATE_NOT_FOUND,
    ERR_TEMPLATE_KEY_EXISTS,
    MAX_HISTORY_MESSAGES,
    MAX_TURNS_PER_SESSION,
    ROLE_ASSISTANT,
    ROLE_USER,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    WORKFLOW_STATUS_ACTIVE,
    WORKFLOW_STATUS_COMPLETED,
)
from app.engines.ai_conversation.backend_tools import BackendToolExecutor
from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
from app.engines.ai_conversation.models import (
    AIConversationAuditLog,
    AIConversationMessage,
    AIConversationSession,
    AILLMCallLog,
    AIPromptTemplate,
    AIToolCallLog,
)
from app.engines.ai_conversation.safety import (
    sanitize_user_message,
    validate_assistant_reply,
    strip_markdown_formatting,
)
from app.engines.ai_conversation.workflow_router import (
    AIWorkflowRouterService,
    detect_intent,
)
from app.engines.ai_conversation.regional_language import build_language_options
from app.exceptions import ServiceOSException

logger = structlog.get_logger("ai_conversation.service")


class AIConversationService:
    """
    Main service for AI conversation sessions.

    Manages session lifecycle, message persistence, DeepSeek calls,
    tool execution, safety enforcement, and admin visibility.
    """

    def _session_dict(self, session: AIConversationSession) -> dict[str, Any]:
        """session.to_dict() plus the real, backend-derived chatbot language
        options (regional_language.build_language_options) -- was never
        called anywhere, so the mobile app's LanguageSelector always
        received an empty list and rendered nothing, even though the
        customer_home capability flag advertised chatbot_language_selectable.
        """
        data = session.to_dict()
        zipcode = (session.context_data or {}).get("zipcode")
        data["language_options"] = build_language_options(zipcode)
        return data

    async def _catalog_questions_complete(self, draft_id_str: str) -> bool:
        """True only when the deterministic question-flow (question_flow_
        service.QuestionFlowService) reports no current_question left for
        this draft -- i.e. the canonical catalog question set genuinely
        owns nothing more to ask. Any failure (job type not yet resolved,
        offering unavailable, bad draft id) fails CLOSED (returns False),
        never assumes completion -- scheduling must never activate on an
        exception swallowed as "probably fine"."""
        try:
            from app.engines.home_service_booking.question_flow_service import QuestionFlowService
            qf = QuestionFlowService(db=self.db)
            envelope = await qf.get_current_question(draft_id=uuid.UUID(draft_id_str), customer_id=None)
            return envelope.get("current_question") is None
        except Exception:
            return False

    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db         = db
        self.request_id = request_id
        self.workflow   = AIWorkflowRouterService(db=db)

    # ══════════════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    async def create_session(
        self,
        customer_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        context_data: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new conversation session and return its data."""
        session_key = secrets.token_urlsafe(32)
        session = AIConversationSession(
            id=uuid.uuid4(),
            session_key=session_key,
            customer_id=customer_id,
            category_id=category_id,
            current_intent="unknown",
            workflow_status=WORKFLOW_STATUS_ACTIVE,
            collected_fields={},
            context_data=context_data or {},
            turn_count=0,
            last_activity_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self.db.add(session)
        await self.db.flush()

        await self._audit(
            session_id=str(session.id),
            event_type=AUDIT_SESSION_START,
            event_data={"category_id": str(category_id) if category_id else None},
            customer_id=customer_id,
            severity=SEVERITY_INFO,
        )
        await self.db.commit()

        logger.info("ai_conv.session_created", session_id=str(session.id),
                    request_id=self.request_id)
        return self._session_dict(session)

    async def get_session(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Get session by ID. Raises if not found."""
        session = await self._require_session(session_id)
        return self._session_dict(session)

    async def get_session_by_key(self, session_key: str) -> dict[str, Any]:
        """Get session by session_key string."""
        q = select(AIConversationSession).where(
            AIConversationSession.session_key == session_key
        )
        session = (await self.db.execute(q)).scalars().first()
        if not session:
            raise ServiceOSException(ERR_SESSION_NOT_FOUND, "Session not found.", status_code=404)
        return self._session_dict(session)

    async def close_session(self, session_id: uuid.UUID) -> dict[str, Any]:
        """Mark a session as completed."""
        session = await self._require_session(session_id)
        session.workflow_status = WORKFLOW_STATUS_COMPLETED
        session.is_active       = False
        session.completed_at    = datetime.now(timezone.utc)
        await self.db.flush()

        await self._audit(
            session_id=str(session.id),
            event_type=AUDIT_SESSION_CLOSE,
            event_data={"turn_count": session.turn_count},
            customer_id=session.customer_id,
            severity=SEVERITY_INFO,
        )
        await self.db.commit()
        return self._session_dict(session)

    async def set_session_language(
        self, session_id: uuid.UUID, language: str,
    ) -> dict[str, Any]:
        """Set the chatbot conversation language. Was called by the mobile
        app (PUT .../language) against a route that never existed on this
        engine -- every language change silently 404'd. Only allows a code
        this session's own build_language_options() actually offers, never
        an arbitrary ALLOWED_LANGUAGES value the customer wasn't shown."""
        session = await self._require_session(session_id)
        offered = {opt["code"] for opt in build_language_options((session.context_data or {}).get("zipcode"))}
        if language not in offered:
            raise ServiceOSException(
                "AI_LANGUAGE_NOT_OFFERED",
                f"'{language}' is not one of this session's offered languages.",
                status_code=422,
            )
        session.language = language
        await self.db.commit()
        return self._session_dict(session)

    async def list_customer_sessions(
        self,
        customer_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List all sessions for a customer."""
        offset = (page - 1) * page_size
        q = (
            select(AIConversationSession)
            .where(AIConversationSession.customer_id == customer_id)
            .order_by(desc(AIConversationSession.last_activity_at))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.db.execute(q)).scalars().all()
        total = (await self.db.execute(
            select(func.count()).select_from(AIConversationSession)
            .where(AIConversationSession.customer_id == customer_id)
        )).scalar_one()
        return {
            "sessions":  [r.to_dict() for r in rows],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # MESSAGE + CHAT
    # ══════════════════════════════════════════════════════════════════════════

    async def send_message(
        self,
        session_id: uuid.UUID,
        user_message: str,
        customer_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Process one user message, call DeepSeek (with tool loop), persist everything.
        Returns {"reply": str, "tools_called": [str], "session": dict, "intent": str}.
        """
        import time

        session = await self._require_session(session_id)

        if not session.is_active:
            raise ServiceOSException(
                ERR_SESSION_CLOSED,
                "This conversation session has been closed.",
                status_code=409,
            )
        if session.turn_count >= MAX_TURNS_PER_SESSION:
            raise ServiceOSException(
                ERR_SESSION_MAX_TURNS,
                "Maximum conversation length reached. Please start a new session.",
                status_code=429,
            )

        # ── Safety: prompt injection check ────────────────────────────────────
        safe_msg, injections = sanitize_user_message(user_message)
        if injections:
            await self._audit(
                session_id=str(session.id),
                event_type=AUDIT_PROMPT_INJECTION,
                event_data={"patterns": injections, "preview": user_message[:100]},
                customer_id=customer_id or session.customer_id,
                severity=SEVERITY_WARNING,
            )

        # ── Detect intent ─────────────────────────────────────────────────────
        intent = detect_intent(user_message)
        if intent != session.current_intent:
            session.current_intent = intent

        # ── Persist user message ──────────────────────────────────────────────
        user_msg_obj = AIConversationMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role=ROLE_USER,
            content=user_message,
            intent_at_time=intent,
            tool_calls_made=[],
        )
        self.db.add(user_msg_obj)
        await self.db.flush()

        # ── Build chat history from DB ─────────────────────────────────────────
        history = await self._get_history_for_chat(session.id)

        # ── Get active system prompt ──────────────────────────────────────────
        system_prompt = await self._get_active_system_prompt()

        # ── Context injection ──────────────────────────────────────────────────
        context_prefix = self.workflow.build_context_prompt(
            intent=intent,
            collected_fields=session.collected_fields or {},
        )
        enriched_message = f"{context_prefix}\n\n{user_message}" if context_prefix else user_message

        # ── Build message list for DeepSeek ───────────────────────────────────
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]
        for h in history[-MAX_HISTORY_MESSAGES:]:
            messages.append({"role": h["role"], "content": h["content"]})
        # Replace last user message with context-enriched version
        messages[-1]["content"] = enriched_message

        # ── DeepSeek client + tool loop ────────────────────────────────────────
        deepseek = DeepSeekClientService(
            db=self.db,
            session_id=str(session.id),
            request_id=self.request_id,
        )
        tool_executor = BackendToolExecutor(
            db=self.db,
            customer_id=customer_id or session.customer_id,
            session_id=str(session.id),
            zipcode=(session.context_data or {}).get("zipcode"),
        )

        tools_called: list[str] = []
        start = time.monotonic()
        # Captures the most recent get_category_offerings result this turn
        # (real slugs/names, straight from the tool executor) -- if the
        # conversation ends this turn WITHOUT a draft having been started,
        # it means DeepSeek is (or should be) disambiguating between
        # offerings, and the app can render these as real tap buttons
        # instead of the customer having to type a reply. This is
        # deliberately generic (not draft/question-flow specific) so any
        # tool that returns a small set of named choices can opt in the
        # same way later.
        pending_offering_choice: dict | None = None
        pending_date_choice: bool = False
        pending_date_draft_id: str | None = None

        from app.engines.ai_conversation.constants import MAX_TOOL_ITERATIONS
        for iteration in range(MAX_TOOL_ITERATIONS):
            response = await deepseek.chat(messages=messages, tools=BACKEND_TOOLS)
            choice = response["choices"][0]
            msg    = choice["message"]
            messages.append(msg)

            if not msg.get("tool_calls"):
                reply_text = msg.get("content") or ""
                break

            for tc in msg["tool_calls"]:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"] or "{}")
                tools_called.append(fn_name)

                result = await tool_executor.execute(fn_name, fn_args)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "name":         fn_name,
                    "content":      result,
                })

                if fn_name == "get_category_offerings":
                    try:
                        parsed = json.loads(result)
                        offerings = parsed.get("offerings") or []
                        if len(offerings) >= 2:
                            pending_offering_choice = {
                                "category_slug": parsed.get("category_slug"),
                                "offerings": offerings,
                            }
                        else:
                            pending_offering_choice = None
                    except (ValueError, TypeError):
                        pass
                elif fn_name in ("start_home_service_draft", "update_home_service_draft"):
                    pending_offering_choice = None  # resolved -- no longer pending
                    # `preferred_date` has no natural free-text answer a
                    # customer would want to type (a real date) -- offer
                    # real, backend-computed date presets as tap options
                    # the same way offering choice does, instead of
                    # leaving it as the one remaining typed field.
                    try:
                        parsed = json.loads(result)
                        still_needed = parsed.get("still_needed") or []
                        if "preferred_date" in still_needed:
                            pending_date_choice = True
                            pending_date_draft_id = fn_args.get("draft_id")
                        elif fn_name == "update_home_service_draft":
                            pending_date_choice = False
                    except (ValueError, TypeError):
                        pass
        else:
            reply_text = "I'm having trouble processing your request. Please try again."

        # ── Safety: strip forbidden fields from reply ──────────────────────────
        reply_text = strip_markdown_formatting(reply_text)
        safe_reply, violations = validate_assistant_reply(reply_text)
        if violations:
            await self._audit(
                session_id=str(session.id),
                event_type=AUDIT_FORBIDDEN_FIELD,
                event_data={"fields": violations},
                customer_id=customer_id or session.customer_id,
                severity=SEVERITY_WARNING,
            )

        latency_ms = int((time.monotonic() - start) * 1000)
        token_count = (
            response.get("usage", {}).get("completion_tokens") if "usage" in response else None
        )

        # ── Persist assistant message ──────────────────────────────────────────
        asst_msg_obj = AIConversationMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role=ROLE_ASSISTANT,
            content=safe_reply,
            intent_at_time=intent,
            tool_calls_made=tools_called,
            latency_ms=latency_ms,
            token_count=token_count,
        )
        self.db.add(asst_msg_obj)

        # ── Update session ────────────────────────────────────────────────────
        session.turn_count       += 1
        session.last_activity_at  = datetime.now(timezone.utc)
        session.current_intent    = intent

        await self.db.flush()
        await self.db.commit()

        logger.info("ai_conv.message_processed", session_id=str(session.id),
                    intent=intent, tools=tools_called, latency_ms=latency_ms)

        # Real, backend-sourced tap options for THIS reply (e.g. "AC
        # Installation" vs "AC Service") -- only when the conversation is
        # still undecided (no draft started this turn). `value` is the
        # exact text sent back through the normal sendMessage path when
        # tapped, so DeepSeek sees it exactly like the customer typed it,
        # no separate client-side codepath needed.
        quick_replies = None
        if pending_offering_choice:
            quick_replies = [
                {"label": o["name"], "value": f"I want {o['name']}."}
                for o in pending_offering_choice["offerings"]
                if o.get("name")
            ]
        elif pending_date_choice and pending_date_draft_id and await self._catalog_questions_complete(pending_date_draft_id):
            # DETERMINISTIC GUARD (not prompt-wording alone): confirmed live
            # via a physical-device screenshot that offering date presets
            # purely from `still_needed` (which only diffs draft columns,
            # blind to the deterministic question-flow's own state) let a
            # date quick-reply appear in THE SAME turn a required catalog
            # question (e.g. "What's happening with the cooling?") first
            # became active -- both rendered as simultaneous, competing
            # actionable groups. The question-flow owns the interaction
            # until it reports complete; only then may schedule quick-
            # replies appear.
            today = datetime.now(timezone.utc).date()
            presets = [
                ("Today", today),
                ("Tomorrow", today + timedelta(days=1)),
                ("This weekend", today + timedelta(days=(5 - today.weekday()) % 7 or 7)),
            ]
            quick_replies = [
                {"label": label, "value": f"I'd like it on {date_val.isoformat()} ({label})."}
                for label, date_val in presets
            ]

        return {
            "reply":       safe_reply,
            "tools_called": tools_called,
            "intent":      intent,
            "session":     self._session_dict(session),
            "quick_replies": quick_replies,
        }

    async def get_messages(
        self,
        session_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get paginated messages for a session."""
        await self._require_session(session_id)
        offset = (page - 1) * page_size
        q = (
            select(AIConversationMessage)
            .where(AIConversationMessage.session_id == session_id)
            .order_by(AIConversationMessage.created_at)
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.db.execute(q)).scalars().all()
        total = (await self.db.execute(
            select(func.count()).select_from(AIConversationMessage)
            .where(AIConversationMessage.session_id == session_id)
        )).scalar_one()
        return {
            "messages":  [r.to_dict() for r in rows],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN — SESSIONS
    # ══════════════════════════════════════════════════════════════════════════

    async def admin_list_sessions(
        self,
        search: str | None = None,
        workflow_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Admin: list all sessions with optional filters."""
        offset = (page - 1) * page_size
        q = select(AIConversationSession).order_by(
            desc(AIConversationSession.last_activity_at)
        )
        if workflow_status:
            q = q.where(AIConversationSession.workflow_status == workflow_status)
        rows = (await self.db.execute(q.offset(offset).limit(page_size))).scalars().all()
        total_q = select(func.count()).select_from(AIConversationSession)
        if workflow_status:
            total_q = total_q.where(AIConversationSession.workflow_status == workflow_status)
        total = (await self.db.execute(total_q)).scalar_one()
        return {
            "sessions":  [r.to_dict() for r in rows],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN — LLM CALL LOGS
    # ══════════════════════════════════════════════════════════════════════════

    async def admin_list_llm_logs(
        self,
        session_id: uuid.UUID | None = None,
        response_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Admin: list LLM call logs."""
        offset = (page - 1) * page_size
        q = select(AILLMCallLog).order_by(desc(AILLMCallLog.created_at))
        if session_id:
            q = q.where(AILLMCallLog.session_id == session_id)
        if response_status:
            q = q.where(AILLMCallLog.response_status == response_status)
        rows = (await self.db.execute(q.offset(offset).limit(page_size))).scalars().all()
        total_q = select(func.count()).select_from(AILLMCallLog)
        if response_status:
            total_q = total_q.where(AILLMCallLog.response_status == response_status)
        total = (await self.db.execute(total_q)).scalar_one()
        return {
            "logs":      [r.to_dict() for r in rows],
            "total":     total,
            "page":      page,
            "page_size": page_size,
        }

    async def admin_get_llm_log(self, log_id: uuid.UUID) -> dict[str, Any]:
        """Admin: get single LLM call log with tool calls."""
        log = (await self.db.execute(
            select(AILLMCallLog).where(AILLMCallLog.id == log_id)
        )).scalars().first()
        if not log:
            raise ServiceOSException("AI_LOG_NOT_FOUND", "Log not found.", status_code=404)
        tool_logs = (await self.db.execute(
            select(AIToolCallLog).where(AIToolCallLog.llm_call_id == log_id)
        )).scalars().all()
        result = log.to_dict()
        result["tool_calls"] = [t.to_dict() for t in tool_logs]
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN — PROMPT TEMPLATES
    # ══════════════════════════════════════════════════════════════════════════

    async def list_prompt_templates(
        self,
        category: str | None = None,
        active_only: bool = True,
    ) -> dict[str, Any]:
        q = select(AIPromptTemplate).order_by(AIPromptTemplate.template_key)
        if active_only:
            q = q.where(AIPromptTemplate.is_active == True)
        if category:
            q = q.where(AIPromptTemplate.category == category)
        rows = (await self.db.execute(q)).scalars().all()
        return {"templates": [r.to_dict() for r in rows], "total": len(rows)}

    async def get_prompt_template(self, template_key: str) -> dict[str, Any]:
        tmpl = await self._require_template(template_key)
        return tmpl.to_dict()

    async def create_prompt_template(self, data: dict) -> dict[str, Any]:
        key = data.get("template_key", "").strip()
        if not key:
            raise ServiceOSException("AI_TEMPLATE_INVALID", "template_key required.", status_code=422)
        existing = (await self.db.execute(
            select(AIPromptTemplate).where(AIPromptTemplate.template_key == key)
        )).scalars().first()
        if existing:
            raise ServiceOSException(ERR_TEMPLATE_KEY_EXISTS,
                                     f"Template key '{key}' already exists.", status_code=409)
        tmpl = AIPromptTemplate(
            id=uuid.uuid4(),
            template_key=key,
            name=data.get("name", key),
            description=data.get("description"),
            category=data.get("category", "system"),
            template_content=data.get("template_content", ""),
            variables=data.get("variables", []),
            version=1,
            is_active=data.get("is_active", True),
        )
        self.db.add(tmpl)
        await self.db.flush()
        await self.db.commit()
        return tmpl.to_dict()

    async def update_prompt_template(self, template_key: str, data: dict) -> dict[str, Any]:
        tmpl = await self._require_template(template_key)
        if "name" in data:
            tmpl.name = data["name"]
        if "description" in data:
            tmpl.description = data["description"]
        if "category" in data:
            tmpl.category = data["category"]
        if "template_content" in data:
            tmpl.template_content = data["template_content"]
            tmpl.version += 1
        if "variables" in data:
            tmpl.variables = data["variables"]
        if "is_active" in data:
            tmpl.is_active = data["is_active"]
        await self.db.flush()
        await self.db.commit()
        return tmpl.to_dict()

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN — TEST CONSOLE
    # ══════════════════════════════════════════════════════════════════════════

    async def admin_test_console(
        self,
        message: str,
        template_key: str | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Admin test console — fire a single DeepSeek call without session persistence."""
        if template_key:
            tmpl = (await self.db.execute(
                select(AIPromptTemplate).where(AIPromptTemplate.template_key == template_key)
            )).scalars().first()
            system_content = tmpl.template_content if tmpl else BASE_SYSTEM_PROMPT
        else:
            system_content = BASE_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user",   "content": message},
        ]

        deepseek = DeepSeekClientService(
            db=self.db,
            session_id=None,
            request_id=self.request_id,
        )
        response = await deepseek.chat(messages=messages, tools=None)
        reply = response["choices"][0]["message"].get("content", "")
        safe_reply, _ = validate_assistant_reply(reply)

        return {
            "reply":        safe_reply,
            "model":        response.get("model", "deepseek-chat"),
            "usage":        response.get("usage", {}),
            "template_key": template_key,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    async def _require_session(self, session_id: uuid.UUID) -> AIConversationSession:
        session = (await self.db.execute(
            select(AIConversationSession).where(AIConversationSession.id == session_id)
        )).scalars().first()
        if not session:
            raise ServiceOSException(ERR_SESSION_NOT_FOUND, "Session not found.", status_code=404)
        return session

    async def _require_template(self, template_key: str) -> AIPromptTemplate:
        tmpl = (await self.db.execute(
            select(AIPromptTemplate).where(AIPromptTemplate.template_key == template_key)
        )).scalars().first()
        if not tmpl:
            raise ServiceOSException(
                ERR_TEMPLATE_NOT_FOUND,
                f"Prompt template '{template_key}' not found.",
                status_code=404,
            )
        return tmpl

    async def _get_active_system_prompt(self) -> str:
        """Return active system prompt template content, or BASE_SYSTEM_PROMPT."""
        tmpl = (await self.db.execute(
            select(AIPromptTemplate).where(
                and_(
                    AIPromptTemplate.template_key == "main_system_prompt",
                    AIPromptTemplate.is_active == True,
                )
            )
        )).scalars().first()
        return tmpl.template_content if tmpl else BASE_SYSTEM_PROMPT

    async def _get_history_for_chat(
        self, session_id: uuid.UUID
    ) -> list[dict[str, str]]:
        """Get recent messages for DeepSeek history (user + assistant only)."""
        q = (
            select(AIConversationMessage)
            .where(
                and_(
                    AIConversationMessage.session_id == session_id,
                    AIConversationMessage.role.in_(["user", "assistant"]),
                )
            )
            .order_by(AIConversationMessage.created_at)
            .limit(MAX_HISTORY_MESSAGES)
        )
        rows = (await self.db.execute(q)).scalars().all()
        return [{"role": r.role, "content": r.content} for r in rows]

    async def _audit(
        self,
        session_id: str | None,
        event_type: str,
        event_data: dict | None,
        customer_id: uuid.UUID | None = None,
        severity: str = SEVERITY_INFO,
        ip_address: str | None = None,
    ) -> None:
        try:
            log = AIConversationAuditLog(
                id=uuid.uuid4(),
                session_id=uuid.UUID(session_id) if session_id else None,
                event_type=event_type,
                event_data=event_data or {},
                severity=severity,
                customer_id=customer_id,
                ip_address=ip_address,
            )
            self.db.add(log)
            await self.db.flush()
        except Exception as exc:
            logger.warning("ai_conv.audit_failed", error=str(exc))
