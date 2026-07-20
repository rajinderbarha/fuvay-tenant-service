# CUSTOMER-L5-09 — Test Evidence

```
npx jest
Test Suites: 80 passed, 80 total
Tests:       550 passed, 550 total
```

(526 at the start of this sprint; net +24 new tests, plus a rewrite of
`route-registry.test.ts`'s CUSTOMER-L5-07/L5-08-era `pricing`-remains-dev-only
assertions to match this sprint's real route promotion — no existing
assertions removed without a direct replacement covering the same fact.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/pricing/domain/__tests__/pricing-schema.test.ts` | 6 | real range-shape success, structural stripping of `area_market_comparison`/admin fields, malformed payload, missing required field, single-point-estimate detection (true/false cases) |
| `features/pricing/domain/__tests__/pricing-preflight.test.ts` | 6 | all-preconditions-met success, missing draft, expired draft, missing address, not-serviceable, provider-not-matched |
| `features/pricing/domain/__tests__/pricing-state.test.ts` | 12 | every state transition (preflight_failed, idle, calculating vs. revalidating, failed vs. unavailable, ready with revised true/false/unchanged), plus `priceOptionsEqual`'s three comparison cases |
| `navigation/__tests__/route-registry.test.ts` (extended) | 2 | `pricing` promoted to real/production; `bargain`/`bookingReview` remain the dev-only next boundaries |

## Regression Confirmation

All 526 tests carried forward from before this sprint continue passing
unmodified, confirming the route-registry/route-types changes (`pricing`
production promotion, `PricingBoundaryPlaceholderScreen` → real
`PricingEstimateScreen` swap, new `BookingReviewBoundaryPlaceholderScreen`),
`ProviderPreviewScreen`'s unchanged navigation target (already correct
from L5-08), and the new `features/pricing/` module introduced no
regressions across Home/Category/Service/Search/Assistant/Draft/Media/
Address/Serviceability/ProviderMatching/Auth/deep-links/remote-config —
all unmodified this sprint and all still green.

## Not Covered This Pass

- No component/render test for `PricingEstimateScreen` — consistent with
  every previous sprint's identical, explicitly-documented
  deprioritization; the domain logic the screen depends on (schema
  parsing, preflight evaluation, state derivation) is exhaustively tested
  instead.
- No test exercises `pricing-api.ts`'s URL construction directly —
  consistent with the established pattern that thin `*-api.ts` wrappers
  around `apiClient` are not independently unit-tested in this codebase
  (verified against `draft-api.ts`/`address-api.ts`/`provider-matching-api.ts`,
  none of which have one either).
- No test exercises `use-pricing-estimate.ts`'s hook composition directly
  (the auto-trigger effect, the `useRef`-based revision tracking across
  renders) — its logic is a thin composition of already-tested pure
  functions (`evaluatePricingPreflight`, `derivePricingState`) over
  already-tested query hooks; judged lower-value than the exhaustive
  domain-logic coverage above, consistent with every previous sprint's
  identical hook-vs-domain-logic prioritization.
- No live runtime proof — see `CUSTOMER-L5-09-runtime-evidence.md`.
- No test exercises a genuine backend-side price revision (would require a
  live backend with an editable seeded `BargainRule` — see
  runtime-evidence.md).
- No true multi-customer isolation test against a real backend (only the
  backend's own source-verified ownership check is covered, matching every
  previous sprint's identical constraint).
