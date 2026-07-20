# Coverage Verification Report

## Recount equality

`TestCanonicalCoverageRecount` (updated this slice) recounts the CSV directly at test time:
`test_no_duplicate_rows` PASS, `test_no_false_positive_rows` PASS, `test_canonical_totals`
asserts `total == 221, protected == 174` PASS, `test_field_ops_subtotal` asserts field_ops
`== 40/40` PASS (unaffected — booking rows are tracked separately from field_ops rows).

## Runtime inventory agreement

Fresh `--module app.engines.booking.router` run: 11 total, 5 protected (4
`TENANT_MUTATION_PERMISSION_SCOPE_AWARE` + 1 `PLATFORM_ADMIN_ONLY`), 6 unprotected/out-of-scope —
matches the CSV row-by-row exactly.

`--verify-module app.engines.booking.router` reports `unverified_count: 6` (the 6 explicitly
out-of-scope routes), exit code 1 — this is EXPECTED and consistent with this slice's honest,
partial-closure scope (the tool's exit code reflects unclassified-as-protected routes, not
unclassified-in-documentation routes; all 6 are fully classified in
`booking-mutation-route-inventory.csv`).

`--verify-module app.engines.field_ops.router` and `--verify-module
app.engines.field_ops.staff_router` both continue to report `unverified_count: 0`, exit 0 —
unaffected by this slice.

## One canonical figure for the full tenant-mutation surface

**174 protected of 221.** No second, divergent tally exists.
