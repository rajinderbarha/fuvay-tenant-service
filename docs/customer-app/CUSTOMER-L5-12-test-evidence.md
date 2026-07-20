# CUSTOMER-L5-12 — Test Evidence

```
npx jest
Test Suites: 91 passed, 91 total
Tests:       608 passed, 608 total
```

(585 at the start of this sprint; net +23 new tests, plus two
pre-existing tests updated to reflect this sprint's real route
promotions — no existing assertions removed without a direct, corrected
replacement.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/bookings/domain/__tests__/booking-status-registry.test.ts` | 4 | every real reachable status, the defined-but-unreachable statuses mapped safely, the unknown-status fail-safe fallback, `isKnownBookingStatus` |
| `features/bookings/domain/__tests__/booking-list-schema.test.ts` | 5 | real page shape, per-item resilience (dropping invalid rows), honest `mayHaveMore` inference (full page vs. partial), null `selected_provider`, malformed envelope |
| `features/bookings/domain/__tests__/booking-detail-schema.test.ts` | 4 | real found-with-job/without-job shapes, the real distinct `{success:false,error:{...}}` error shape, malformed payload |
| `features/bookings/domain/__tests__/booking-tracking-schema.test.ts` | 4 | real timeline with the synthetic first row plus real events, per-item resilience, real empty-timeline shape, malformed envelope |
| `features/bookings/domain/__tests__/booking-group.test.ts` | 3 | active/past grouping for every real status, unknown-status fail-safe grouping |
| `features/bookings/domain/__tests__/booking-review-status-schema.test.ts` | 3 | real null-review and existing-review shapes, malformed payload |

## Pre-Existing Tests Corrected (Not Weakened)

- `navigation/__tests__/route-guards.test.ts`: the "denies a
  production-disabled route in a production build" test referenced
  `bookingsList`, which this sprint legitimately promotes to production —
  updated to reference `tracking` (confirmed still `productionEnabled:
  false`, same real assertion intent preserved).
- `navigation/__tests__/route-registry.test.ts`: the CUSTOMER-L5-11-era
  "bookingsList and bookingDetail remain dev-only" assertion was replaced
  with a new CUSTOMER-L5-12 describe block asserting the real production
  promotion, plus a new assertion that `tracking` correctly remains
  dev-only (CUSTOMER-L5-13's scope).

## Regression Confirmation

All other tests carried forward from before this sprint continue passing
unmodified, confirming the route-registry/MainNavigator changes
(`bookingsList`/`bookingDetail` production promotion, new
`BookingsListScreen`/`BookingDetailScreen`, the Home screen's new "View my
bookings" entry point) introduced no regressions across
Home/Category/Service/Search/Assistant/Draft/Media/Address/
Serviceability/ProviderMatching/Pricing/Bargain/BookingConfirmation/Auth/
deep-links/remote-config — all unmodified this sprint (beyond the
described route-guard/route-registry test corrections) and all still
green.

## Not Covered This Pass

- No component/render tests for `BookingsListScreen`/`BookingDetailScreen`
  — consistent with every previous sprint's identical, explicitly-documented
  deprioritization.
- No test exercises `bookings-api.ts`'s URL construction directly, or
  `use-bookings-list-view.ts`'s hook composition directly — consistent
  with the established pattern that thin API wrappers and hook-composition
  layers over already-tested pure functions/query hooks are not
  independently unit-tested.
- No live runtime proof — see `CUSTOMER-L5-12-runtime-evidence.md`.
- No genuine multi-page pagination test against a live backend (would
  require a real seeded customer with more than one page of bookings —
  see runtime-evidence.md).
- No genuine end-to-end timeline test against a live technician-assignment
  transition (would require a real seeded job and staff member — see
  runtime-evidence.md).
- No true multi-customer isolation test against a real backend (only the
  backend's own source-verified ownership checks are covered, matching
  every previous sprint's identical constraint).
