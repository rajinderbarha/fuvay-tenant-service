# CUSTOMER-L5-13 — Test Evidence

```
npx jest
Test Suites: 93 passed, 93 total
Tests:       617 passed, 617 total
```

(608 at the start of this sprint; net +9 new tests, plus two pre-existing
tests updated to reflect this sprint's real `tracking` route promotion —
no existing assertions removed without a direct, corrected replacement.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/service-tracking/domain/__tests__/execution-timeline-schema.test.ts` | 5 | real in-progress timeline shape, structural stripping of `notes`/`actor_role`/`id`/`job_id`, real empty-timeline shape, per-item resilience, malformed envelope |
| `features/service-tracking/domain/__tests__/execution-event-labels.test.ts` | 3 | every real, confirmed-emitted event type maps correctly; a real-but-unmapped event type (diagnosis/photo/note events) fails safe; a wholly unrecognized event type fails safe without throwing |
| `features/bookings/domain/__tests__/booking-status-registry.test.ts` (extended) | 2 new assertions | every real execution-engine status added this sprint; corrected framing of `completed`/`cancelled` as confirmed-reachable (not merely defined-but-dead) |

## Pre-Existing Tests Corrected (Not Weakened)

- `navigation/__tests__/route-guards.test.ts`: the "denies a
  production-disabled route in a production build" test referenced
  `tracking`, which this sprint legitimately promotes to production —
  updated to reference `notifications` (confirmed still
  `productionEnabled: false`, same real assertion intent preserved).
- `navigation/__tests__/route-registry.test.ts`: the CUSTOMER-L5-12-era
  "tracking remains a dev-only boundary" assertion was replaced with a
  new CUSTOMER-L5-13 describe block asserting the real production
  promotion.

## Regression Confirmation

All other tests carried forward from before this sprint continue passing
unmodified, confirming the route-registry/MainNavigator changes
(`tracking` production promotion, new `ServiceTrackingScreen`,
`BookingDetailScreen`'s "Track provider" button promotion) introduced no
regressions across Home/Category/Service/Search/Assistant/Draft/Media/
Address/Serviceability/ProviderMatching/Pricing/Bargain/BookingConfirmation/
Bookings/Auth/deep-links/remote-config — all unmodified this sprint
(beyond the described route-guard/route-registry test corrections and the
`BookingDetailScreen`/status-registry extensions) and all still green.

## Not Covered This Pass

- No component/render tests for `ServiceTrackingScreen` — consistent with
  every previous sprint's identical, explicitly-documented
  deprioritization.
- No test exercises `service-tracking-api.ts`'s URL construction directly,
  or `use-service-tracking.ts`'s hook composition directly — consistent
  with the established pattern that thin API wrappers and hook-composition
  layers over already-tested query hooks are not independently
  unit-tested.
- No live runtime proof — see `CUSTOMER-L5-13-runtime-evidence.md`.
- No genuine end-to-end execution-transition test against a live backend
  (would require a real seeded job, staff member, and sequential real
  staff-endpoint calls — see runtime-evidence.md).
- No true multi-customer isolation test against a real backend (only the
  backend's own source-verified ownership check is covered, matching
  every previous sprint's identical constraint).
- No tests for technician profile, live GPS, map, ETA, route, or
  masked-call — none of these have any real backend capability to test
  against (see the corresponding contract docs).
