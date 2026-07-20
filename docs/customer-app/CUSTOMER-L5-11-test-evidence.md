# CUSTOMER-L5-11 — Test Evidence

```
npx jest
Test Suites: 85 passed, 85 total
Tests:       584 passed, 584 total
```

(564 at the start of this sprint; net +20 new tests.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/booking-confirmation/domain/__tests__/review-schema.test.ts` | 4 | real fully-ready summary, real not-ready summary with only the guaranteed field, missing `ready_for_confirmation` fails closed, malformed payload fails closed |
| `features/booking-confirmation/domain/__tests__/booking-schema.test.ts` | 8 | real first-time confirm response, real smaller idempotent-retry response, malformed confirm response fails closed; real found/error(not-found)/error(access-denied)/malformed booking-detail shapes, and the critical `internal_score`/`matching_score_snapshot`-stripping test |
| `features/booking-confirmation/domain/__tests__/booking-state.test.ts` | 8 | every real `ReviewState` transition (preflight_failed, loading×2, unavailable, ready, not_ready) and every real `categorizeConfirmFailure` classification (6 uncertain categories, 4 failed categories) |
| `navigation/__tests__/route-registry.test.ts` (extended) | 2 | `bookingReview`/`bookingSuccess` promoted to real/production; `bookingsList`/`bookingDetail` remain dev-only, explicitly noted as unrelated to the legacy `/v1/bookings` screens |

## Regression Confirmation

All 564 tests carried forward from before this sprint continue passing
unmodified, confirming the route-registry/route-types/MainNavigator
changes (`bookingReview`/`bookingSuccess` production promotion, new
`BookingReviewScreen`/`BookingConfirmationScreen`, removed
`BookingReviewBoundaryPlaceholderScreen`), `BargainScreen`'s unchanged
navigation target (already correct from L5-10), and the new
`features/booking-confirmation/` module (which reuses
`features/pricing/`'s `evaluatePricingPreflight` and
`features/provider-matching/`'s `matchedProviderSchema` directly rather
than duplicating them) introduced no regressions across
Home/Category/Service/Search/Assistant/Draft/Media/Address/
Serviceability/ProviderMatching/Pricing/Bargain/Auth/deep-links/
remote-config — all unmodified this sprint and all still green.

## Not Covered This Pass

- No component/render tests for `BookingReviewScreen`/
  `BookingConfirmationScreen` — consistent with every previous sprint's
  identical, explicitly-documented deprioritization.
- No test exercises `booking-confirmation-api.ts`'s URL/header
  construction directly — consistent with the established pattern that
  thin `*-api.ts` wrappers are not independently unit-tested.
- No test exercises `use-booking-review.ts`/`use-confirm-booking.ts`'s
  hook composition directly — thin compositions of already-tested pure
  functions over already-tested query hooks, same prioritization as
  every previous sprint's identical hooks.
- No live runtime proof — see `CUSTOMER-L5-11-runtime-evidence.md`.
- No genuine duplicate-submission/timeout-reconciliation/two-device test
  against a live backend (would require a real seeded draft and database
  — see runtime-evidence.md).
- No true multi-customer isolation test against a real backend (only the
  backend's own source-verified ownership checks are covered, matching
  every previous sprint's identical constraint).
