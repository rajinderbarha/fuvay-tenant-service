# CUSTOMER-L5-05 — Assistant Architecture

## Canonical Ownership

There is no backend workflow engine (see contract-matrix.md). Canonical
ownership is therefore split honestly, not pretended away:

- **Backend** owns the real catalog data: which issue types, service
  options, and brands exist for a category, and the two real conditional
  flags (`requires_photo`, `requires_description`) on an issue type. It also
  owns whether a *step* is needed at all, via CUSTOMER-L5-04's already-real
  `ValidatedOfferingDetail.required_fields` (`requires_brand`, `requires_type`,
  `requires_customer_notes`, `requires_photo_upload`).
- **Mobile app** owns sequencing those real signals into a step order and
  tracking the customer's progress through them, entirely in memory, for the
  current app session only. This is not a fabricated "client-side branching
  engine" pretending to be backend-driven — it is the client's own,
  disclosed responsibility for a UI concern (question order) the backend
  does not concern itself with, exactly because the backend has no session
  concept to own it.
- **Remote configuration** is not consulted for canonical question content
  in this sprint — no module governs the assistant's availability beyond
  the route's own `access: "authenticated"` gate (see known-gaps.md for the
  pre-existing `featureKey` bug this sprint also fixed, mirroring
  CUSTOMER-L5-04's identical `service-discovery` fix).

## Entry Flow

```
ServiceDetailScreen ("Book service")
  → evaluateBookingBoundary({ authenticated }) → AVAILABLE | AUTH_REQUIRED
  → navigate("BookingAssistant", { serviceId, categoryId })
      → BookingAssistantScreen re-fetches the real service via
        useServiceDetail(categoryId, serviceId) — route params are never
        trusted alone (CUSTOMER-L5-05 §13)
      → useBookingAssistant() fetches the needed category-scoped catalogs
        and, once settled, creates the in-memory session exactly once
      → renders the current step via the renderer registry
      → on reaching "completion" → navigate("DiagnosticCompletion", ...)
        (dev-only placeholder — CUSTOMER-L5-06's real scope)
```

## Question Model

Not a backend-returned schema (none exists) — a small, closed, client-owned
union (`StepId`) mapped to a `QuestionType`
(`features/booking-assistant/domain/assistant-steps.ts`). Every step's
*options* come from real backend data; only the step's *existence and order*
is client-computed from real gates. See
`CUSTOMER-L5-05-question-renderer-registry.md` for the per-type contract.

## Answer Model

`AnswerRecord` (`domain/assistant-session.ts`): `stepId`, `questionType`,
`canonicalAnswer` (stable backend ID or normalized text — never a
translated label), `displaySummary` (locale-aware, display-only),
`submittedAt`. Normalization lives in `domain/answer-normalization.ts` —
one function per question type, each documented with what it strips/caps
and why (see CUSTOMER-L5-05 §22/§32/§53).

## State Machine

`AssistantSessionState` (`domain/assistant-session.ts`) — a small, pure,
fully-tested reducer-style module (no external state library):

```
status: "IDLE" | "READY" | "COMPLETED" | "ERROR"
```

`IDLE`/`INITIALIZING`/`SUBMITTING`/`BRANCHING`/`VALIDATION_ERROR`/`EXPIRED`/
`CANCELLED` from the spec's aspirational model were deliberately not
implemented as separate states: there is no backend round-trip to be
`SUBMITTING`/`INITIALIZING` for (all catalog fetches happen once, up front,
via `useBookingAssistant`, before the session object even exists), no
server branch evaluation to be `BRANCHING` for, no workflow to `EXPIRE`, and
no cancel endpoint to call for a formal `CANCELLED` state (exit is handled
by simple navigation plus a confirmation prompt, not a state transition).
Adding those states without real backend operations behind them would be
decorative complexity, not honest modeling.

Transitions (`domain/assistant-session.ts`, each pure and unit-tested):
`createAssistantSession`, `submitAnswer` (fails closed to `ERROR` if the
submitted `stepId` isn't the actual current step — CUSTOMER-L5-05 §61's
"QUESTION_NOT_CURRENT" concept, enforced entirely client-side since no
backend equivalent exists), `goToPreviousStep`, `reviseAnswer` (clears the
revised step and everything downstream, and — for `issue_type` specifically
— clears `selectedIssueType` so the branch recomputes cleanly),
`completeSession`.

## Branching

The only real branching in this sprint: `deriveSteps()`
(`domain/assistant-steps.ts`) inserts `issue_description` and/or
`photo_boundary` immediately after `issue_type` once its real
`requires_description`/`requires_photo` flags are known, and removes them
again if the customer revises `issue_type` to a different selection. See
`CUSTOMER-L5-05-branching-contract.md`.

## Completion Boundary

Reaching the final `"completion"` step navigates to `DiagnosticCompletion`
— a dev-only placeholder (`productionEnabled: false`), exactly mirroring
CUSTOMER-L5-04's own `BookingAssistantPlaceholderScreen` precedent for a
not-yet-built next stage. No booking draft is created, no data is persisted
beyond the current in-memory session, and no fake completion is claimed to
any backend.

## Cache and Isolation

The four catalog queries (`assistant-queries.ts`) are scoped by
`(categoryId, locale, tenantId)` — the same pattern as CUSTOMER-L5-04's
`categoryQueryKeys`. The in-memory session itself is not a React Query
cache entry at all — it lives in component state
(`useState` inside `useBookingAssistant`) and is discarded the moment the
screen unmounts, which is what makes cross-customer/account-switch leakage
structurally impossible for it (there is nothing to clear — see
security-review.md).

## Analytics and Accessibility

See `CUSTOMER-L5-05-security-review.md` for the privacy-safe event list and
sensitive-answer handling, and the component implementations themselves for
accessibility roles (`accessibilityRole="radiogroup"`/`"progressbar"`,
`accessibilityState={{ selected, disabled }}` on every option, a real
heading (`accessibilityRole="header"`) on every step so a screen reader's
focus has somewhere deliberate to land).
