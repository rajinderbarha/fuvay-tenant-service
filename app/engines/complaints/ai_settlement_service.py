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
    # MODULE-L5-02 bug #38: this read os.environ directly, which does NOT pick up
    # .env — pydantic Settings (env_file=".env") is what loads it. So the AI
    # settlement analysis ALWAYS failed with "DEEPSEEK_API_KEY not configured"
    # even though the key was correctly configured and every other AI feature
    # worked, because every other DeepSeek caller (ai_chat, ai_conversation) goes
    # through get_settings(). The bug was invisible while analyze_and_propose had
    # no caller at all (bug #37). Read it the same way everyone else does, still
    # falling back to the raw environment.
    from app.config import get_settings
    key = get_settings().DEEPSEEK_API_KEY or os.environ.get("DEEPSEEK_API_KEY", "")
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

        # Running an AI settlement is a paid platform service: the PROVIDER is
        # charged from the canonical usage-credit balance. Never fatal: a
        # billing problem must not prevent the dispute from being handled.
        from app.engines.complaints.settlement_rules import charge_ai_settlement_fee
        try:
            fee = await charge_ai_settlement_fee(
                db, complaint.tenant_id, complaint.id, actor_id=actor_id)
            db.add(ComplaintEvent(
                complaint_id  = complaint.id,
                tenant_id     = complaint.tenant_id,
                actor_type    = ACTOR_SYSTEM,
                actor_user_id = None,
                event_type    = "ai_settlement_fee_charged",
                reason        = (f"AI settlement fee {fee['fee']} charged to provider "
                                 f"(usage credits {fee['charged_from_wallet']}, "
                                 f"balance after {fee['balance_after']})"),
                new_value     = fee,
                request_id    = request_id,
            ))
        except Exception:  # a billing problem must never block the dispute
            pass

        # Generate questions for customer and tenant
        questions = await self._generate_questions(complaint)
        session.customer_questions = questions.get("customer_questions", [])
        session.tenant_questions   = questions.get("tenant_questions", [])
        await db.flush()

        return session

    async def submit_answers(
        self,
        db: AsyncSession,
        complaint: CustomerComplaint,
        party: str,
        answers: list[str] | dict,
        request_id: str = "—",
    ) -> AISettlementSession:
        """MODULE-L5-02 bug #37: start_session asked the customer and the tenant
        a set of clarifying questions — but NOTHING could ever answer them. There
        was no endpoint on either side, so customer_answers/tenant_answers stayed
        NULL forever and the session sat in 'collecting' permanently. And
        analyze_and_propose() — which turns those answers into the AI
        recommendation and the SettlementProposal — had ZERO callers, so the AI
        never actually analysed anything. The whole AI settlement engine was a
        dead end.

        This is the missing step: record one party's answers and, once BOTH have
        answered, run the analysis that produces the settlement proposal (which
        then flows into the normal dual-acceptance path).
        """
        session = await self._get_active_session(db, complaint.id)
        if session is None:
            raise ValueError("AI_SESSION_NOT_FOUND")
        if session.status not in (AI_SESSION_COLLECTING,):
            raise ValueError("AI_SESSION_NOT_COLLECTING")
        if party not in ("customer", "tenant"):
            raise ValueError("AI_SESSION_INVALID_PARTY")

        if party == "customer":
            session.customer_answers = answers
        else:
            session.tenant_answers = answers
        await db.flush()

        # Both sides in → run the (previously orphaned) analysis.
        if session.customer_answers is not None and session.tenant_answers is not None:
            await self.analyze_and_propose(db, session, complaint, request_id=request_id)

        await db.flush()
        return session

    async def _get_active_session(
        self, db: AsyncSession, complaint_id: uuid.UUID
    ) -> AISettlementSession | None:
        r = await db.execute(
            select(AISettlementSession)
            .where(AISettlementSession.complaint_id == complaint_id)
            .order_by(AISettlementSession.created_at.desc())
        )
        return r.scalars().first()

    async def analyze_and_propose(
        self,
        db: AsyncSession,
        session: AISettlementSession,
        complaint: CustomerComplaint,
        request_id: str = "—",
    ) -> SettlementProposal | None:
        """Analyze all evidence and answers, then generate a settlement proposal."""
        from app.engines.complaints.settlement_rules import (
            resolve_rule, resolve_job_value, evaluate_proposal,
        )
        from app.engines.complaints.constants import (
            STATUS_UNDER_ADMIN_REVIEW, ALLOWED_TRANSITIONS, EVT_AI_CAP_EXCEEDED,
        )

        rule      = await resolve_rule(db, complaint)
        job_value = await resolve_job_value(db, complaint)

        session.status = AI_SESSION_ANALYZING
        await db.flush()

        try:
            result = await self._analyze_dispute(complaint, session, rule, job_value)
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

        # ── The rule, enforced in code ────────────────────────────────────────
        # Whatever the model returned is re-checked here against the admin's
        # policy. A monetary remedy, a remedy the admin has not permitted, or an
        # amount above the cap does NOT get clamped down and settled quietly —
        # the case is handed to a human, which is the entire point of the cap.
        verdict = evaluate_proposal(
            rule, job_value,
            remedy=proposal_data.get("type", ""),
            amount=proposal_data.get("amount"),
        )

        if not verdict.allowed:
            session.status = AI_SESSION_COMPLETED
            session.completed_at = _now()
            complaint.ai_session_id = session.id
            if STATUS_UNDER_ADMIN_REVIEW in ALLOWED_TRANSITIONS.get(complaint.status, set()):
                complaint.status = STATUS_UNDER_ADMIN_REVIEW
            db.add(ComplaintEvent(
                complaint_id  = complaint.id,
                tenant_id     = complaint.tenant_id,
                actor_type    = ACTOR_AI,
                actor_user_id = None,
                event_type    = EVT_AI_CAP_EXCEEDED,
                reason        = verdict.reason,
                new_value     = {
                    "proposed_remedy": verdict.remedy,
                    "proposed_amount": str(verdict.amount),
                    "cap":             str(rule.cap_amount(job_value)),
                    "job_value":       str(job_value),
                },
                request_id    = request_id,
            ))
            # bug #40: tell the admins a case has landed in their lap — the AI
            # deliberately did NOT settle it and it now needs a human decision.
            try:
                from app.engines.complaints.notifications import notify_admins_complaint
                await notify_admins_complaint(
                    db, complaint,
                    notification_type="complaint.ai_settlement.escalated",
                    title=f"AI settlement escalated — {complaint.complaint_number}",
                    body=verdict.reason,
                    severity="warning",
                )
            except Exception:
                pass
            await db.flush()
            return None

        proposal = SettlementProposal(
            complaint_id     = complaint.id,
            tenant_id        = complaint.tenant_id,
            proposed_by      = ACTOR_AI,
            proposal_type    = verdict.remedy,
            proposal_amount  = verdict.amount if verdict.amount > 0 else None,
            description      = proposal_data.get("description", "AI-generated settlement"),
            conditions       = proposal_data.get("conditions"),
            status           = PROPOSAL_PROPOSED,
            ai_generated     = True,
            ai_confidence_score = result.get("confidence_score", 0.5),
        )
        db.add(proposal)

        session.status = AI_SESSION_COMPLETED
        complaint.ai_session_id = session.id

        # bug #42: the AI proposal needs BOTH parties to accept — tell them both
        # it is now awaiting their response.
        try:
            from app.engines.complaints.notifications import (
                notify_customer_complaint, notify_provider_complaint,
            )
            title = f"AI proposed a settlement — {complaint.complaint_number}"
            body = (f"The AI mediator proposed: {verdict.remedy.replace('_', ' ')}"
                    f"{f' ({verdict.amount} credits)' if verdict.amount > 0 else ''}. "
                    "It takes effect once both you and the other party accept.")
            await notify_customer_complaint(db, complaint,
                notification_type="complaint.ai_settlement_proposed", title=title, body=body)
            await notify_provider_complaint(db, complaint,
                notification_type="complaint.ai_settlement_proposed", title=title, body=body)
        except Exception:
            pass

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
        self, complaint: CustomerComplaint, session: AISettlementSession,
        rule=None, job_value=None,
    ) -> dict:
        from decimal import Decimal
        from app.engines.complaints.settlement_rules import DEFAULT_RULE

        rule = rule or DEFAULT_RULE
        job_value = Decimal(str(job_value if job_value is not None else "0"))
        cap = rule.cap_amount(job_value)

        customer_qa = self._format_qa(
            session.customer_questions or [], session.customer_answers or []
        )
        tenant_qa = self._format_qa(
            session.tenant_questions or [], session.tenant_answers or []
        )

        # The rule is stated to the model, and then enforced again in code after
        # it answers (see settlement_rules.evaluate_proposal) — the model is
        # never trusted to honour the cap or the no-money rule on its own.
        prompt = f"""Analyze this dispute and propose a fair settlement.

Complaint: {complaint.complaint_type}
Description: {complaint.description}
Priority: {complaint.priority}  Severity: {complaint.severity or 'medium'}
Requested resolution: {complaint.requested_resolution or 'not specified'}

Customer responses:
{customer_qa}

Provider responses:
{tenant_qa}

SETTLEMENT RULES — these are hard limits, not suggestions:
- The job is worth {job_value}. You may offer AT MOST {rule.max_pct}% of that,
  i.e. a maximum of {cap}.
- Compensation is paid in CREDIT POINTS only. You must NEVER propose money: no
  refund, partial refund, cash or bank transfer of any kind.
- Permitted remedies, and nothing else: {", ".join(rule.allowed_remedies)}
    credit_points = account credit (has an "amount", must be <= {cap})
    rework        = a free repeat visit (no amount)
    callback      = a follow-up call (no amount)
    apology       = an apology only (no amount)
    no_action     = the complaint does not merit compensation
- If this case is strong enough that fairness demands MORE than {cap}, do NOT
  try to settle it. Set "type" to "escalate" and explain why — a human will
  decide. Escalating a genuinely strong case is the correct outcome, not a
  failure.

Return JSON with:
{{
  "evidence_summary": "objective summary of facts",
  "recommendation": "recommended resolution and rationale",
  "risk_flags": ["list of concerns"],
  "confidence_score": 0.0-1.0,
  "proposal": {{
    "type": "{'|'.join(rule.allowed_remedies)}|escalate",
    "amount": null or number (only for credit_points, and <= {cap}),
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
