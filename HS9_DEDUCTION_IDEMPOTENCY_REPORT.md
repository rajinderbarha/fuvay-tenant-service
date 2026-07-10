# HS9 — Deduction Idempotency Report

## Result: cannot deduct twice for the same job

Two independent guards (see `HS9_USAGE_CREDIT_LEDGER_REPORT.md` for
full detail):
1. The job-status machine itself — `completed` is a terminal status
   (`JOB_TRANSITIONS["completed"] = set()`), and `COMPLETABLE_JOB_STATUSES`
   does not include `completed`, so `/complete` can never be called
   successfully twice on the same job — live-verified: a real retry
   attempt returned `422 JOB_NOT_COMPLETABLE`.
2. Even if some future code path called `deduct_for_completed_job()`
   directly (bypassing the job-status guard), it independently checks
   for an existing `job_id` + `completed_job_deduction` ledger row and
   returns it rather than deducting again — backed by a real database
   unique index (`uq_ucl_job_event_once`), not just an application-level
   check.

## Verdict
Idempotency: **enforced at two independent layers, live-verified at
the job-status layer.**
