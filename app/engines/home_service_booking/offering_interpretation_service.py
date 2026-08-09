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

from app.engines.home_service_booking.offering_catalog_service import (
    list_serviceable_issues,
    list_serviceable_issues_across_categories,
)
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


_CROSS_CATEGORY_PROMPT_TEMPLATE = """You are helping a customer say what they need fixed at home, from a fixed list in a booking app. You must reply with ONLY a single JSON object, no other text.

These are ALL the services available at this customer's location, grouped by category. Nothing outside this list is valid:
{issues_json}

The customer just wrote a free-text message. It may be about ANY of the categories above -- do not assume it is about the first one. Decide which ONE action applies and reply with exactly this JSON shape:
{{"action": "<one of: match_option, ask_clarification, answer_and_repeat_options, out_of_scope, cannot_answer>", "reply": "<a short, natural, friendly reply to show the customer>", "matched_issue_id": "<an issue id from the list above, or null>", "confidence": <0.0 to 1.0>}}

Rules:
- Use "match_option" ONLY if the message clearly identifies one of the listed issues. matched_issue_id MUST be one of the ids listed above, never invented.
- Match on MEANING, not on wording: "my tap is dripping" is a plumbing leak, "no light in the bathroom" is electrical, "the house smells" may be pest control or cleaning -- pick the one that fits, and ask if two fit equally.
- Use "ask_clarification" if you are not confident which one they mean, or if the message could be two different categories.
- Use "answer_and_repeat_options" if they asked a genuine question about one of these -- answer briefly, then lead back to what they need.
- Use "out_of_scope" ONLY if the message is not about any home service at all.
- Use "cannot_answer" if none of the above fit.
- Never invent an issue that is not in the list, and never promise a price, a time or a technician.
- Never mention that you are an AI, a language model, or any internal system/tool name.
"""


class OfferingInterpretationService:
    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db = db
        self.request_id = request_id

    async def interpret_across_categories(
        self, zipcode: str | None, text: str, session_id: str | None = None,
    ) -> dict:
        """Same contract as `interpret`, but the model sees EVERY category bookable
        at this zipcode.

        The bug this fixes: a conversation entered from an AC service card gave the
        interpreter only AC issues, so "my tap is leaking" could not be matched to
        anything real -- every answer came back AC-shaped, which reads as the model
        being stupid when in fact it was never shown the plumbing catalogue.

        `matched_offering` carries the matched issue's own CATEGORY, because a match
        here can legitimately land outside whatever category the conversation
        started in, and the caller has to know which one to start the draft in.
        """
        catalog = await list_serviceable_issues_across_categories(self.db, zipcode)
        issues = catalog.get("issues", [])
        if not issues:
            raise ServiceOSException(
                ERR_CATEGORY_UNAVAILABLE,
                "No services are available at this location right now.",
                status_code=422,
            )

        # Grouped in the prompt so the model reads a catalogue rather than a flat
        # list of 17 unrelated strings -- and so "which category is this?" is
        # answerable from the same structure it matches against.
        grouped: dict[str, list[dict]] = {}
        for issue in issues:
            grouped.setdefault(issue.get("category_name") or "Other", []).append(
                {"id": issue["id"], "name": issue["label"]}
            )
        by_id = {i["id"]: i for i in issues}

        system_prompt = _CROSS_CATEGORY_PROMPT_TEMPLATE.format(
            issues_json=json.dumps(grouped, ensure_ascii=False),
        )
        safe_issues = [{"id": i["id"], "name": i["label"]} for i in issues]

        parsed = await self._ask(system_prompt, text, session_id)
        if parsed is None:
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

        matched = None
        if action == "match_option":
            issue_id = parsed.get("matched_issue_id")
            confidence = parsed.get("confidence")
            # Validated against the REAL list, so a hallucinated id cannot start a
            # draft, and a low-confidence guess is demoted to a question rather
            # than acted on.
            if (
                issue_id in by_id
                and isinstance(confidence, (int, float))
                and float(confidence) >= MATCH_CONFIDENCE_THRESHOLD
            ):
                hit = by_id[issue_id]
                matched = {
                    "id": hit["id"],
                    "name": hit["label"],
                    "category_slug": hit.get("category_slug"),
                    "category_name": hit.get("category_name"),
                    "category_id": hit.get("category_id"),
                }
            else:
                action = "ask_clarification"

        reply = parsed.get("reply")
        return {
            "action": action,
            "reply": reply if isinstance(reply, str) and reply.strip() else "What do you need help with?",
            "matched_offering": matched,
            "offerings": safe_issues,
        }

    async def _ask(self, system_prompt: str, text: str, session_id: str | None) -> dict | None:
        """One DeepSeek round trip, or None if anything about it was unusable.

        Every failure mode -- transport, a non-JSON body, a JSON body that is not
        an object -- collapses to None here so callers degrade to their own honest
        fallback rather than each re-implementing the same try/except.
        """
        client = DeepSeekClientService(db=self.db, session_id=session_id, request_id=self.request_id)
        try:
            raw = await client.chat(messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ])
            parsed = json.loads(raw["choices"][0]["message"]["content"])
        except (ServiceOSException, KeyError, IndexError, json.JSONDecodeError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None

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
