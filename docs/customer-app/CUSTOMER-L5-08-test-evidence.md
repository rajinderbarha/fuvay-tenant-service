# CUSTOMER-L5-08 — Test Evidence

```
npx jest
Test Suites: 77 passed, 77 total
Tests:       526 passed, 526 total
```

(516 at the start of this sprint; net +10 new tests, plus a rewrite of
`route-registry.test.ts` adding a new `describe` block for the
`providerPreview` promotion — no existing assertions removed or weakened.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/provider-matching/domain/__tests__/provider-match-schema.test.ts` | 6 | real success shape, null rating, empty badges array, pricing-field-stripping (structural proof, not just a UI choice), malformed payload, missing `draft_status` |
| `features/provider-matching/domain/__tests__/badge-label-mapping.test.ts` | 2 | all three known badge strings map correctly; unrecognized string fails safe (returns null, logs once, never throws) |
| `navigation/__tests__/route-registry.test.ts` (extended) | 2 | `providerPreview` promoted to real/production; `pricing` remains dev-only next boundary |

## Regression Confirmation

All 516 tests carried forward from before this sprint continue passing
unmodified, confirming the route-type/route-registry changes
(`providerPreview`'s param shape correction, production promotion),
`ServiceabilityScreen`'s navigation-target change, and
`PricingBoundaryPlaceholderScreen`'s doc/copy update introduced no
regressions across Home/Category/Service/Search/Assistant/Draft/Media/
Address/Serviceability/Auth/deep-links/remote-config — all unmodified this
sprint (beyond the one-line navigation-target change) and all still green.

## Not Covered This Pass

- No component/render test for `ProviderPreviewScreen` — consistent with
  every previous sprint's identical, explicitly-documented
  deprioritization; the domain logic the screen depends on (schema
  parsing, badge mapping) is exhaustively tested instead.
- No test exercises `provider-matching-api.ts`'s URL construction directly
  — consistent with the established pattern that `*-api.ts` thin wrappers
  around `apiClient` are not independently unit-tested in this codebase
  (verified: `draft-api.ts`/`address-api.ts` have no dedicated test files
  either).
- No live runtime proof — see `CUSTOMER-L5-08-runtime-evidence.md`.
- No test exercises genuine multi-candidate scoring/selection (would
  require a live backend with seeded competing tenants — see
  runtime-evidence.md's "What Would Close the Environment Gap").
- No true multi-customer isolation test against a real backend (only the
  backend's own source-verified ownership check is covered, matching every
  previous sprint's identical constraint).
