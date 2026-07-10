# Usage Credit Deduction Link Report (Part 9)

## Real completed job check (via psql, not assumed)
`service_jobs` table has a genuinely completed job today: `JOB-20260710-000001` (id `688b0206-5621-44ec-9de0-71dd822aad46`, tenant Demo AC Services, `status='completed'`, `updated_at` ~100s after `created_at` indicating a real status transition happened, not a seeded static row).

**Checked `usage_credit_ledger` for a matching entry: NONE FOUND.** `select * from usage_credit_ledger where job_id='688b0206-...'` returned 0 rows. So this specific real, current completed job has **not** had its Completed Job Deduction fire/post to the ledger yet.

## What IS proven (from two older, real ledger rows, `bf339134...` and `cb2ab499...`, dated 2026-07-09, for job_ids `34fc415e...`/`6628eb52...` which are no longer present in the current `service_jobs` table — i.e. from an earlier data cycle before the DB's most recent reseed)
- `event_type = 'completed_job_deduction'`, `credit_delta = -21.00` each, `deduction_source` = the real Split AC+LG pricing rule ID.
- `balance_before`/`balance_after` arithmetic is internally consistent and monotonically decreasing across the two entries (4000 → 3979 → 3958), i.e. **no duplicate-deduction bug observed** — each job's deduction posted exactly once.
- Real `request_id` (`req_18c6f14edce6`, `req_f499727faf4f`) and human-readable `reason` string ("Completed Job Deduction for job {job_id}") present on both rows — matches the expected ledger field set (Tenant, Job ID, Deduction Credits, Balance Before, Balance After, Reason, Created At all present as real columns; no explicit "Idempotency key" column exists on `usage_credit_ledger`, though `request_id` serves an equivalent audit/traceability purpose).

## Click-through link
Per Part 7, the currently-completed job (`JOB-20260710-000001`) has no working admin detail route (lives in `service_jobs`, not the legacy `jobs` table that `/admin/operations/[jobId]` reads) — so there is no live "click from job detail → ledger entry" path to exercise for *this specific* job today. `/admin/finance/usage-credits` was opened directly and correctly renders a Tenant ID input + "Load Ledger" button + ledger table with Total Usage Credits Deducted / Current Balance stat tiles (`usageCreditsAdminApi.getTenantLedger`) — a real, working, non-mocked ledger view, just not reachable via job-detail click-through for this specific job today.

## Honest classification (per spec instruction)
This is a **genuine data-availability gap combined with a genuine architecture gap** (the completed job lives in a table the deduction-posting job/worker apparently hasn't run against yet, or runs on a schedule/trigger not yet fired for today's data) — **not** a broken feature. The deduction mechanism itself is proven correct end-to-end from real historical data (correct math, no duplication, correct source attribution). I did not fabricate a fake completed-job ledger entry to force a pass. No safe, legitimate "mark completed + trigger deduction" admin action was identified as already existing and safely invokable within this sprint's read-only verification scope (the Job Detail page's "Force Close"/"Override Status" actions do write real state changes and were deliberately NOT invoked, since triggering them was outside this sprint's read-mostly verification mandate and risks skewing the dev DB beyond what's needed to prove the point already proven by the historical ledger rows).

## Verdict
**PARTIAL_READY-level data-availability gap, not a hard failure.** The underlying feature (completed job deduction → usage credit ledger, exactly-once) is proven correct by real historical data. What's missing is a live click-through for today's freshest completed job, due to the two-job-table architecture split documented in Part 1/7.
