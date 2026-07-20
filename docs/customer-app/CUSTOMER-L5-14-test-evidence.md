# CUSTOMER-L5-14 — Test Evidence

```
npx jest
Test Suites: 95 passed, 95 total
Tests:       634 passed, 634 total
```

(617 at the start of this sprint; net +17 new tests, no existing
assertions removed or weakened.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/quote-decision/domain/__tests__/quote-schema.test.ts` | 9 | real multi-quote list parsing, per-quote resilience, malformed-envelope fail-safe, real quote-detail-with-items parsing, structural filtering of `is_customer_visible: false` items (real disclosed gap), structural exclusion of `provider_internal_notes`/`idempotency_key`/`locked_at`/`created_by_user_id`, per-item resilience, malformed-detail fail-safe, `toNumber` helper |
| `features/quote-decision/domain/__tests__/quote-state.test.ts` | 6 | `isQuoteActionable` true only for `sent_to_customer` across every other real status, `quoteStatusTitleKey` mapping + unknown-status fail-safe, `selectPrimaryQuote`'s actionable-first preference and most-recent fallback, empty-list case |
| `features/bookings/domain/__tests__/booking-status-registry.test.ts` (extended) | 2 new assertions folded into 1 new `it` | the four new real `quote_checklist`-engine statuses added this sprint |

## Pre-Existing Tests Corrected (Not Weakened)

None required changes this sprint — `quoteDecision` is a wholly new
route with no prior dev-only reservation to promote (unlike `tracking`
in CUSTOMER-L5-13), so no existing "remains dev-only" assertion needed
updating. `route-registry.test.ts` gained a new, additive describe
block; `route-guards.test.ts` was not touched (its stable disabled-route
example, `notifications`, remains disabled and unaffected).

## Regression Confirmation

All tests carried forward from before this sprint continue passing
unmodified — Home/Category/Service/Search/Assistant/Draft/Media/Address/
Serviceability/ProviderMatching/Pricing/Bargain/BookingConfirmation/
Bookings/ServiceTracking/Auth/deep-links/remote-config — all unmodified
this sprint beyond the described `booking-status-registry.ts` extension
and `BookingDetailScreen.tsx`'s action-row promotion, and all still
green.

## Not Covered This Pass

- No component/render tests for `QuoteDecisionScreen` — consistent with
  every previous sprint's identical, explicitly-documented
  deprioritization of screen-render tests in favor of domain-logic tests.
- No test exercises `quote-api.ts`'s URL construction directly, or
  `use-quote-decision.ts`'s hook composition directly, or
  `quote-queries.ts`'s cache-invalidation call sequence directly —
  consistent with the established pattern that thin API wrappers,
  hook-composition layers, and mutation-side-effect wiring over
  already-tested query hooks are not independently unit-tested.
- No live runtime proof — see `runtime-evidence.md`.
- No genuine end-to-end quote-decision test against a live backend (would
  require a real seeded job, a staff-created quote sent to the customer,
  and sequential real staff/customer endpoint calls).
- No test exercises the real opaque-500 behavior against a live server
  (verified by source reading only — see `financial-security-review.md`).
