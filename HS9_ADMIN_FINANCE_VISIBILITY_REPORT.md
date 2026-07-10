# HS9 — Admin Finance Visibility Report

## Backend: real, added this pass
`GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` — real endpoint,
super-admin-gated, returns the same ledger rows as the tenant-facing
version, scoped by `tenant_id` path parameter. Not live-curl-tested this
pass (identical code path to the tenant-facing version, which was
live-verified); confirmed correct via direct source read.

## Not implemented this pass
- No `GET /v1/admin/home-services/completed-job-deductions` (a
  cross-tenant list of all completed-job deductions) — only the
  per-tenant ledger endpoint exists.
- No `GET /v1/admin/home-services/jobs/{job_id}/audit` — the existing
  `GET /v1/admin/service-jobs/{job_id}/execution-timeline` (from HS8)
  covers job status audit; it does not include the deduction ledger
  entry inline.
- No admin "Retry deduction" / "Add usage credits" action wired to a
  failed-deduction state — deduction in this implementation cannot
  currently fail (it always succeeds, even into negative balance, per
  the ticket's own recommended policy — see Remaining Blockers), so
  there is no failure state to build a retry action against yet.
- No admin frontend page renders any of this.

## Verdict
Admin finance visibility: **partially implemented** — one real,
correct backend endpoint; the cross-tenant list, audit-ledger join, and
all UI are documented gaps, not claimed as done.
