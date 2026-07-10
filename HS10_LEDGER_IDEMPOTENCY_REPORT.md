# HS10 — Ledger Idempotency Report

## Two independent guards (built HS9, re-confirmed this session)
1. **Job-status terminality** — `completed` has no further allowed
   transitions; `COMPLETABLE_JOB_STATUSES` doesn't include `completed`
   itself, so `/complete` can never succeed twice on the same job.
2. **Database unique index** — `uq_ucl_job_event_once` on
   `(job_id, event_type)` WHERE `event_type = 'completed_job_deduction'`
   — a real Postgres constraint, not just application discipline.

## Live-verified this session
Final ledger check across the whole session's activity: **exactly 2
entries**, one per each of the 2 jobs completed this session
(`6628eb52...` from HS9, `34fc415e...` from HS10's own chain), each
`-21.0`, with `balance_before`/`balance_after` chaining correctly
(`4000 → 3979 → 3958`) — no duplicate, no missing, no misordered entry.

## Verdict
Ledger idempotency: **real, live-verified, two independent enforcement
layers.**
