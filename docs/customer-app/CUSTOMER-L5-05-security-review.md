# CUSTOMER-L5-05 — Security Review

## Sensitive Answers

`issue_description` and `customer_note` (both `SHORT_TEXT`) are the only
customer-authored free-text fields in this sprint — potentially revealing
property/issue details. Verified by grep across
`features/booking-assistant/`: every `logger.*` call passes only
`stepId`/`optionId`/`stepCount`/`stepIndex`/`droppedCount` — never
`record.canonicalAnswer` or `record.displaySummary`. `diagnostic_answer_selected`
only fires for `SINGLE_SELECT` (`issue_type`), logging the selected
`optionId` (a stable backend ID, not free text) — never for `SHORT_TEXT`
submissions.

No route param, deep link, or navigation call ever carries an answer value
— `BookingAssistantScreen`/`DiagnosticCompletionScreen` navigation only
ever passes `{ serviceId, categoryId }`, both already-validated branded IDs.

## No Persistent Storage of Answers

The entire `AssistantSessionState` — including every `AnswerRecord` — lives
in a single `useState` inside `useBookingAssistant`, scoped to the
`BookingAssistantScreen` component instance. It is never written to
`AsyncStorage`, `SecureStore`, or any React Query cache. Unmounting the
screen (navigating away, backgrounding long enough for React Navigation to
tear down the stack, or a full app restart) discards it completely — there
is no explicit "clear" step needed because there is nothing durable to
clear, which is a stronger isolation guarantee than an explicit-clear
pattern that could be forgotten.

## Cross-Customer / Cross-Tenant Isolation

- **Session state**: structurally impossible to leak across customers or
  accounts, per the "no persistent storage" point above — a `logout` or
  account switch that unmounts `BookingAssistantScreen` (which
  `queryClient.clear()` and `reevaluateStartup()` already force, per
  CUSTOMER-L5-02) takes the in-memory session with it.
- **Catalog queries** (`assistant-queries.ts`): scoped by
  `(categoryId, locale, tenantId)`, matching CUSTOMER-L5-04's identical
  category/service query-key pattern. These are public catalog reads (no
  auth dependency on the backend routes — confirmed by reading
  `service_option_customer_router.py`/`customer_router.py`), so there is no
  customer-specific data in them to leak in the first place; `tenantId` is
  included defensively for forward-compatibility, same rationale as
  CUSTOMER-L5-04's documented approach.

## Tampering Resistance

- `submitAnswer` fails closed to `ERROR` if the submitted `stepId` does not
  match the actual current step — a stale or replayed submission (e.g. from
  a double-tap racing a state update) cannot silently apply to the wrong
  step.
- Option IDs submitted are always taken from the renderer's own fetched
  `options` array (never freely typed or constructed by the caller), so an
  "option from another question" cannot be fabricated client-side — though
  since there is no backend answer-submission endpoint to validate against
  server-side either, this is a UI-level guarantee only, not a
  cryptographic one. Documented honestly as a gap in known-gaps.md.

## Untrusted Content

Brand `logo_url` reuses the same `httpsOrRelativeImageUrl`-style validation
pattern as CUSTOMER-L5-03/04's category/service images
(`brand-schema.ts`'s zod refinement) — rejects non-`https://`/non-relative
schemes. All other rendered text (issue-type names, option names, brand
names) is plain `AppText`, never interpreted as markup.

## Analytics

Verified real, privacy-safe events wired: `diagnostic_answer_selected`
(single-select only, option ID), `diagnostic_completed` (step count only),
`diagnostic_exited` (step index only). As with every previous sprint, no
analytics SDK is actually integrated in this app — these are structured
`logger.*` calls only, not delivered to a vendor (see known-gaps.md, same
pattern as CUSTOMER-L5-04's own documented gap).

## No Production Mocks

Grepped `features/booking-assistant/` for `mock`, `fake`, `TODO`, `FIXME`,
hardcoded issue-type/option/brand names — none found. Every rendered option
traces to a real, schema-validated backend response.
