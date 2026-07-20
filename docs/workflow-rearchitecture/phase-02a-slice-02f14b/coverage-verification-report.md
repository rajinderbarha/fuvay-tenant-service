# Coverage Verification Report

## Recount equality

`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount`
(updated this slice with the new canonical figures) recounts the CSV directly at test time:

- `test_no_duplicate_rows` — PASS.
- `test_no_false_positive_rows` — PASS.
- `test_canonical_totals` — asserts `total == 210`, `protected == 167`. PASS.
- `test_field_ops_subtotal` — asserts field_ops rows == 40, protected == 38. PASS.

## Runtime inventory agreement

A fresh run of `scripts/workflow_rearchitecture/inventory_mutation_routes.py --module
app.engines.field_ops.router` (post-fix) reports: 28 total, 11 `TENANT_MUTATION_PERMISSION_SCOPE_AWARE`
+ 12 `STAFF_EXECUTION_ROLE_SCOPE_AWARE` + 3 `CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED` = 26 protected,
2 `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` (`add_note`/`add_media`) — matching the CSV row-by-row
exactly for this module.

## One canonical figure

167 protected of 210. No second, divergent tally exists.
