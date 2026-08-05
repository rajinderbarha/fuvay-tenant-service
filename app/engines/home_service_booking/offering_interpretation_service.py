"""Backend-first Booking Assistant — constrained issue-selection
interpretation (Phase 10 of the re-architecture).

Mirrors `QuestionInterpretationService`'s contract exactly, one stage
earlier: BEFORE any draft exists, a customer may type instead of tapping
an issue (real customer intent -- "AC not cooling", "install a new AC" --
never an internal offering/job-type split). This service gives DeepSeek
only the real, zipcode-serviceable issue list
(`offering_catalog_service.list_serviceable_issues`) and requires one of a
fixed set of structured actions. DeepSeek never creates a draft, never
invents an issue, and never advances past issue selection -- a
`match_option` action only ever returns the matched, backend-validated
issue; the CALLER (the customer_router endpoint / `select_issue`) is
responsible for actually creating the draft and resolving the offering/
job type, via the exact same path a tap uses.
"""
from __future__ import annotations
import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues
from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
from app.exceptions import ServiceOSException

ERR_CATEGORY_UNAVAILABLE = "OI_CATEGORY_UNAVAILABLE"

ALLOWED_ACTIONS = {
    "match_option",
    "ask_clarification",
    "answer_and_repeat_options",
    "out_of_scope",
    "cannot_answer",
}

MATCH_CONFIDENCE_THRESHOLD = 0.6

_SYSTEM_PROMPT_TEMPLATE = """You are helping a customer describe what's wrong with their appliance, or what they need, from a fixed list in a booking app. You must reply with ONLY a single JSON object, no other text.

The category is "{category_name}".

The only valid choices are these issues/needs (nothing else is valid):
{issues_json}

The customer just wrote a free-text message. Decide which ONE action applies and reply with exactly this JSON shape:
{{"action": "<one of: match_option, ask_clarification, answer_and_repeat_options, out_of_scope, cannot_answer>", "reply": "<a short, natural, friendly reply to show the customer>", "matched_issue_id": "<an issue id from the list above, or null>", "confidence": <0.0 to 1.0>}}

Rules:
- Use "match_option" ONLY if the customer's message clearly identifies one of the listed issues/needs. matched_issue_id MUST be one of the ids listed above, never invented.
- Use "ask_clarification" if you are not confident which one they mean.
- Use "answer_and_repeat_options" if they asked a genuine question about one of these -- answer briefly, then your reply should naturally lead back to asking what they need.
- Use "out_of_scope" if the message is unrelated to this booking category -- your reply should briefly redirect them back to choosing what they need.
- Use "cannot_answer" if none of the above fit.
- Never invent an issue that is not in the list.
- Never mention that you are an AI, a language model, or any internal system/tool name.
"""


class OfferingInterpretationService:
    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db = db
        self.request_id = request_id

    async def interpret(
        self, category_slug: str, zipcode: str | None, text: str, session_id: str | None = None,
    ) -> dict:
        """Returns {"action", "reply", "matched_offering": {...} | None,
        "offerings": [...]} -- `offerings` here carries the real,
        zipcode-serviceable ISSUE list (kept as `matched_offering`/
        `offerings` keys for wire-contract stability with the existing
        frontend adapter), so the caller never has to guess what to
        render next."""
        catalog = await list_serviceable_issues(self.db, category_slug, zipcode)
        issues = catalog.get("issues", [])
        if not issues:
            raise ServiceOSException(
                ERR_CATEGORY_UNAVAILABLE,
                "No services are available for this category right now.",
                status_code=422,
            )
        safe_issues = [{"id": i["id"], "name": i["label"]} for i in issues]
        valid_ids = {i["id"] for i in safe_issues}

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            category_name=catalog.get("category") or category_slug,
            issues_json=json.dumps(safe_issues),
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
            return {
                "action": "cannot_answer",
                "reply": "What do you need help with?",
                "matched_offering": None,
                "offerings": safe_issues,
            }

        action = parsed.get("action")
        if action not in ALLOWED_ACTIONS:
            return {
                "action": "cannot_answer",
                "reply": "What do you need help with?",
                "matched_offering": None,
                "offerings": safe_issues,
            }

        if action == "match_option":
            matched_id = parsed.get("matched_issue_id")
            confidence = parsed.get("confidence")
            confidence = confidence if isinstance(confidence, (int, float)) else 0.0

            if matched_id not in valid_ids or confidence < MATCH_CONFIDENCE_THRESHOLD:
                return {
                    "action": "ask_clarification",
                    "reply": "Which of these best matches what you need?",
                    "matched_offering": None,
                    "offerings": safe_issues,
                }

            matched = next(i for i in safe_issues if i["id"] == matched_id)
            return {
                "action": "match_option",
                "reply": parsed.get("reply") or matched["name"],
                "matched_offering": matched,
                "offerings": safe_issues,
            }

        reply = parsed.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            reply = "What do you need help with?"
        return {"action": action, "reply": reply, "matched_offering": None, "offerings": safe_issues}
