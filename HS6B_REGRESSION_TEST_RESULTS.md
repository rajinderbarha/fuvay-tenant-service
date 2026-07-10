# HS6B — Regression Test Results (updated, second pass)

## New test file (second pass)
`tests/test_hs6b_matching_alignment_completion.py` — 13 tests covering
reason-code return type, reuse (not reimplementation) of
`get_tenant_home_services_matching_inputs`, break/holiday/booking-window
codes present in the gate, `excluded_providers` surfaced end-to-end
(engine → router → frontend type → UI), canonical source labels present
in both router and UI, forbidden-label scan. **13/13 passing.**

## First-pass test file (unchanged this pass)
`tests/test_provider_first_matching_and_price_choice.py` —
`REQUIRED_ELIGIBILITY_CHECKS` updated to the canonical model;
`test_eligibility_gate_no_longer_uses_parallel_readiness_tables`
regression guard. **19/19 passing.**

## Externally-modified files — 3 tests updated to match new reality
`TenantLayout.tsx`'s "Availability" nav label and route were externally
renamed to "Business Hours" / `/tenant/setup/availability` (not this
sprint's change). Per established session convention, updated the
affected assertions rather than reverting the external edit:
- `tests/test_hs5_service_areas_availability.py::test_setup_menu_has_service_areas_and_availability`
- `tests/test_hs5_service_areas_availability.py::test_availability_page_renders_weekly_schedule`
  (page source path updated to the new canonical file)
- `tests/test_tenant_menu_cleanup.py::test_availability_in_nav`

`python -m pytest tests/test_hs5_service_areas_availability.py tests/test_tenant_menu_cleanup.py -q`
→ **43 passed.**

## Full broader regression sweep (final, post all fixes)
```
pytest tests/ -k "home_service_booking or matching or bargain or provider_first or auto_price or bookab or availability or service_area or hs6b" -q
```
**380 passed, 0 failed.**

## TypeScript
0 errors in `frontend/super-admin` (diagnostics page + `api.ts` changes
confirmed clean when made; the only additional edits since were `.py`
test files, which don't affect TS).

## Live verification
See `HS6B_HTTP_E2E_LIVE_VERIFICATION_REPORT.md` — direct real-database
function verification of all alignment fixes across both passes,
including the second pass's break/holiday/booking-window scenarios, in
both include and exclude directions.

## Verdict
All tests passing, 0 regressions across the full sweep. Real dev-data
state (`tenants.status`) correctly restored after every live
verification session.
