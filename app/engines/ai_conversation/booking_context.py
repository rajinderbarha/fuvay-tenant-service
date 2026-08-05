"""LEVEL-5 REMEDIATION (2026-08-01) — Server-authoritative booking context.

Confirmed live (see docs/backend/ai-booking-assistant-canonical.md): DeepSeek
has no persisted memory of tool-call results across turns (only final
plain-text replies are saved to conversation history), so it would
re-derive/re-fetch static facts (categories, offerings, job-type options,
even the draft it already started) on every turn — wasting tool-call
budget and, before the draft-dedup fix, creating duplicate draft rows.

This module is the fix at the correct layer: a compact, server-owned
context object persisted on `AIConversationSession.context_data`, updated
by the backend tool executor after each tool call, and re-injected into
the system prompt every turn. DeepSeek is TOLD what it already knows
instead of being expected to remember it — the backend remains the single
source of truth, never the LLM's own recollection.

This is explicitly NOT solved by raising MAX_TOOL_ITERATIONS again — that
only delays the same problem. A stale/incomplete context here still fails
safe: any tool call always re-validates against the real database (this is
a hint to reduce redundant calls, not a trust boundary).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any

STATIC_CACHE_TTL_SECONDS = 900  # 15 minutes — categories/offerings/job-types change rarely

_utcnow = lambda: datetime.now(timezone.utc)


def _scope_key(category_id: str | None, offering_id: str | None, zipcode: str | None) -> str:
    return f"{category_id or ''}|{offering_id or ''}|{zipcode or ''}"


def get_booking_context(session) -> dict[str, Any]:
    return dict((session.context_data or {}).get("booking_context") or {})


def _is_fresh(entry: dict | None, ttl_seconds: int = STATIC_CACHE_TTL_SECONDS) -> bool:
    if not entry or not entry.get("cached_at"):
        return False
    try:
        cached_at = datetime.fromisoformat(entry["cached_at"])
    except (ValueError, TypeError):
        return False
    return (_utcnow() - cached_at) < timedelta(seconds=ttl_seconds)


def get_cached(ctx: dict, key: str, ttl_seconds: int = STATIC_CACHE_TTL_SECONDS) -> Any | None:
    """Returns the cached value for `key` if still fresh, else None."""
    entry = ctx.get(key)
    if _is_fresh(entry, ttl_seconds):
        return entry.get("value")
    return None


def set_cached(ctx: dict, key: str, value: Any) -> dict:
    ctx = dict(ctx)
    ctx[key] = {"value": value, "cached_at": _utcnow().isoformat()}
    return ctx


def update_booking_context(session, **updates: Any) -> dict:
    """Merge `updates` into the session's booking_context, applying scope-
    change invalidation (ZIP/category/offering change clears job-type and
    question-flow state, since those are only valid for the prior scope).
    Does not commit — caller is expected to commit the surrounding
    transaction (the tool executor already flushes/commits its own writes).
    """
    ctx = get_booking_context(session)

    # CUSTOMER WORKFLOW REGRESSION CLOSURE (2026-08-01): confirmed live this
    # was a critical bug — `updates.get("zipcode", ctx.get("zipcode"))`
    # returns None (not the fallback) whenever a caller passes `zipcode=None`
    # explicitly (the key is PRESENT, just with a None value — dict.get only
    # falls back when the key is ABSENT). Every tool that always passes
    # zipcode/category_id/offering_id as kwargs (even when it has nothing
    # new to report) was silently computing a different scope_key each
    # call, triggering the scope-change invalidation branch below and
    # wiping draft_id/job_type_id/current_question on almost every turn.
    #
    # `current_question` is the one field where None is itself meaningful
    # ("question collection is complete" — not "nothing to report this
    # call"), so it's handled separately from the generic None-means-
    # unchanged filtering applied to every other field.
    has_current_question_update = "current_question" in updates
    current_question_value = updates.pop("current_question", None)
    clean_updates = {k: v for k, v in updates.items() if v is not None}

    new_category = clean_updates.get("category_id", ctx.get("category_id"))
    new_offering = clean_updates.get("offering_id", ctx.get("offering_id"))
    new_zipcode = clean_updates.get("zipcode", ctx.get("zipcode"))
    new_scope_key = _scope_key(new_category, new_offering, new_zipcode)
    old_scope_key = ctx.get("scope_key")

    if old_scope_key and old_scope_key != new_scope_key:
        # Scope changed (customer switched service, category, or moved to a
        # different ZIP) — the job-type/question-flow state resolved under
        # the OLD scope is no longer valid. Drop it; the assistant must
        # re-resolve job type and questions for the new scope. draft_id is
        # deliberately also cleared: a scope change means a different
        # offering/location, which start_home_service_draft's own
        # ai_session_id dedup would otherwise incorrectly keep reusing.
        for stale_key in (
            "draft_id", "job_type_id", "job_type_options", "current_question",
            "completed_question_ids", "question_flow_version", "catalog_version",
        ):
            ctx.pop(stale_key, None)

    ctx["scope_key"] = new_scope_key
    ctx.update(clean_updates)
    if has_current_question_update:
        # Applied last and unconditionally (even if None) so a freshly-
        # resolved "no more questions" state is never masked by the
        # scope-invalidation pop above, and never silently dropped by the
        # generic None filter.
        ctx["current_question"] = current_question_value

    session.context_data = {**(session.context_data or {}), "booking_context": ctx}
    return ctx


def format_context_for_prompt(ctx: dict) -> str:
    """Compact, bracketed context block injected into the system prompt.
    Tells DeepSeek what it already has — explicit instruction not to
    re-fetch these via tool calls unless the customer changes location or
    service."""
    if not ctx:
        return ""

    lines = ["[BOOKING CONTEXT — already known, do NOT re-fetch via tools unless customer changes ZIP/service]"]
    if ctx.get("category_slug") or ctx.get("offering_slug"):
        lines.append(f"category={ctx.get('category_slug')} offering={ctx.get('offering_slug')}")
    if ctx.get("zipcode"):
        lines.append(f"zipcode={ctx.get('zipcode')} city={ctx.get('city')}")
    if ctx.get("draft_id"):
        lines.append(f"draft_id={ctx['draft_id']} (already started — do NOT call start_home_service_draft again)")
    if ctx.get("job_type_id"):
        lines.append(f"job_type_id={ctx['job_type_id']} (already resolved — do NOT call get_home_service_job_type_options again)")
    elif ctx.get("job_type_options", {}).get("value"):
        opts = ", ".join(f"{o['label']}={o['job_type_id']}" for o in ctx["job_type_options"]["value"][:5])
        lines.append(f"available job types (already fetched): {opts}")

    current_q = ctx.get("current_question")
    if current_q:
        opts_str = ", ".join(f"{o['label']}={o['id']}" for o in current_q.get("options", []))
        lines.append(
            f"current_question: id={current_q['question_id']} text=\"{current_q['text']}\" "
            f"type={current_q['question_type']} required={current_q['required']} options=[{opts_str}] "
            "(phrase THIS question next — do NOT call get_home_service_question_flow again unless "
            "you need to refresh after a scope change)"
        )
    elif ctx.get("job_type_id"):
        lines.append("current_question=null (question collection complete for this draft) — "
                      "tell the customer their request is ready.")

    return "\n".join(lines)
