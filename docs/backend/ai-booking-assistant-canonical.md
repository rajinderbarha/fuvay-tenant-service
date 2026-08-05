# Canonical Customer Booking Assistant — Decision Record

**Status:** Active decision, effective 2026-08-01 (Level-5 remediation).
**Supersedes:** informal usage of `ai_chat` and `ai_conversation` Sprint-29 for new customer booking work.

## Decision

The **canonical customer booking assistant is `app.engines.ai_conversation`'s Sprint-15 session/message surface**:

- Routes: `POST/GET /v1/customer/ai-chat/sessions*` (`app/engines/ai_conversation/customer_router.py`)
- Service: `AIConversationService` (`app/engines/ai_conversation/service.py`)
- Models: `AIConversationSession`, `AIConversationMessage`, `AIWorkflowState`, `AIPromptTemplate`, `AILLMCallLog`, `AIToolCallLog`, `AIConversationAuditLog`

All new customer-app AI chat / guided-booking UI must be built against this surface only.

## Why this one

| Criterion | `ai_chat` (`/v1/ai/chat`) | `ai_conversation` Sprint-15 (`/v1/customer/ai-chat`) | `ai_conversation` Sprint-29 (`/v1/customer/ai`) |
|---|---|---|---|
| Session persistence | None (stateless per-call, client resends history) | Real (`AIConversationSession`, resumable via `session_key`) | Same tables as Sprint-15 (shares `AIConversationService`) |
| Backend booking-draft integration | None | Via `BackendToolExecutor` → real `home_service_booking`/pricing tools | Same tool executor |
| Structured validation | None | Regex-based `safety.py` (now extended, see below) | A stronger JSON-contract validator exists (`validation_service.py`) but was never wired into the live path |
| Test coverage | 12 tests, mostly structural | 53 tests after this remediation (was 45) | 38 tests, but the actual message-send handler had a live signature-mismatch bug (G5) masked by a broad `except` |
| Known defects | Hardcoded price/catalog/slot fabrication (G7 — fixed this pass) | None found | `send_ai_message` called `send_message(message=...)` against a real signature of `user_message=` — guaranteed `TypeError`, silently swallowed (G5 — fixed this pass) |
| Migration risk of choosing this one | N/A (deprecated) | Lowest — already functional, already has the real session/message tables | N/A (compatibility layer) |

## What changed in this remediation (2026-08-01)

1. **`ai_chat` deprecated for customer booking use** (`app/engines/ai_chat/router.py`) — `deprecated=True` on the route, docstring explains why. Left mounted (other callers not fully ruled out — see Removal Timeline) but must not be used for new customer flows.
2. **`ai_conversation` Sprint-29 (`/v1/customer/ai/*`) marked as a compatibility layer**, not canonical — all 6 routes now carry `deprecated=True`. Its `send_ai_message` signature bug (G5) is fixed (`user_message=` not `message=`), with a regression test (`test_send_ai_message_calls_service_without_typeerror` in `tests/test_sprint29_ai_marketing.py`) that would have caught the original bug.
3. **The dormant `AIWorkflowState` FSM is now wired into the live `send_message` path** (`AIConversationService.send_message`, `service.py`) — every turn resolves/creates a workflow state (mapped from detected intent → `service_booking`/`status_check`/`complaint`/`general`) and injects `[WORKFLOW STEP]`/`[STILL NEEDED]` context into the DeepSeek prompt. This closes G11 (the FSM existed in code but was never invoked).
4. **Real prompt-injection enforcement** (`safety.py`): hard-block patterns (`ignore previous instructions`, `reveal your instructions`, `jailbreak`, etc.) now refuse the message outright *before* any DeepSeek call, instead of the prior "detect, log, forward unmodified" behavior. Softer patterns are still logged/audited but allowed through (avoids over-blocking ordinary service language).
5. **Server-side, dynamic out-of-scope refusal**: if a message's detected intent is `unknown` and the session has a bound `category_id`, the backend refuses without ever calling DeepSeek, quoting the session's own category name + ZIP (e.g. *"I can only help with AC & Cooling services available in 141002."*) — never hardcoded to one vertical/location.
6. **Plain-text price/provider-claim scrubbing** ported into `validate_assistant_reply` (previously only scanned JSON code-fence blocks) — a reply like *"that will cost ₹499"* is now scrubbed to `[price from backend]` regardless of which engine produced it.
7. **Tool-name and tool-argument allowlisting**: only tool names present in the `BACKEND_TOOLS` contract sent to DeepSeek may execute; unrecognized names are refused (`{tool}(blocked)`) and malformed JSON arguments are refused (`(malformed_args)`) rather than crashing or executing with bad input.
8. **DeepSeek call timeout** (`DEEPSEEK_TIMEOUT_S`, 30s) via `asyncio.wait_for` — a hung call now degrades to a safe "taking a bit long" response instead of hanging the request indefinitely.

## Compatibility routes / deprecated routes / migration strategy

- **Compatibility (kept mounted, deprecated)**: `ai_conversation` Sprint-29 (`/v1/customer/ai/*`, `/v1/admin/ai/*`) — has rate-limit/reset/handoff/draft-status actions with no Sprint-15 equivalent yet. Delegates to the same `AIConversationService`/tables as Sprint-15, so there is no parallel booking-assistant *state* — only the route surface differs.
- **Deprecated (kept mounted)**: `ai_chat` (`/v1/ai/chat`, `/v1/ai/chat/meta`) — its own price/catalog/slot tools were fabricating data; now fixed to either query real models or return an honest "not available here" response (see Phase 5 below), but the engine's fundamental lack of booking-draft/session context means it should still not be used for new customer booking flows.
- **Known callers**: `mobile/customer-app/src/domain/capabilities/registry.ts` (a capability registry inside the in-progress customer-app redesign) already flags this exact ambiguity ("TWO parallel AI session surfaces are mounted... backend must confirm which is canonical") and cites the deprecated `match-providers` booking endpoint as canonical (it isn't — `match-and-price` is, see `home_service_booking/customer_router.py`). This decision record and the `deprecated=True` route metadata are the answer to that open question.
- **Removal timeline**: not removing anything this pass — `Depends(get_tenant)`-style caller analysis for `ai_chat`/Sprint-29 was not exhaustively done beyond the customer-app registry reference above. Recommend a dedicated caller-census pass before deleting either surface.

## Deterministic question flow (Phase 3) — COMPLETE (2026-08-01, second pass)

Three mechanisms now exist, fully wired end-to-end:

1. **Catalog questions** (`app/engines/admin_catalog`) — fully deterministic, DB-configured, admin-editable (`CatalogQuestion`/`Option`/`Rule`, resolved via `CatalogQuestionService.resolve_applicable_questions`). Unchanged — already correct.
2. **`AIWorkflowState`** (`app/engines/ai_conversation`) — step-list FSM wired into the live chat path (see DeepSeek Scope Enforcement above) so the prompt reflects real backend state.
3. **`QuestionFlowService`** (`app/engines/home_service_booking/question_flow_service.py`, new) — the unified structured-question envelope that binds (1) to the canonical `HomeServiceBookingDraft`:
   - `GET /v1/customer/home-services/booking-drafts/{draft_id}/question-flow` — returns one versioned envelope: `envelope_version`, `session_id`, `draft_id`, `workflow_version`, `question_flow_version`, `scope` (category/offering/job_type ids), `current_question` (question_id, question_key, question_type, text, help_text, required, options, validation_metadata, photo_capable) or `null` if collection is complete, `progress` (answered/remaining/complete), `next_permitted_actions`.
   - `POST .../question-flow/answer` — body `{question_id, option_id?, value?, expected_version?}`. Validates the question_id against the currently-resolved applicable set (fails closed with `QF_QUESTION_NOT_APPLICABLE` if unknown/stale/already-answered), validates option_id against the question's own allowed options (`QF_INVALID_OPTION`), enforces required-field presence (`QF_ANSWER_REQUIRED`), and enforces optimistic concurrency via `expected_version`/`question_flow_version` (`QF_STALE_QUESTION_FLOW_VERSION`, 409) — a duplicate/stale submission is rejected, not silently re-applied.
   - Answers persist to `HomeServiceBookingDraft.catalog_question_answers` (new JSONB column, migration `220`), keyed by `question_key` (never free-form label) — re-evaluating dependent questions is automatic: every call re-resolves from scratch against the updated `prior_answers`, so a rule referencing an answer that just changed naturally reveals/hides the questions it gates.
   - Requires `draft.job_type_id` already resolved — fails closed (`QF_JOB_TYPE_REQUIRED`, 422) rather than guessing which question set applies.
   - 12 new tests (`tests/test_level5_question_flow_service.py`) covering: valid question returned, completion detection, missing-job-type fail-closed, cross-customer ownership denial, photo-question flagging, valid single/multi-select answers with version bump, invalid question id, invalid option id, missing required answer, stale version, and duplicate-submission-after-resolution rejection.

DeepSeek's role is now precisely bounded by this envelope: it may phrase `current_question.text` naturally and map a free-text reply onto one of `current_question.options`, but it cannot choose a different `question_id`, invent an `option_id`, or skip ahead — the `submit_answer` validation is the enforcement boundary, independent of whatever DeepSeek says.

## Price-hallucination removal (Phase 5)

All hardcoded customer-facing price/catalog/availability fabrication was removed from `app/engines/ai_chat/tools.py`:

- `_tool_get_price_estimate`: previously a static `PRICE_RANGES` dict (`AC Repair: 499–2499`, etc.) returned as if it were a real quote. Now returns `price_available: False` and an honest explanation — this engine has no bound booking/tenant context to resolve a real price against, so it must never invent one.
- `_tool_get_service_catalog`: previously a fully hardcoded `CATALOG` dict with fabricated visit fees/fixed prices/consultation fees per service. Now queries real `admin_catalog.ServiceCategory`/`MasterService` rows — names are real, no price figure is fabricated.
- `_tool_get_available_slots`: previously fabricated a rotating "available" time-slot pattern with a comment admitting `"Simulate some slots being taken"`. Now returns no slot data and an honest message directing the customer to the real booking flow.
- `_tool_get_active_job`: previously queried the dead `field_ops.Job` table (never written to by the home-services pipeline). Repointed to canonical `final_records.ServiceJob`.

`ai_conversation`'s own pricing tool (`backend_tools.py::_tool_get_home_service_price_estimate`) already correctly delegated to the real backend pricing service — no change needed there, confirmed via code read (not re-broken by this pass).

## Realtime transport (Phase 14)

No WebSocket implementation exists anywhere in this codebase (confirmed by exhaustive grep). `app/main.py`'s architecture docstring and `app/engine_registry/registry.py`'s chat-engine description previously claimed "WebSocket rooms per job/conversation" / "Real-time WebSocket messaging" — both corrected to describe the actual transport (HTTP polling) as of this remediation. Do not build a customer-app screen assuming push/typing-indicator/live-GPS behavior. If real-time transport becomes a launch requirement, that is a separate, larger decision requiring its own design — not expanded into this remediation.

## Consultation → repair linkage (Phase 15)

`CONSULTATION_TO_REPAIR_LINKAGE_ENABLED = False` (`app/engines/home_service_booking/constants.py`). Confirmed: `admin_catalog` allows configuring a service with `job_type="consultation"`, and `quote_checklist` supports a standalone consultation fee/quote, but no code anywhere spawns a linked/child repair `ServiceJob` from an approved consultation — there is no `parent_job_id`/`child_job_id` concept on `ServiceJob` at all (that field only exists on the disjoint legacy `field_ops.Job`). This is an explicit **product decision gap**, not a bug: classified `NOT_APPLICABLE` for the current launch. Do not design a "book a follow-up repair from this consultation" screen until a schema/migration/lifecycle plan is explicitly approved.

## Commission/credit double-charging (Phase 15)

Verified, not a defect: **usage-credit deduction** (`execution.usage_credit_deduction.deduct_for_completed_job`, fixed per-job amount, triggered by job **completion**) and **percentage commission** (`invoice_payment.commission_service.ServiceCommissionService`, writes `svc_commission_records`, triggered by the **on-site payment recording** flow) are two independently real, already-idempotent mechanisms tied to *different* events, not double-charging on the same event. `finance_hub/home_services_finance_service.py` already documents this explicitly ("Two independent provider-charge models coexist... neither writer changes"). No fix applied — an unnecessary fix was correctly avoided here per the audit-before-fix requirement.

## Legacy engine duplication — `review` vs `customer_reviews` (Phase 12 follow-up)

Resolved (2026-08-01): `app/engines/review` (mounted at `/v1/reviews`) is a **legacy engine scoped to `field_ops.Job`** — its own docstring states "the authoritative parent is `field_ops.Job` — established by the only internal caller (`field_ops.service` on job close)". `app/engines/customer_reviews` (mounted at `/v1/customer/reviews`) is the canonical home-services review engine. The two use disjoint route prefixes with no collision, and `review` never touches `final_records.ServiceJob` or any canonical home-services table — same clean separation pattern already confirmed for `booking`/`convert_to_job` and `dispatch`. **No fix required**; this was flagged as an open item in the initial audit but is now verified isolated, not broken.

## Language / chatbot scope (Phase 9) — COMPLETE (2026-08-01, second pass)

Per project direction, language selection belongs only inside the chatbot, never app-wide. `AIConversationSession.language` (new column, migration `221`, default `"en"`) is now a real, validated, session-level field:

- `AIConversationService.set_session_language(session_id, language)` validates against the **existing** `app.engines.profile.schemas.ALLOWED_LANGUAGES` (11 languages incl. Punjabi `pa`) rather than inventing a smaller list — an unsupported code is rejected (`AI_INVALID_LANGUAGE`, 422). Exposed via `PUT /v1/customer/ai-chat/sessions/{session_id}/language`.
- Changing language **never resets** `collected_fields`, `turn_count`, or any booking-draft state — verified by test.
- `send_message` injects a `[RESPOND IN LANGUAGE: {code}]` directive into the system prompt only when non-English — this affects DeepSeek's reply phrasing only. Question/option identifiers and all business validation remain entirely inside `QuestionFlowService`, which is completely independent of session language — the backend always validates answers using stable ids regardless of what language the customer is chatting in.
- No translation-confidence handling exists (DeepSeek is instructed to phrase naturally in the target language; there is no separate translation-confidence signal to fall back from) — if this becomes a real quality issue in production, add a confidence check before this directive is trusted, not assumed here.
- 5 new tests (in `tests/test_sprint15_ai_conversation.py::TestSessionLanguage`) covering: valid language update, invalid language rejection, collected_fields/turn_count preservation across a language change, Punjabi/Hindi/English all present in the allowed set, and the system-prompt directive actually appearing in the DeepSeek call payload.
