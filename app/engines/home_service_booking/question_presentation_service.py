"""CUSTOMER-ASSISTANT-UX-04 Parts 3/4 — DeepSeek question PRESENTATION.

Strict separation of concerns:

  * The BACKEND owns every piece of booking semantics -- which question is
    active, its canonical text, its type, its allowed option ids and
    canonical labels, required/optional state, dependencies, ordering,
    progress, and which stage may come next. None of that is ever
    delegated.
  * DeepSeek owns PRESENTATION ONLY -- rendering that one already-chosen
    question, and its already-chosen options, naturally in the customer's
    selected conversation language (en / hi / pa).

This is deliberately NOT the general chat endpoint and NOT
`QuestionInterpretationService` (which reads a customer's free text and
may submit a validated option). This service never writes to a draft,
never advances a stage, and never decides anything -- it is a pure,
validated translation layer in front of a question the backend already
selected.

Every DeepSeek response is validated before the customer can see it (see
`_validate`). Any failure -- wrong question id, wrong language, an
invented/missing/duplicated option, malformed JSON, a timeout, a network
error -- fails CLOSED to the canonical backend question, which is always
a correct (if untranslated) thing to show. The customer never sees an
error, a retry prompt, or any internal terminology.
"""
from __future__ import annotations
import json
import hashlib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.ai_conversation.deepseek_client import DeepSeekClientService
from app.exceptions import ServiceOSException
from app.core.logging import get_logger

logger = get_logger(__name__)

# The only conversation languages this service will ever present in --
# mirrors `regional_language._LANGUAGE_LABELS`. A language outside this
# set is not an error: it simply means "present canonically" (English
# backend text as-authored), never a guess at an unsupported language.
SUPPORTED_PRESENTATION_LANGUAGES = {"en", "hi", "pa"}

_LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "pa": "Punjabi (ਪੰਜਾਬੀ, Gurmukhi script)",
}

# Presentations are pure functions of (question text/options, language) --
# they contain NO draft-specific or customer-specific data whatsoever, so
# they are safe to share across customers. Keyed by a hash of the exact
# canonical content so ANY admin edit to the question or its options
# naturally produces a different key and invalidates the old entry.
_PRESENTATION_CACHE: dict[str, dict] = {}
_PRESENTATION_CACHE_MAX = 512

_SYSTEM_PROMPT = """You translate ONE question for a home-service booking app into the customer's language. Reply with ONLY a single JSON object and no other text.

You will be given a question and its exact list of allowed options.

Your ONLY job:
- Translate the question text naturally into {language_name}.
- Translate each option's label naturally into {language_name}.
- Keep every option id EXACTLY as given, in EXACTLY the same order.

Reply with exactly this JSON shape:
{{"question_id": "{question_id}", "language": "{language}", "message": "<the question, in {language_name}>", "options": [{{"id": "<the exact id given>", "label": "<that option's label, in {language_name}>"}}]}}

Rules:
- You MUST include every option that was given, exactly once, in the same order.
- You MUST NOT add, remove, merge, reorder or invent any option.
- Option ids are opaque identifiers: copy them character-for-character. Never translate or alter an id.
- Proper nouns (brand names such as LG, Samsung, Voltas) stay as-is; do not transliterate them unless that is genuinely how they are written in {language_name}.
- Do not answer the question, do not add advice, do not ask anything new.
- Do not mention that you are an AI or any internal system.
- question_id must be exactly "{question_id}".
- language must be exactly "{language}".
"""


def _cache_key(question_id: str, language: str, message: str, options: list[dict]) -> str:
    """Question version + option version + language, per spec. Hashing the
    real canonical CONTENT (rather than an updated_at column) means an
    admin editing a label invalidates the cache automatically, with no
    separate version bookkeeping to keep in sync."""
    payload = json.dumps(
        {"q": question_id, "l": language, "t": message,
         "o": [[str(o.get("id")), o.get("label")] for o in options]},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical(question: dict, language: str) -> dict:
    """The always-safe presentation: the backend's own text and labels,
    untranslated. Returned whenever DeepSeek is unavailable or returns
    anything that fails validation."""
    return {
        "question_id": question["question_id"],
        "language": language,
        "message": question["text"],
        "options": [
            {"id": o.get("id"), "label": o.get("label")}
            for o in (question.get("options") or [])
        ],
        "presented_by": "canonical",
    }


def _validate(parsed: Any, question: dict, language: str) -> dict | None:
    """Every mandatory check from the spec. Returns the customer-safe
    presentation dict on success, or None to fail closed.

    Deliberately strict: option identity is compared as an ORDERED list of
    ids, which simultaneously rejects additions, removals, duplicates and
    reordering in one comparison."""
    if not isinstance(parsed, dict):
        return None

    # Question identity -- DeepSeek can never present a different question.
    if parsed.get("question_id") != question["question_id"]:
        return None

    # Language identity -- never present in a language the customer did
    # not choose.
    if parsed.get("language") != language:
        return None

    message = parsed.get("message")
    if not isinstance(message, str) or not message.strip():
        return None

    allowed = question.get("options") or []
    returned = parsed.get("options")
    if not isinstance(returned, list) or len(returned) != len(allowed):
        return None

    allowed_ids = [str(o.get("id")) for o in allowed]
    returned_ids = [str(o.get("id")) for o in returned if isinstance(o, dict)]
    # Exact ordered equality: no add, no remove, no duplicate, no reorder.
    if returned_ids != allowed_ids:
        return None

    options: list[dict] = []
    for canonical_option, presented in zip(allowed, returned):
        label = presented.get("label")
        if not isinstance(label, str) or not label.strip():
            # A blank/missing translated label falls back to the canonical
            # one for THAT option rather than discarding the whole
            # presentation -- the ids are already proven correct.
            label = canonical_option.get("label")
        options.append({"id": canonical_option.get("id"), "label": label})

    return {
        "question_id": question["question_id"],
        "language": language,
        "message": message.strip(),
        "options": options,
        "presented_by": "deepseek",
    }


class QuestionPresentationService:
    """Presents an already-selected canonical question in the customer's
    chosen conversation language. Never selects, validates, stores or
    advances anything."""

    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db = db
        self.request_id = request_id

    async def present(
        self,
        *,
        question: dict,
        language: str,
        session_id: str | None = None,
    ) -> dict:
        """`question` is the `current_question` block of a real
        question-flow envelope (see QuestionFlowService._build_envelope).

        Always returns a presentation dict -- never raises for a DeepSeek
        problem, and never returns something that contradicts the backend.
        """
        if not question or not question.get("question_id"):
            raise ServiceOSException(
                "QP_NO_QUESTION",
                "There is no active question to present right now.",
                status_code=422,
            )

        # English is the language the catalog is already authored in --
        # translating it round-trip would risk drift for zero benefit.
        # An unsupported code is treated the same way: present canonically
        # rather than guess.
        if language == "en" or language not in SUPPORTED_PRESENTATION_LANGUAGES:
            return _canonical(question, language)

        options = question.get("options") or []
        key = _cache_key(question["question_id"], language, question["text"], options)
        cached = _PRESENTATION_CACHE.get(key)
        if cached is not None:
            return {**cached, "presented_by": "cache"}

        prompt = _SYSTEM_PROMPT.format(
            language=language,
            language_name=_LANGUAGE_NAMES.get(language, language),
            question_id=question["question_id"],
        )
        payload = {
            "question": {
                "id": question["question_id"],
                "text": question["text"],
                "type": question.get("question_type"),
                "required": question.get("required"),
            },
            "allowed_options": [{"id": o.get("id"), "label": o.get("label")} for o in options],
        }

        client = DeepSeekClientService(db=self.db, session_id=session_id, request_id=self.request_id)
        try:
            raw = await client.chat(messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ])
            parsed = json.loads(raw["choices"][0]["message"]["content"])
        except (ServiceOSException, KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            # Timeout, network failure, malformed output -- all identical
            # from the customer's point of view: they see the real
            # question, just untranslated. Logged customer-safely (ids and
            # a reason class only, never draft or customer content).
            logger.info(
                "question_presentation.fell_back",
                request_id=self.request_id, question_id=question["question_id"],
                language=language, reason=type(exc).__name__,
            )
            return _canonical(question, language)

        validated = _validate(parsed, question, language)
        if validated is None:
            logger.info(
                "question_presentation.rejected",
                request_id=self.request_id, question_id=question["question_id"],
                language=language, reason="failed_validation",
            )
            return _canonical(question, language)

        if len(_PRESENTATION_CACHE) >= _PRESENTATION_CACHE_MAX:
            _PRESENTATION_CACHE.clear()
        _PRESENTATION_CACHE[key] = validated
        return validated


async def present_envelope(
    db: AsyncSession,
    envelope: dict,
    language: str | None,
    *,
    session_id: str | None = None,
    request_id: str = "—",
) -> dict:
    """Attach a language presentation to a real question-flow envelope.

    Only the DISPLAY fields (`current_question.text` and each option's
    `label`) are replaced. Every semantic field -- `question_id`,
    `question_key`, `question_type`, `required`, option `id`s and their
    order, progress, `next_permitted_actions` -- is passed through
    untouched, and `_validate` has already proven the presented option ids
    are identical (same ids, same order, none added or removed). That
    means the client submits exactly the same canonical ids it always did,
    so translation can never change what the customer actually answers.

    The original English text is preserved on `canonical_text` /
    `canonical_label` so any surface that needs the authored wording (logs,
    admin views, the immutable answer snapshot) still has it.
    """
    question = (envelope or {}).get("current_question")
    if not question or not language:
        return envelope

    svc = QuestionPresentationService(db=db, request_id=request_id)
    presentation = await svc.present(question=question, language=language, session_id=session_id)

    if presentation.get("presented_by") == "canonical":
        # Nothing was translated -- leave the envelope byte-identical
        # rather than adding misleading "canonical_*" echo fields.
        return envelope

    presented_labels = {str(o.get("id")): o.get("label") for o in presentation.get("options") or []}
    new_question = {
        **question,
        "text": presentation["message"],
        "canonical_text": question["text"],
        "options": [
            {**o, "label": presented_labels.get(str(o.get("id")), o.get("label")),
             "canonical_label": o.get("label")}
            for o in (question.get("options") or [])
        ],
        "presented_language": language,
        "presented_by": presentation.get("presented_by"),
    }
    return {**envelope, "current_question": new_question}
