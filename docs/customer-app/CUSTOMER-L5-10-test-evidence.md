# CUSTOMER-L5-10 — Test Evidence

```
npx jest
Test Suites: 82 passed, 82 total
Tests:       564 passed, 564 total
```

(550 at the start of this sprint; net +14 new tests — see below.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/bargain/domain/__tests__/bargain-schema.test.ts` | 5 | real `confirm-price-choice` success shape, all three real tier values, unrecognized tier fails closed, null optional fields accepted, malformed payload fails closed |
| `features/bargain/domain/__tests__/bargain-state.test.ts` | 8 | every real state transition (preflight_failed, loading_estimate, estimate_unavailable, choosing, confirming, confirm_failed, confirmed, and confirmed-takes-priority edge case) |
| `navigation/__tests__/route-registry.test.ts` (extended) | 2 | `bargain` promoted to real/production; `bookingReview` remains the dev-only next boundary |

## Regression Confirmation

All 550 tests carried forward from before this sprint continue passing
unmodified, confirming the route-registry/route-types/MainNavigator
changes (`bargain` production promotion, new `BargainScreen`, relocated
`BookingReviewBoundaryPlaceholderScreen`), `PricingEstimateScreen`'s one
navigation-target change (`"BookingReview"` → `"Bargain"`), and the new
`features/bargain/` module (which reuses `features/pricing/`'s
`useCalculatePriceEstimate`/`evaluatePricingPreflight` directly rather than
duplicating them) introduced no regressions across
Home/Category/Service/Search/Assistant/Draft/Media/Address/Serviceability/
ProviderMatching/Pricing/Auth/deep-links/remote-config — all unmodified
this sprint and all still green.

## Not Covered This Pass

- No component/render test for `BargainScreen` — consistent with every
  previous sprint's identical, explicitly-documented deprioritization; the
  domain logic the screen depends on (schema parsing, state derivation) is
  exhaustively tested instead.
- No test exercises `bargain-api.ts`'s URL/body construction directly —
  consistent with the established pattern that thin `*-api.ts` wrappers
  around `apiClient` are not independently unit-tested (verified against
  every previous sprint's identical `*-api.ts` files, none of which have
  one either).
- No test exercises `use-bargain.ts`'s hook composition directly (the
  auto-trigger effect, the `chooseTier`/`changeSelection` action wiring) —
  its logic is a thin composition of already-tested pure functions
  (`evaluatePricingPreflight`, `deriveBargainState`) over already-tested
  query hooks; same prioritization CUSTOMER-L5-09 already applied to
  `use-pricing-estimate.ts`.
- No live runtime proof — see `CUSTOMER-L5-10-runtime-evidence.md`.
- No test exercises a genuine "change selection then pick a different
  tier" round trip against a live backend (would require a real seeded
  `BargainRule` — see runtime-evidence.md).
- No true multi-customer isolation test against a real backend (only the
  backend's own source-verified ownership check is covered, matching
  every previous sprint's identical constraint).
- No counteroffer/attempt-limit/rate-limit tests exist — not a coverage
  gap, but a direct consequence of those capabilities being confirmed
  absent from the real backend (see `counteroffer-contract.md`/
  `attempt-and-rate-limit-policy.md`); there is nothing real to test.
