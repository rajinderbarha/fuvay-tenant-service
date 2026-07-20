# Deterministic Test Report

## New this slice
`tests/test_phase2f19_remaining_queue_reconciliation.py` — 13 tests, all
passing:
- `TestCanonicalBaseline` (1): confirms 226/200/26 baseline.
- `TestRemainingRowCompleteness` (3): 26-row completeness, no duplicate
  route keys, runtime-mount confirmation for all 26.
- `TestModuleGrouping` (2): 26-route sum across modules, exactly 10
  modules.
- `TestRiskScoring` (2): every module scored, compliance is the sole
  CRITICAL module.
- `TestNonSelectedQueue` (2): queue accounts for all 26 routes exactly
  once, selected module identified correctly.
- `TestSelectedModuleRuntimeExistence` (2): selected routes exist in the
  canonical CSV AND are independently confirmed mounted at runtime (a
  live, in-process re-walk of the mounted app, not a cached assumption).
- `TestCoverageUnchanged` (1): coverage-row-diff shows zero corrections.

## Runtime inventory tests
Re-ran `test_selected_routes_are_mounted_at_runtime` — a genuine live
re-walk of the mounted FastAPI application (not reading from a CSV) — to
independently corroborate the 6 selected routes' existence, matching the
methodology established in every prior slice of this initiative.

## Canonical recount tests
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` and
`tests/test_phase2f17a_global_mutation_inventory.py` both re-run this
slice — both continue to assert `total==226, protected==200`, unchanged,
passing.

## Remaining-row completeness / module-grouping / risk-ranking / selection-consistency tests
All covered by the new suite above — 13/13 passing.

## Existing Slice 2F-17A / 2F-18 through 2F-18E tests
All re-run this slice as part of the combined regression (see
`regression-report.md`) — 175 tests combined, 0 failures.

## Previously closed module verifiers
`field_ops.router`, `field_ops.staff_router`, Booking, quote_checklist,
invoice-lineage, and the full platform_notifications six-slice series'
own verifier suites all re-run and pass unchanged this slice (part of the
same combined regression).
