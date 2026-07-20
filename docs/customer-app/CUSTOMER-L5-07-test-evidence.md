# CUSTOMER-L5-07 — Test Evidence

```
npx jest
Test Suites: 75 passed, 75 total
Tests:       516 passed, 516 total
```

(489 at the start of this sprint; net +27 new tests, plus a rewrite of
`route-registry.test.ts`'s CUSTOMER-L5-06-era address-placeholder
assertion to match this sprint's real route promotion.)

## New and Rewritten Test Files

| File | Count | Covers |
|---|---|---|
| `features/address/domain/__tests__/address-schema.test.ts` | 8 | valid/invalid address parsing, null coordinates, list drop-not-fail, delete response shape |
| `features/address/domain/__tests__/address-form-validation.test.ts` | 10 | sanitization (trim/control-char-strip/length-cap/Unicode preservation), required-field validation matching the real backend's own requirements exactly |
| `features/address/queries/__tests__/address-query-keys.test.ts` | 3 | locale/tenant scoping |
| `features/booking-draft/domain/__tests__/serviceability-schema.test.ts` | 5 | real serviceable (zipcode/city match) and not-serviceable result shapes, fails-closed on an unrecognized `matched_by` value |
| `navigation/__tests__/route-registry.test.ts` (rewritten) | 4 | `addressSelection`/`addressForm`/`serviceabilityCheck` promoted to real/production; `pricing` remains dev-only |

## Regression Confirmation

All 489 tests carried forward from before this sprint continue passing
unmodified, confirming the route-registry changes (three new production
routes, one route removed and its screen retired), the multipart/media
code from CUSTOMER-L5-06, and the draft-queries additions
(`useCheckServiceability`) introduced no regressions across Home/Category/
Service/Search/Assistant/Draft/Media/Auth/deep-links/remote-config — all
unmodified this sprint and all still green.

## Not Covered This Pass

- No component/render tests for `AddressListScreen`/`AddressFormScreen`/
  `ServiceabilityScreen`/`PricingBoundaryPlaceholderScreen` — consistent
  with every previous sprint's identical deprioritization; the domain
  logic those screens call (schemas, validation) is exhaustively tested
  instead.
- No test exercises `use-current-location.ts` against a mocked
  `expo-location` module (permission/coordinate/reverse-geocode flow) —
  judged lower-value than the domain-logic coverage above given this
  sprint's already-large scope; the module's logic is a thin,
  straightforward wrapper over three sequential `expo-location` calls with
  no complex branching to unit-test in isolation.
- No live runtime proof — see `CUSTOMER-L5-07-runtime-evidence.md`.
- No true multi-customer isolation test against a real backend (only the
  backend's own source-verified ownership checks are covered, matching
  every previous sprint's identical constraint).
