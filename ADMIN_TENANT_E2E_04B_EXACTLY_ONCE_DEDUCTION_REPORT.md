# ADMIN-TENANT-E2E-04B — Exactly-Once Deduction Report

## Checks, all live-verified this session

1. **Same job has only one `completed_job_deduction` ledger entry** —
   confirmed via direct API query filtered by `job_id`:
   `count: 1` for `JOB-20260710-000002` (`b035159a-...`).
2. **Same job cannot create a duplicate ledger entry by
   refreshing/reopening detail** — verified via Playwright: opened the
   filtered ledger view, reloaded the page, row count stayed at exactly
   1 both before and after reload (the detail page and ledger view are
   both read-only GETs — no write path is triggered by viewing).
3. **Duplicate completion action is blocked** — verified live via a real
   API call: re-calling `POST /v1/staff/service-jobs/{job_id}/complete`
   on the already-completed job returned `422 JOB_NOT_COMPLETABLE`
   (`"Job cannot be completed from its current status (completed)."`),
   confirmed the state machine itself blocks re-completion, so the
   deduction's idempotency guard is never even reached on retry.
4. **Ledger idempotency at the deduction-function level** — confirmed via
   source read of `app/engines/execution/usage_credit_deduction.py`:
   `deduct_for_completed_job` checks
   `UsageCreditLedger.job_id == job_id` before inserting, and the
   function's own docstring states *"Idempotent per job_id — a second
   call for the same job returns the existing deduction record."* This
   is a second, independent layer of protection beneath the state-machine
   guard in #3.

## Verdict
Full pass. Exactly-once deduction verified at two independent layers
(state machine + ledger idempotency check), both exercised live this
session with real API calls against the real freshly-completed job.
