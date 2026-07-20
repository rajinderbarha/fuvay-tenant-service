# Coverage Verification Report

## Recount equality

`TestCanonicalCoverageRecount` (updated this slice) recounts the master CSV directly at test
time: `test_no_duplicate_rows` PASS, `test_no_false_positive_rows` PASS, `test_canonical_totals`
asserts `total == 210, protected == 169` PASS, `test_field_ops_subtotal` asserts
`len(fo) == 40, protected == 40` PASS.

## Runtime inventory agreement

Fresh `--module app.engines.field_ops.router` run: 28 total, 28 protected (11
`TENANT_MUTATION_PERMISSION_SCOPE_AWARE` + 3 `CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED` + 14
`STAFF_EXECUTION_ROLE_SCOPE_AWARE`) — matches the CSV row-by-row exactly.
`--verify-module` reports `unverified_count: 0`, exit code 0.

## One canonical figure

**169 protected of 210.** No second, divergent tally exists.
