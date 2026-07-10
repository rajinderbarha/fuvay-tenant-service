# HS9 — Job Completion Report

## Result: reuses HS8B's certified single validated completion action

HS9 does not introduce a new completion endpoint — `POST
/v1/staff/service-jobs/{job_id}/complete` (built and live-verified in
HS8B) already enforces everything the ticket's "Job Completion Flow"
section requires: work summary required, collected amount required and
≥0, payment mode locked to `customer_pays_provider_directly`, job must
be in a completable status, unresolved parts requests block completion.

## Bug found and fixed this pass
`JS_SERVICE_STARTED` was in `COMPLETABLE_JOB_STATUSES` (HS8B) but its
entry in `JOB_TRANSITIONS` did not allow a transition to `"completed"`
— live-verified: completing a job still in `service_started` (not yet
marked `work_done`) failed with a raw
`EXECUTION_INVALID_STATUS_TRANSITION` 422, contradicting HS8B's own
stated completable-status set. Fixed by adding `"completed"` to
`JOB_TRANSITIONS[JS_SERVICE_STARTED]`.

## New this pass: Completed Job Deduction wired into completion
`complete_job()` now calls `deduct_for_completed_job()`
(`app/engines/execution/usage_credit_deduction.py`) immediately after
setting the job to `completed`, atomically in the same transaction — a
job can never be marked completed without a deduction attempt being
made and recorded (see `HS9_COMPLETED_JOB_DEDUCTION_REPORT.md` and
`HS9_USAGE_CREDIT_LEDGER_REPORT.md`).

## Live-verified
Real booking → job → full technician lifecycle → completion, for a
freshly created HS7 booking this pass (`JOB-20260709-000003`), completed
from `service_started` (not `work_done`) — confirms the bug-fix above
and the ticket's own "customer pays provider directly" flow end-to-end.

## Verdict
Job completion: **works, validated, live-verified.** Not
`NOT_READY_HS9_JOB_COMPLETION_FAILED`.
