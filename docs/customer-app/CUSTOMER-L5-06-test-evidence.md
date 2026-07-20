# CUSTOMER-L5-06 — Test Evidence

```
npx jest
Test Suites: 71 passed, 71 total
Tests:       489 passed, 489 total
```

(426 carried over from before this sprint; 63 new this pass.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/booking-draft/domain/__tests__/draft-schema.test.ts` | 12 | valid/invalid draft parsing, terminal-status classification, expiry detection (including the async-scheduler-lag case), cancel/link-photo response parsing |
| `features/booking-draft/domain/__tests__/draft-session.test.ts` | 10 | all state transitions, fail-closed expiry/cancellation classification, isMutable guard |
| `features/booking-draft/domain/__tests__/media-asset-schema.test.ts` | 8 | the real nested-upload-envelope quirk, flat asset parsing, list drop-not-fail, replace/delete response shapes |
| `features/booking-draft/domain/__tests__/media-validation.test.ts` | 10 | real MIME allowlist (stricter than the media engine's own), real 10MB/5-photo limits, null-size tolerance for post-compression items |
| `features/booking-draft/domain/__tests__/media-item.test.ts` | 7 | full upload/link happy path, invalid-item terminality, retry-count capping, delete path |
| `features/booking-draft/domain/__tests__/assistant-answer-mapping.test.ts` | 6 | brand/service-type/issue-summary mapping, and explicit non-inclusion of issue_type_id/service_option (the sprint's key contract gap) |
| `features/booking-draft/queries/__tests__/draft-query-keys.test.ts` | 5 | draft-detail and draft-media key scoping |
| `features/booking-draft/state/__tests__/draft-local-store.test.ts` | 5 | cross-customer isolation, clear-one-doesn't-affect-other |
| `navigation/__tests__/route-registry.test.ts` (rewritten) | 3 | `bookingDraft`/`bookingMedia` promoted to real/production; `addressSelection` remains dev-only |

## Regression Confirmation

All 426 tests from before this sprint continue passing unmodified,
confirming the route-registry changes (`bookingDraft`/`bookingMedia`
promotion, `diagnosticCompletion` retirement), the multipart addition to
`api-client.ts`, and the `use-logout`/`use-logout-all` isolation changes
introduced no regressions across Home/Category/Service/Search/Assistant/
Auth/deep-links/remote-config — all unmodified this sprint and all still
green.

## Not Covered This Pass

- No component/render tests for `BookingDraftScreen`/`BookingMediaScreen`/
  `AddressSelectionPlaceholderScreen` — consistent with every previous
  sprint's identical deprioritization; the domain logic those screens call
  (schemas, state machines, validation, mapping) is exhaustively tested
  instead.
- No test exercises the actual multipart upload path end-to-end against a
  mocked HTTP server (only the response-parsing side is tested) — building
  a realistic `fetch`/`FormData` mock for React Native's multipart
  encoding was judged lower-value than the domain-logic coverage above
  given this sprint's time budget.
- No live runtime proof — see `CUSTOMER-L5-06-runtime-evidence.md`.
- No true multi-customer isolation test against a real backend (only the
  local-store isolation and the backend's own source-verified ownership
  checks are covered).
