# CUSTOMER-L5-05 — Test Evidence

```
npx jest
Test Suites: 63 passed, 63 total
Tests:       425 passed, 425 total
```

(370 at the start of this sprint; 59 new/rewritten this pass.)

## New and Rewritten Test Files

| File | Count | Covers |
|---|---|---|
| `features/booking-assistant/domain/__tests__/diagnostic-catalog-schema.test.ts` | 10 | issue-type/service-option/brand/service-type parsing, per-item drop-not-fail, unsafe logo URL rejection, malformed envelopes |
| `features/booking-assistant/domain/__tests__/assistant-steps.test.ts` | 12 | `buildBaseStepOrder` per-gate combinations, `deriveSteps` branch insertion/dedup/no-op cases |
| `features/booking-assistant/domain/__tests__/assistant-session.test.ts` | 17 | full state machine: creation, submit (advance + fail-closed), previous-step, revision (incl. issue_type branch clearing), progress honesty, completion, question-type lookup, ordered history |
| `features/booking-assistant/domain/__tests__/answer-normalization.test.ts` | 8 | canonical-vs-label distinction, order preservation, text trim/control-char-strip/length-cap, Hindi/Punjabi preservation, information acknowledgement |
| `features/booking-assistant/domain/__tests__/question-renderer-registry.test.ts` | 3 | all 4 supported types recognized, unknown type and empty string fail closed |
| `features/booking-assistant/queries/__tests__/assistant-query-keys.test.ts` | 5 | category/locale/tenant scoping, catalog-kind distinctness |
| `navigation/__tests__/route-registry.test.ts` (new) | 2 | `bookingAssistant` promoted to real/authenticated/production; `diagnosticCompletion` correctly dev-only |
| `features/service-detail/domain/__tests__/booking-boundary.test.ts` (rewritten) | 2 | simplified two-outcome boundary (dev-gate removed, matching the real, now-production `bookingAssistant` route) |

## Regression Confirmation

All 368 tests carried forward from before this sprint's route changes
continue passing, confirming: the `bookingAssistant`/`diagnosticCompletion`
route-registry changes, the `BookingAssistantPlaceholderScreen` removal, and
the `booking-boundary.ts` signature change introduced no regressions
elsewhere (Home, Category, Service, Search, Auth, deep links, remote
config, startup — all unmodified this sprint and all still green).

## Not Covered This Pass

- No component/render tests for `BookingAssistantScreen`,
  `DiagnosticCompletionScreen`, or the four question-renderer components
  themselves (`SingleSelectRenderer`, `MultiSelectRenderer`,
  `ShortTextRenderer`, `InformationRenderer`) — consistent with every
  previous sprint's identical deprioritization of screen/component render
  tests in favor of pure-logic coverage; the state machine and
  normalization logic those components call are exhaustively tested
  instead.
- No true integration test mocking only the HTTP boundary across the full
  ServiceDetail → BookingAssistant → DiagnosticCompletion chain in one test.
- No live runtime proof — see `CUSTOMER-L5-05-runtime-evidence.md`.
- No multi-tenant isolation test with real data (single-tenant sandbox,
  same constraint as every previous sprint).
- No test exercising the offline path for this screen specifically (no
  `OfflineBanner` was added — see known-gaps.md).
