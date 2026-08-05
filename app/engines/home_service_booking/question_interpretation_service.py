"""Backend-first-with-DeepSeek-on-demand — free-text answer interpretation.

`QuestionFlowService` remains the SOLE authority over which question is
active, which options are valid, ordering, dependencies and completion
(see its own module docstring). This service is the ONLY place DeepSeek
is ever consulted while a canonical question is active, and only for a
customer's own free-text message -- never for a normal tap (that already
goes straight to `QuestionFlowService.submit_answer`, see
customer_router.submit_question_flow_answer).

DeepSeek is given a small, scoped, customer-safe context (the current
question's id/text/options only -- no other tenant data, no pricing
internals, no other draft's data) and MUST return one of a fixed set of
structured actions. DeepSeek never writes to the draft directly: a
`match_option` action is only ever applied by calling
`QuestionFlowService.submit_answer` with the SAME validation every tap
already goes through (canonical option id, current question id, draft
ownership, question-flow version). Any invalid, low-confidence, or
malformed structured response fails closed -- the canonical question is
simply shown again, exactly as if DeepSeek had said nothing.
"""
from __future__ import annotations
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_booking.question_flow_service import QuestionFlowService
from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
from app.exceptions import ServiceOSException

ERR_NO_ACTIVE_QUESTION = "QI_NO_ACTIVE_QUESTION"

ALLOWED_ACTIONS = {
    "match_option",
    "ask_clarification",
    "answer_and_repeat_question",
    "out_of_scope",
    "cannot_answer",
}

# Below this confidence, a `match_option` action is treated as uncertain --
# the customer is asked to clarify via the same canonical options, never
# silently guessed onto the draft.
MATCH_CONFIDENCE_THRESHOLD = 0.6

# The only structural instruction DeepSeek receives for this call -- no
# booking policy, no other tenant/pricing data, nothing beyond the single
# active question's own text/options (customer-safe scoped context, per
# spec). Deliberately does not mention internal terms like "canonical",
# "backend flow", or "fallback" -- those must never leak into a reply.
_SYSTEM_PROMPT_TEMPLATE = """You are helping a customer answer ONE specific question in a home-service booking app. You must reply with ONLY a single JSON object, no other text.

The current question is:
"{question_text}"

The only valid answers are these options (nothing else is valid):
{options_json}

The customer just wrote a free-text message. Decide which ONE action applies and reply with exactly this JSON shape:
{{"action": "<one of: match_option, ask_clarification, answer_and_repeat_question, out_of_scope, cannot_answer>", "reply": "<a short, natural, friendly reply to show the customer>", "current_question_id": "{question_id}", "matched_option_id": "<an option id from the list above, or null>", "confidence": <0.0 to 1.0>}}

Rules:
- Use "match_option" ONLY if the customer's message clearly identifies one of the listed options. matched_option_id MUST be one of the option ids listed above, never invented.
- Use "ask_clarification" if you are not confident which option they mean.
- Use "answer_and_repeat_question" if they asked a genuine question about THIS question (e.g. why it's needed) -- answer briefly using only the information given here, then your reply should naturally lead back to asking the question again.
- Use "out_of_scope" if the message is unrelated to this booking (e.g. small talk, unrelated topics) -- your reply should briefly redirect them back to this question.
- Use "cannot_answer" if none of the above fit.
- Never invent an option that is not in the list.
- Never mention that you are an AI, a language model, or any internal system/tool name.
- current_question_id must always be exactly "{question_id}".
"""


class QuestionInterpretationService:
    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db = db
        self.request_id = request_id
        self.qf = QuestionFlowService(db=db)

    async def interpret(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None,
        text: str, session_id: str | None = None,
    ) -> dict:
        """Returns {"action", "reply", "envelope"} -- `envelope` is always
        the CURRENT canonical question-flow envelope (freshly re-fetched
        after a successful match_option submission, unchanged otherwise),
        so the caller never has to guess what to render next."""
        envelope = await self.qf.get_current_question(draft_id=draft_id, customer_id=customer_id)
        question = envelope.get("current_question")
        if question is None:
            raise ServiceOSException(
                ERR_NO_ACTIVE_QUESTION,
                "There is no active question to answer right now.",
                status_code=422,
            )

        options = question.get("options") or []
        valid_option_ids = {str(o["id"]) for o in options if o.get("id")}

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            question_text=question["text"],
            options_json=json.dumps([{"id": o["id"], "label": o.get("label")} for o in options]),
            question_id=question["question_id"],
        )

        client = DeepSeekClientService(db=self.db, session_id=session_id, request_id=self.request_id)
        try:
            raw = await client.chat(messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ])
            content = raw["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (ServiceOSException, KeyError, IndexError, json.JSONDecodeError, TypeError):
            # DeepSeek unavailable or returned malformed output -- fail
            # closed to the canonical question, never surface an internal
            # error or "fallback" wording to the customer.
            return {
                "action": "cannot_answer",
                "reply": "Let's continue with this question.",
                "envelope": envelope,
            }

        action = parsed.get("action")
        returned_question_id = parsed.get("current_question_id")

        # Structural validation -- DeepSeek can never change which question
        # is active, invent an action, or answer a stale question.
        if action not in ALLOWED_ACTIONS or returned_question_id != question["question_id"]:
            return {
                "action": "cannot_answer",
                "reply": "Let's continue with this question.",
                "envelope": envelope,
            }

        if action == "match_option":
            matched_id = parsed.get("matched_option_id")
            confidence = parsed.get("confidence")
            confidence = confidence if isinstance(confidence, (int, float)) else 0.0

            if matched_id not in valid_option_ids or confidence < MATCH_CONFIDENCE_THRESHOLD:
                # An invented option id, or a genuinely uncertain match --
                # both fail the same way: ask the customer to tap instead
                # of guessing on their behalf.
                return {
                    "action": "ask_clarification",
                    "reply": "Which of these options is yours?",
                    "envelope": envelope,
                }

            # The ONLY place a DeepSeek-derived answer ever reaches the
            # draft -- through the exact same canonical, validated path a
            # tap uses. DeepSeek itself never writes to the draft.
            updated_envelope = await self.qf.submit_answer(
                draft_id=draft_id, customer_id=customer_id,
                question_id=question["question_id"], option_id=matched_id,
                expected_version=envelope.get("question_flow_version"),
            )
            matched_label = next((o.get("label") for o in options if str(o.get("id")) == matched_id), None)
            return {
                "action": "match_option",
                "reply": parsed.get("reply") or (matched_label or "Got it."),
                "envelope": updated_envelope,
            }

        # ask_clarification / answer_and_repeat_question / out_of_scope /
        # cannot_answer -- none of these ever change the active question;
        # the same envelope is returned so the caller re-renders the exact
        # same canonical question and options.
        reply = parsed.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            reply = "Let's continue with this question."
        return {"action": action, "reply": reply, "envelope": envelope}
