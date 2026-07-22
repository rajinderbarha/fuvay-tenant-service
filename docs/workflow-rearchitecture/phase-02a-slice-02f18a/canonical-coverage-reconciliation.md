# Canonical Coverage Reconciliation

## Starting approved baseline
190/226 (pre-2F-18) → 200/226 (2F-18's router-level guard fix, provisional
pending this slice's object-level closure per the 2F-18 approval gate's own
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` status).

## Row-level reconciliation of the same 10 routes
The canonical CSV's convention (established since Slice 2F-15C, "Design A")
counts a row as protected based on its ROUTER-LEVEL dependency
(`guard_status` — e.g. `TENANT_MUTATION_ROLE_SCOPE_AWARE`,
`STAFF_EXECUTION_ROLE_SCOPE_AWARE`), not on the depth of downstream
object-level policy. This slice did NOT change any router's dependency
(`require_owner_or_office_staff_mutation`/`require_staff_or_technician_only`
remain exactly as 2F-18 left them) — it changed what happens INSIDE the
service layer once a request already passed the router gate.

Confirmed via direct runtime introspection (re-run this slice, identical
output to 2F-18's `runtime-verification-report.md`):
```
POST /v1/provider/notifications/{notification_id}/read  -> TENANT_MUTATION_ROLE_SCOPE_AWARE
... (all 10 routes, unchanged guard_status)
```

**Therefore the row-level guard_status classification, and hence the
numerator/denominator arithmetic, is UNCHANGED by this slice: still
200/226.** This slice does not "force" 200/226 — it INDEPENDENTLY confirms
it was already earned at the router-classification level in 2F-18, and now
additionally closes the deeper object-policy gaps that made 2F-18 unwilling
to claim full closure (`DOMAIN_INTEGRITY_BLOCKED`).

## What actually changed as a RESULT of this slice
Not the coverage arithmetic — the JUSTIFICATION for the final status label.
2F-18 could only claim `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` because
technician tenant-wide access and unvalidated attachments were open. Both
are substantially closed now (see `implementation-summary.md`), which is
why this slice's final status advances to
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` (see
`approval-gate.md`) rather than changing the coverage fraction.

## Both canonical CSVs recount identically
No row was added, removed, or reclassified this slice —
`tenant-mutation-endpoint-inventory.csv` (226 rows, 200 protected) and
`mutation-enforcement-matrix.csv` (unchanged from 2F-18's update) both
remain exactly as 2F-18 left them. `test_canonical_totals` and
`test_global_numerator_denominator_match_2f17_baseline` (both asserting
`total==226, protected==200`) pass unchanged, re-confirmed by this slice's
regression run.

## Remaining module count
Unchanged: 26 unprotected tenant/provider mutation routes across the 10
non-selected modules in `remaining-module-queue-update.csv` (copied
verbatim from 2F-18, not re-modified this slice — this slice touched only
`platform_notifications`).
