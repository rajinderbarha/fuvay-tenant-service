"""Sprint 15 — AIWorkflowRouterService: intent detection + workflow state management."""
from __future__ import annotations
import uuid
from typing import Any

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.ai_conversation.constants import (
    INTENT_BOOKING_INTENT,
    INTENT_COMPLAINT,
    INTENT_GENERAL_QUERY,
    INTENT_SERVICE_INQUIRY,
    INTENT_STATUS_CHECK,
    INTENT_UNKNOWN,
    VALID_INTENTS,
)

logger = structlog.get_logger("ai_conversation.workflow")


# ── Keyword maps for quick intent detection ────────────────────────────────────
INTENT_KEYWORDS: dict[str, list[str]] = {
    INTENT_BOOKING_INTENT: [
        "book", "schedule", "appointment", "slot", "reserve", "fix a time",
        "want to book", "need to book", "set up", "arrange",
    ],
    INTENT_STATUS_CHECK: [
        "status", "where is", "technician", "when will", "my booking",
        "track", "eta", "arriving", "update on",
    ],
    INTENT_COMPLAINT: [
        "complaint", "unhappy", "bad service", "refund", "cancel", "wrong",
        "not satisfied", "issue with", "problem with booking", "demand",
    ],
    INTENT_SERVICE_INQUIRY: [
        "repair", "service", "fix", "broken", "not working", "leaking",
        "clean", "pest", "painting", "ac", "plumbing", "electrical",
        "maintenance", "install", "consultation", "inspect",
    ],
    INTENT_GENERAL_QUERY: [
        "how much", "price", "cost", "what is", "how long", "do you",
        "are you", "can you", "available", "offer",
    ],
}


def detect_intent(message: str) -> str:
    """Classify customer intent from message text using keyword matching."""
    lower = message.lower()
    scores: dict[str, int] = {intent: 0 for intent in VALID_INTENTS}

    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[intent] += 1

    # Return highest scoring intent, minimum 1 match required
    best_intent = max(scores, key=lambda i: scores[i])
    if scores[best_intent] == 0:
        return INTENT_UNKNOWN
    return best_intent


class AIWorkflowRouterService:
    """
    Manages workflow state for AI conversations.
    Determines what step the conversation is at and what context to inject.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_workflow_state(
        self, session_id: uuid.UUID, workflow_name: str
    ) -> dict[str, Any]:
        """Get existing workflow state or create a new one."""
        from app.engines.ai_conversation.models import AIWorkflowState

        q = select(AIWorkflowState).where(
            and_(
                AIWorkflowState.session_id == session_id,
                AIWorkflowState.workflow_name == workflow_name,
            )
        )
        state = (await self.db.execute(q)).scalars().first()
        if state:
            return state.to_dict()

        state = AIWorkflowState(
            id=uuid.uuid4(),
            session_id=session_id,
            workflow_name=workflow_name,
            current_step="start",
            steps_completed=[],
            steps_pending=self._get_workflow_steps(workflow_name),
            extracted_data={},
            validation_errors=[],
            is_complete=False,
        )
        self.db.add(state)
        await self.db.flush()
        return state.to_dict()

    async def advance_workflow(
        self,
        session_id: uuid.UUID,
        workflow_name: str,
        completed_step: str,
        extracted_data: dict | None = None,
    ) -> dict[str, Any]:
        """Mark a step as completed and advance to next step."""
        from app.engines.ai_conversation.models import AIWorkflowState

        q = select(AIWorkflowState).where(
            and_(
                AIWorkflowState.session_id == session_id,
                AIWorkflowState.workflow_name == workflow_name,
            )
        )
        state = (await self.db.execute(q)).scalars().first()
        if not state:
            return await self.get_or_create_workflow_state(session_id, workflow_name)

        completed = list(state.steps_completed or [])
        if completed_step not in completed:
            completed.append(completed_step)

        pending = list(state.steps_pending or [])
        if completed_step in pending:
            pending.remove(completed_step)

        merged_data = {**(state.extracted_data or {}), **(extracted_data or {})}
        next_step = pending[0] if pending else "complete"

        state.steps_completed = completed
        state.steps_pending   = pending
        state.extracted_data  = merged_data
        state.current_step    = next_step
        state.is_complete     = len(pending) == 0
        await self.db.flush()

        return state.to_dict()

    def build_context_prompt(
        self,
        intent: str,
        collected_fields: dict,
        workflow_state: dict | None = None,
    ) -> str:
        """Build a context injection string to prepend to user messages."""
        lines = [f"[CURRENT INTENT: {intent}]"]

        if collected_fields:
            field_summary = ", ".join(f"{k}={v}" for k, v in collected_fields.items()
                                      if v is not None)
            if field_summary:
                lines.append(f"[COLLECTED: {field_summary}]")

        if workflow_state:
            step = workflow_state.get("current_step", "unknown")
            lines.append(f"[WORKFLOW STEP: {step}]")
            if workflow_state.get("steps_pending"):
                pending = ", ".join(workflow_state["steps_pending"][:3])
                lines.append(f"[STILL NEEDED: {pending}]")

        return "\n".join(lines)

    def _get_workflow_steps(self, workflow_name: str) -> list[str]:
        """Return the step list for a workflow type."""
        workflows = {
            "service_booking": ["identify_service", "get_location", "get_schedule", "confirm"],
            "complaint":       ["understand_issue", "get_booking_ref", "escalate"],
            "status_check":    ["get_booking_ref", "check_status"],
            "general":         ["understand_query", "respond"],
        }
        return workflows.get(workflow_name, ["understand", "respond"])
