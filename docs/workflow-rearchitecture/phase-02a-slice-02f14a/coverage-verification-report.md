# Coverage Verification Report

## Recount equality

`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount`
recounts `tenant-mutation-endpoint-inventory.csv` directly at test time (not a cached figure):

- `test_no_duplicate_rows` — asserts zero `(method, path, module)` duplicate keys. PASS.
- `test_no_false_positive_rows` — asserts no row's `guard_status` contains `FALSE_POSITIVE`.
  PASS.
- `test_canonical_totals` — asserts `total == 210` and `protected == 158`. PASS.
- `test_field_ops_subtotal` — asserts field_ops-related rows == 40, protected == 29. PASS.

## Runtime inventory agreement

Fresh runs of `scripts/workflow_rearchitecture/inventory_mutation_routes.py` against
`app.engines.field_ops.staff_router` (6 total, 6 protected) and `app.engines.field_ops.router`
(28 total, 17 protected) match exactly what is recorded in the CSV for those 34 rows (plus
`checklist_router`'s pre-existing 6, all field_ops-related total = 40, protected = 29 —
consistent with the field_ops subtotal test above).

## Both CSVs recount identically

There is one master CSV (`tenant-mutation-endpoint-inventory.csv`); this slice's own
`exact-runtime-route-reconciliation.csv` (field_ops-only, 34 rows) and
`deferred-field-ops-route-classification.csv` (19 rows) are derived views of the same underlying
runtime data, not independently maintained counts — no second, divergent tally exists.

## Discrepancy resolution confirmed

The exact 3-row gap between 2F-14's 213-row raw count and its own 210-row headline expectation is
fully explained and eliminated: 2 exact-duplicate rows + 1 false-positive row = 3.
