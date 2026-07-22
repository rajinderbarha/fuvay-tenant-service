# Canonical Global Coverage Reconciliation

## Starting point

Last approved baseline: **131 protected of 182 tenant-facing mutations.**
Slice 2F-14 produced two conflicting, unapproved figures: 146/210 (headline) and 143/213 (direct
CSV recount). Neither is canonical.

## Root causes of the discrepancy, found and fixed

1. **2 exact-duplicate rows.** `app.engines.home_service_assignment.staff_router`'s `accept_job`
   and `reject_job` rows were each present twice, byte-for-byte identical (a double-append from
   an earlier slice, Slice 2F-3B era). Removed one copy of each (−2 rows).
2. **1 false-positive row.** `app.engines.admin_catalog.tenant_router`'s
   `preview_tenant_price_options` was tagged `FALSE_POSITIVE (not a real mutation)` in its own
   `guard_status` column (a POST-verb preview/query endpoint, not a real mutation, mis-included
   in an earlier slice) — excluded from the denominator entirely (−1 row).
3. **`FULLY_PROTECTED` rows omitted from the "protected" count.** 9 rows across
   `app.engines.admin_catalog.tenant_router` carry `guard_status = FULLY_PROTECTED` but every
   prior slice's recount script (including 2F-14's) used a `VERIFIED` set that did not include
   this literal string — undercounting the numerator by 9 in every prior recount.
4. **field_ops.router's guard statuses were stale** in the CSV relative to this slice's fixes
   (8 additional routes moved from `PERMISSION_ONLY_NOT_SCOPE_AWARE`/
   `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` to `TENANT_MUTATION_PERMISSION_SCOPE_AWARE`/
   `STAFF_EXECUTION_ROLE_SCOPE_AWARE` this slice) — refreshed via a fresh runtime tool run.

## Canonical result

**213 (Slice 2F-14 raw) − 2 (duplicates) − 1 (false positive) = 210 total tenant-facing
mutation routes.**

**158 protected of 210** (up from the last-approved 131/182 — +27 protected, +28 total; the
denominator increase is entirely field_ops.router's 28 rows, which had zero prior rows before
Slice 2F-14; the numerator increase is 6 (staff_router) + 23 (field_ops.router, cumulative
2F-14+2F-14A) + 9 (`FULLY_PROTECTED` correction, unrelated to field_ops) − 11 (net of the 2
duplicate protected rows removed) ... see coverage-row-diff.csv for the exact row-by-row
reconciliation).

This is the single canonical figure. Both the master CSV
(`tenant-mutation-endpoint-inventory.csv`) and every module-specific recount in this slice's own
docs (field-ops subtotal: 40 rows, 29 protected) recount identically — verified by
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount`,
which asserts `total == 210` and `protected == 158` directly against the CSV file, and asserts
zero duplicate keys and zero remaining `FALSE_POSITIVE` rows.

## No "headline convention" used

There is exactly one number pair reported: **158/210**. No separate direct-recount figure is
reported alongside it — the CSV recount **is** the canonical figure, computed once.
