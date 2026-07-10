"""AI Settlement Service — uses DeepSeek as neutral arbitrator for complaint resolution.

The API key is read from the environment (DEEPSEEK_API_KEY) and is NEVER
stored in source code, DB, or API responses.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.complaints.constants import (
    AI_SESSION_COLLECTING, AI_SESSION_ANALYZING,
    AI_SESSION_PROPOSAL_READY, AI_SESSION_COMPLETED, AI_SESSION_FAILED,
    ACTOR_AI, ACTOR_SYSTEM,
    EVT_AI_SESSION_STARTED, EVT_AI_PROPOSAL_GENERATED,
    PROPOSAL_PROPOSED,
)
from app.engines.complaints.models import (
    AISettlementSession, CustomerComplaint, ComplaintEvent,
    ComplaintMessage, ComplaintMedia, SettlementProposal,
)

_DEEPSEEK_URL  = "https://api.deepseek.com/chat/completions"
_MODEL         = "deepseek-chat"
_SYSTEM_PROMPT = """You are a neutral AI dispute arbitrator for a home-services platform.
Your role is to analyze complaint evidence objectively and propose fair settlements.
Never side with either party without clear evidence. Always recommend the resolution
that is most proportional to the harm caused. Output structured JSON only."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not configured")
    return key


async def _call_deepseek(messages: list[dict], max_tokens: int = 1500) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            _DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
            json={"model": _MODEL, "messages": messages, "max_tokens": max_tokens,
                  "response_format": {"type": "json_object"}},
        )
        resp.raise_for_status()
        return resp.json()


class AISettlementService:

    async def start_session(
        self,
        db: AsyncSession,
        complaint: CustomerComplaint,
        actor_id: uuid.UUID,
        request_id: str = "—",
    ) -> AISettlementSession:
        """Create an AI settlement session and generate clarifying questions."""
        session = AISettlementSession(
            complaint_id = complaint.id,
            tenant_id    = complaint.tenant_id,
            status       = AI_SESSION_COLLECTING,
            model_used   = _MODEL,
            started_at   = _now(),
        )
        db.add(session)

        # Log event
        db.add(ComplaintEvent(
            complaint_id  = complaint.id,
            tenant_id     = complaint.tenant_id,
            actor_type    = ACTOR_AI,
            actor_user_id = None,
            event_type    = EVT_AI_SESSION_STARTED,
            old_status    = complaint.status,
            new_status    = complaint.status,
            reason        = "AI settlement session started",
            request_id    = request_id,
        ))

        await db.flush()

        # Generate questions for customer and tenant
        questions = await self._generate_questions(complaint)
        session.customer_questions = questions.get("customer_questions", [])
        session.tenant_questions   = questions.get("tenant_questions", [])
        await db.flush()

        return session

    async def analyze_and_propose(
        self,
        db: AsyncSession,
        session: AISettlementSession,
        complaint: CustomerComplaint,
        request_id: str = "—",
    ) -> SettlementProposal | None:
        """Analyze all evidence and answers, then generate a settlement proposal."""
        session.status = AI_SESSION_ANALYZING
        await db.flush()

        try:
            result = await self._analyze_dispute(complaint, session)
        except Exception as exc:
            session.status       = AI_SESSION_FAILED
            session.ai_recommendation = f"Analysis failed: {exc}"
            session.completed_at = _now()
            await db.flush()
            return None

        session.evidence_summary  = result.get("evidence_summary", "")
        session.ai_recommendation = result.get("recommendation", "")
        session.risk_flags        = result.get("risk_flags", [])
        session.confidence_score  = result.get("confidence_score", 0.5)
        session.status            = AI_SESSION_PROPOSAL_READY
        session.completed_at      = _now()

        # Create a SettlementProposal from the AI recommendation
        proposal_data  = result.get("proposal", {})
        if not proposal_data:
            session.status = AI_SESSION_FAILED
            await db.flush()
            return None

        proposal = SettlementProposal(
            complaint_id     = complaint.id,
            tenant_id        = complaint.tenant_id,
            proposed_by      = ACTOR_AI,
            proposal_type    = proposal_data.get("type", "partial_refund"),
            proposal_amount  = proposal_data.get("amount"),
            description      = proposal_data.get("description", "AI-generated settlement"),
            conditions       = proposal_data.get("conditions"),
            status           = PROPOSAL_PROPOSED,
            ai_generated     = True,
            ai_confidence_score = result.get("confidence_score", 0.5),
        )
        db.add(proposal)

        session.status = AI_SESSION_COMPLETED
        complaint.ai_session_id = session.id

        db.add(ComplaintEvent(
            complaint_id  = complaint.id,
            tenant_id     = complaint.tenant_id,
            actor_type    = ACTOR_AI,
            actor_user_id = None,
            event_type    = EVT_AI_PROPOSAL_GENERATED,
            reason        = f"AI settlement proposal generated with {int((result.get('confidence_score', 0.5))*100)}% confidence",
            request_id    = request_id,
        ))

        await db.flush()
        return proposal

    async def _generate_questions(self, complaint: CustomerComplaint) -> dict:
        prompt = f"""Generate clarifying questions for a dispute case.

Complaint type: {complaint.complaint_type}
Description: {complaint.description}
Priority: {complaint.priority}
Severity: {complaint.severity or 'medium'}

Generate 3 targeted questions for the customer and 3 for the provider tenant.
Return JSON: {{"customer_questions": [...], "tenant_questions": [...]}}"""

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        try:
            raw = await _call_deepseek(messages, max_tokens=600)
            content = raw["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            return {
                "customer_questions": [
                    "Please describe the issue in detail.",
                    "What resolution are you expecting?",
                    "Do you have evidence (photos/videos)?",
                ],
                "tenant_questions": [
                    "Please provide your explanation of what occurred.",
                    "What remedy can you offer the customer?",
                    "Do you have documentation of the service delivered?",
                ],
            }

    async def _analyze_dispute(
        self, complaint: CustomerComplaint, session: AISettlementSession
    ) -> dict:
        customer_qa = self._format_qa(
            session.customer_questions or [], session.customer_answers or []
        )
        tenant_qa = self._format_qa(
            session.tenant_questions or [], session.tenant_answers or []
        )

        prompt = f"""Analyze this dispute and propose a fair settlement.

Complaint: {complaint.complaint_type}
Description: {complaint.description}
Priority: {complaint.priority}  Severity: {complaint.severity or 'medium'}
Requested resolution: {complaint.requested_resolution or 'not specified'}

Customer responses:
{customer_qa}

Provider responses:
{tenant_qa}

Return JSON with:
{{
  "evidence_summary": "objective summary of facts",
  "recommendation": "recommended resolution and rationale",
  "risk_flags": ["list of concerns"],
  "confidence_score": 0.0-1.0,
  "proposal": {{
    "type": "partial_refund|full_refund|rework|apology|no_action|service_credit",
    "amount": null or number,
    "description": "what the settlement entails",
    "conditions": "any conditions on the settlement"
  }}
}}"""

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        raw     = await _call_deepseek(messages, max_tokens=1200)
        content = raw["choices"][0]["message"]["content"]
        data    = json.loads(content)

        # Track token usage
        usage = raw.get("usage", {})
        session.prompt_tokens     = usage.get("prompt_tokens")
        session.completion_tokens = usage.get("completion_tokens")

        return data

    def _format_qa(self, questions: list, answers: list) -> str:
        lines = []
        for i, q in enumerate(questions):
            a = answers[i] if i < len(answers) else "(no answer)"
            lines.append(f"Q: {q}\nA: {a}")
        return "\n".join(lines) or "(no responses)"
