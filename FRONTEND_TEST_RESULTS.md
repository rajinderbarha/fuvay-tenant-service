# Cross-App Frontend Runtime Verification Sprint — Test Results

## New tests

`tests/test_p0_cross_app_frontend_runtime.py` — 18 tests, all passing. Static-inspection style (established
convention), covering: backend `_booking_dict`/admin_router field exposure, the `converted_job_id` JOIN fallback,
`_job_dict` payment_recorded/amount_collected derivation, tenant/admin/staff/customer page content (payment
breakdown cards, Completed Job Deduction labeling, no-payout-language), API client type/method presence, and an
automated forbidden-term scan across all 6 job-completion-facing pages.

## Updated tests

- `tests/test_p0_admin_bookings.py::test_admin_router_service_name_from_join` — previously asserted the literal
  string `"ms.name"`, which was itself the bug (master_services has no `name` column). Updated to assert
  `"ms.service_name"` with a comment explaining the live 500 this caused and how it was found.

## Full backend suite

```
pytest tests/ -q
7531 passed, 36 failed, 99 warnings in ~336s
```

The 36 failures are the same pre-existing, unrelated failures present in every prior sprint's baseline this session
(concurrent in-progress catalog-UI-nav work by another process). Zero new regressions. One test
(`test_p0_navigation_operation_visibility.py::test_disabling_real_estate_hides_site_visits_only`) showed up as
failed in one full-suite run and passed cleanly in isolation — pre-existing test-order flakiness, unrelated to this
sprint's changes, not counted as a regression.

## Frontend type-check

```
npx tsc --noEmit   (frontend/tenant-portal)    → 0 errors
npx tsc --noEmit   (frontend/super-admin)      → 0 errors
```

## Mobile apps (React Native)

`mobile/staff-app` and `mobile/customer-app` do not have a `tsc`/build step wired into this repo's test suite
(confirmed via audit — no `tsconfig.json`-driven CI check exists for either). Changes to
`JobDetailScreen.tsx`/`BookingDetailScreen.tsx` and their `lib/api.ts` files were verified by static-inspection
tests (`test_p0_cross_app_frontend_runtime.py`) and by reading the compiled JSON responses they consume during the
live smoke test, but not by an actual on-device/simulator render — flagged in `REMAINING_BLOCKERS.md`.
