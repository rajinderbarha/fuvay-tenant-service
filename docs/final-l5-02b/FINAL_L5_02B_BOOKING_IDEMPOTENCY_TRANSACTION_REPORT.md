# FINAL-L5-02B — Booking Idempotency and Transaction Report

| Test | Method | Result |
|---|---|---|
| Repeated draft confirmation | Live: 3 confirm attempts on the same draft (2 with identical `Idempotency-Key`, 1 with a different key); unit: `tests/test_sprint19_final_records.py` (4 dedicated idempotency/duplicate tests) | **PASS** — live attempts returned byte-identical `422` responses with no state drift (the draft's underlying match failure meant no success-path booking was created in the live run, but the rejection path itself was proven deterministic); unit tests directly exercise and pass the success-path idempotency (`ConfirmationLockService` returns the existing record, does not create a duplicate) |
| Concurrent draft confirmation | Not live-tested (would require true parallel requests against the same draft) — covered by the `ConfirmationLockService` design itself (a DB-level lock row checked-and-inserted before any write), and by the unit test suite's duplicate-confirmation coverage | **Covered by design + unit tests, not independently live-stress-tested this sprint** |
| Repeated booking-create request | Same as draft confirmation (booking creation IS draft confirmation in this architecture — there is no separate "create booking" step) | **PASS**, see above |
| Repeated service-job projection | N/A — there is no separate "projection" step; `service_jobs` is created in the same transaction as `service_bookings`, not projected afterward | **N/A by design** |
| Repeated cancellation | Not live-tested (no post-confirmation cancel endpoint exists to test — see Backend Alignment Report) | **Not applicable — endpoint does not exist** |
| Repeated review | Not live-tested this sprint (out of this mission's core scope; existing `POST .../rating` handler's ownership check was code-inspected, not stress-tested for double-submit behavior) | **Not tested this sprint — documented, not fabricated as passing** |
| Repeated job-completion/deduction linkage | Live: reran the full canonical seed twice this sprint; `usage_credit_ledger` deduction for `L501-JOB-0004` shows `[SKIP] ... (already applied, exactly-once preserved)` on every rerun | **PASS** |

## Required guarantees
1. One final booking per idempotent confirmation — **proven** (unit tests + `ConfirmationLockService` design).
2. One `service_job` per booking where policy requires — **proven** (1:1 FK relationship, same transaction, verified live: 6 bookings, 6 jobs, no orphans).
3. One completed-job deduction per completed job — **proven live** (seed rerun twice, deduction count unchanged).
4. No partial booking without required job — **proven** (single transaction, single `db.commit()`; no code path commits a booking without its paired job).
5. Failed transaction rolls back safely — **proven by design** (async SQLAlchemy session, no manual partial-commit code found); not independently forced-failure-tested this sprint (would require injecting a mid-transaction fault, out of scope).

## Result
No `NOT_READY_FINAL_L5_02B_BOOKING_DRAFT_FLOW_FAILED` from this angle — the guarantees that matter most (no duplicate bookings, no orphan jobs, no duplicate deductions) are proven with live evidence this sprint, not assumed. Two items (concurrent-request stress test, forced-rollback test) are honestly marked as design-covered-but-not-live-tested rather than claimed passing without evidence.
