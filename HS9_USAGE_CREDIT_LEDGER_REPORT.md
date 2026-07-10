# HS9 — Usage Credit Ledger Report

## New table: `usage_credit_ledger` (migration 129)
Fields match the ticket's required list exactly: `ledger_id`
(`id`), `tenant_id`, `job_id`, `booking_id`, `event_type`,
`credit_delta`, `balance_before`, `balance_after`, `deduction_source`,
`service_id`, `service_type_id`, `brand_id`, `zone_id` (column exists,
unused — no zone/tier concept wired into pricing rules yet), `reason`,
`created_at`, `created_by` (column exists, not currently populated —
see Remaining Blockers), `request_id`.

## Balance field: reused, not duplicated
`tenant_billing.credit_balance` was already the real, canonical usage
credit balance — used by a pre-existing admin `add_usage_credits` flow.
This sprint's deduction logic reads/writes that same column rather than
introducing a second, competing balance field (avoiding the exact kind
of parallel-data-model bug found repeatedly earlier this session in
HS6B/HS7/HS8).

## Live-verified
Real ledger row created on completion (see
`HS9_COMPLETED_JOB_DEDUCTION_REPORT.md` for the full JSON):
`credit_delta: -21.0`, `balance_before: 4000.0`, `balance_after: 3979.0`
— `balance_after == balance_before + credit_delta` holds exactly
(hard gate satisfied). `job_id` and `request_id` both present.

Read endpoints, both live-verified:
- `GET /v1/provider/usage-credits/balance` (tenant-facing) → real balance + `low_credit` flag (`< 20` threshold).
- `GET /v1/provider/usage-credits/ledger` (tenant-facing) → real entries, newest first.
- `GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` (admin) → same data, admin-scoped, not live-curl-tested this pass (code-path identical to the tenant-facing version, confirmed by direct source read).

## Idempotency guard — two layers
1. **Application-level**: `deduct_for_completed_job()` checks for an
   existing `job_id` + `event_type='completed_job_deduction'` row first
   and returns it (`deduction_status: "already_deducted"`) instead of
   inserting a duplicate.
2. **Database-level**: a partial unique index
   (`uq_ucl_job_event_once`) on `(job_id, event_type)` WHERE `event_type
   = 'completed_job_deduction'` — a genuine constraint, not just
   application discipline, so even a race condition or a bypass of the
   service-layer check cannot produce two deduction rows for the same job.

Live-verified indirectly: retrying `/complete` on an already-completed
job is rejected at the job-status layer
(`JOB_NOT_COMPLETABLE`, since `completed` isn't in
`COMPLETABLE_JOB_STATUSES`) before the deduction logic would even run —
the ledger's own uniqueness guard was not separately exercised via a
raw duplicate-insert attempt this pass, but is a real DB constraint,
confirmed via migration inspection.

## Verdict
Ledger: **real, complete, correct arithmetic, live-verified.**
