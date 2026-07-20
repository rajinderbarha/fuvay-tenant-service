# Concurrent Claim Proof

## Live two-session integration test — NOT executed, honestly reported as an environment exclusion
This environment has no live Postgres instance available (confirmed
unavailable throughout every slice of this initiative, including this
one — re-verified this slice). Per the mission's own explicit fallback
instruction ("When live Postgres is unavailable... Report the live test
as an environment exclusion rather than claiming it executed"), no live
two-session concurrency test was written or run. This is a live-environment
exclusion, reported here explicitly, not a silent gap.

## Deterministic unit instrumentation of transaction boundaries and lock retention
What CAN be proven without a live database, and IS proven this slice:
1. **The query requests a row lock** — `test_asset_lookup_uses_select_for_update`
   (2F-18D, re-passing) compiles the constructed SQL and asserts `"FOR
   UPDATE"` appears in it.
2. **No intermediate commit releases the lock early** —
   `test_no_commit_before_claim_and_message_are_both_ready` (this slice)
   proves `db.commit()` is called ZERO times before every piece of state
   (claim, message, notifications) is fully prepared — since a Postgres
   `FOR UPDATE` lock is held until commit/rollback, and there is
   demonstrably no commit before that point, the lock necessarily spans
   the ENTIRE claim-and-message operation.
3. **A downstream failure is not swallowed** —
   `test_commit_failure_propagates_not_swallowed` (this slice) proves an
   exception at the commit step propagates out of `send_message`
   uncaught — the precondition for the framework's standard
   rollback-on-exception behavior (which is what would actually release
   the lock and undo the claim on failure) to ever run.

## What this DOES and does NOT prove
**Proven**: the CODE requests the correct locking primitive, holds it for
the correct scope (no premature release), and does not swallow failures
that should trigger rollback.

**NOT independently provable without a live database**: that Postgres's
actual `FOR UPDATE` implementation correctly blocks a second real
transaction attempting to lock the same row, and that the blocked
transaction, upon waking, sees the first transaction's committed change.
This is standard, well-established Postgres MVCC/locking behavior (not
something this codebase implements itself — `with_for_update()` is a
SQLAlchemy passthrough to the database engine's own lock primitive), so
the residual risk is that Postgres's own locking is broken, which is
outside this codebase's control to prove or disprove without a live
instance.

## Required-outcome checklist (Workstream 6)
| Requirement | Status |
|---|---|
| Same asset, same thread (two concurrent requests) | Logically proven correct by the idempotent claim-application check (unchanged from 2F-18C); TRUE concurrency not live-testable |
| Same asset, different threads | Logically proven correct by the conflict-detection check (2F-18C) PLUS the lock (2F-18D) making it race-free; TRUE concurrency not live-testable |
| Authorized versus unauthorized request | Unaffected by locking — authorization runs before any claim-conflict question is reached, regardless of timing |
| Two authorized staff requests to different threads | Same as "different threads" above — additionally now gated by this slice's office first-use ambiguity rule if neither staff member is the uploader |
| First transaction rollback followed by second success | Logically consistent with the design (a rolled-back transaction's claim was never committed, so a subsequent request sees the asset as still unclaimed) — not live-testable |
