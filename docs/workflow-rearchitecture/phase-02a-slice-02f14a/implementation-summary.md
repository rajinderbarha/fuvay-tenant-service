# Slice 2F-14A Implementation Summary

## Purpose

A focused continuation of Slice 2F-14, closing the specific gaps the approving reviewer flagged
as not yet approved: unresolved alternate-route classification, unfixed JobNote/JobMedia access
control, and two mutually-conflicting global coverage figures.

## Route-count reconciliation

`field_ops.staff_router`: 6/6 mounted mutations, unchanged. `field_ops.router`: 28 mounted
mutations, unchanged count; the "7 vs 9" discrepancy in 2F-14's own docs is resolved as two
correct descriptions of different, previously-unexplained subsets (see
staff-alternate-route-count-resolution.md) — not a counting error.

## Defects found and fixed this slice

1. **`void_job` — genuine cross-tenant IDOR.** Loaded the job with zero tenant-ownership check;
   any actor with the platform-wide `TENANT_UPDATE` permission could void a job belonging to a
   different tenant. Fixed by reusing the existing `_get_job_for_assignment` helper.
2. **`JobNote`/`JobMedia` — genuine, live access-control and privacy gap.** `add_note`/
   `list_notes`/`add_media`/`list_media` accepted a client-supplied `tenant_id` and performed no
   job-ownership check at all; `list_notes` leaked `is_internal=True` notes to customers. Fixed:
   `tenant_id` now server-derived from the job; `_assert_can_access_job` enforced; customers
   denied write access to both; is_internal notes filtered from customer reads.
3. **`start_assessment`/`complete_assessment` — missing named role dependency**, same class as
   `accept_job` (fixed in 2F-14). `_get_job_for_staff_action` already made this safe via
   ID-equality; added `require_staff_or_technician_only` for consistency and tool-visibility.
4. **`close_job`/`generate_invoice`/`record_payment`/`deduct_commission`/`financial_close` —
   permission-only, not access-scope-aware**, the same defect class already fixed for
   `assign_job`/`update_status`. Upgraded to `require_tenant_mutation_permission`.

## Not fixed (classified, distinct capability, no proven bypass)

`create_job`, `convert_to_repair`, `spawn_repair` (creation/spawn, not same-record mutation);
`create_quote`, `create_job_quote`, `approve_job_quote`, `reject_job_quote`, `send_job_quote`,
`respond_to_quote` (quotes — existing service-level ownership already adequate on inspection).

## Coverage reconciliation

Root cause of the prior slice's 2 conflicting figures fully diagnosed: 2 exact-duplicate rows +
1 false-positive row in the master CSV, plus `FULLY_PROTECTED` rows omitted from every prior
slice's "protected" count. Canonical result: **158 protected of 210 tenant-facing mutation
routes** — a single number, recounted identically from the CSV by an automated test
(`TestCanonicalCoverageRecount`).

## Testing

30 new tests (`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`), all
deterministic (mocked job/db objects, not source-string-only). Full slice suite: 192/192 passing.
Broad regression sweep: 1226 passed, 11 pre-existing live-environment exclusions honestly
disclosed and not counted as passing.

## Source-scope

The stray `service.py.tmp.3332.f9e469299afb` file (pre-existing, tracked since the original
baseline commit, unrelated to any slice's work) was restored after Slice 2F-14 had bundled its
deletion into an unrelated implementation diff.

## Final status

See approval-gate.md.
