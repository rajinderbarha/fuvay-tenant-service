# Recount Test Report

## `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount`
Updated `test_canonical_totals` to assert the reconciled figures: `total == 226`, `protected == 190`. All other tests in this class (`test_no_duplicate_rows`, `test_no_false_positive_rows`, `test_field_ops_subtotal`) unchanged and re-verified passing — confirming:
- **Exact canonical numerator**: 190.
- **Exact canonical denominator**: 226.
- **No duplicate canonical route keys**: `test_no_duplicate_rows` passing.
- **No false positive in tenant denominator**: `test_no_false_positive_rows` passing (the one false positive found this slice, `preview_matching_inputs`, was physically removed, not merely relabeled — consistent with this test's invariant that no row's `guard_status` contains the literal string `FALSE_POSITIVE`).
- **`field_ops.router` subtotal unaffected**: `test_field_ops_subtotal` — 40/40, unchanged.

## Row-level completeness (proven via direct file inspection, documented in this slice's CSVs rather than a new pytest assertion, per the "Permitted changes" scope limiting new test additions to what's "directly required")
- **Every remaining row has a module**: `module-grouping-summary.csv` — 36 rows across 11 modules, sum verified to equal 36.
- **Every remaining row has a persona**: `persona-reclassification.csv` — all 11 modules classified `TENANT_PROVIDER_MUTATION` (the false positive is separately classified `FALSE_POSITIVE_NON_MUTATION` and excluded).
- **Every remaining row has a primary gap**: `remaining-gap-classification.csv` — all 41 original rows (36 remaining + 4 reclassified-protected + 1 false-positive) have an assigned primary gap.
- **Every remaining row has runtime status**: `runtime-route-reconciliation.csv` — all 13 modules (11 remaining-unprotected + 2 reclassified) show a runtime-confirmed status; no row is `UNKNOWN`.
- **Ranked module queue covers every remaining row exactly once**: `non-selected-module-queue.csv` (10 modules, 26 routes) + `selected-next-module.md` (1 module, 10 routes) = 11 modules, 36 routes — matches exactly, no overlap, no omission.
- **Selected next module routes all exist at runtime**: confirmed via `runtime-verification-report.md`'s live `--verify-module app.engines.platform_notifications.provider_router` output (`total_routes: 10`, matching `selected-next-module-route-list.csv` exactly).

## No `UNKNOWN` rows
Every one of the 41 originally-flagged rows was resolved to a definitive disposition (36 remain unprotected with an assigned module/persona/gap, 4 reclassified protected, 1 removed as false positive) — zero rows remain in an indeterminate state.
