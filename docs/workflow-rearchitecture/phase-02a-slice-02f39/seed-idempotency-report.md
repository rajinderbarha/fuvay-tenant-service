# Seed Idempotency Report

Verified via `TestIdempotency::test_repeated_call_with_same_canonical_role_is_idempotent`
and `TestExistingUserRoleMismatch::test_existing_user_with_matching_role_is_skipped_quietly`:
calling `get_or_create_user` twice with the same email and canonical role
returns the same user id both times, with the second call performing only
a `SELECT` (no `INSERT`/`UPDATE`). This matches the script's own
documented contract ("Idempotent, re-runnable ... only INSERTs, via
existence checks").

Partial failure rollback: not independently tested this slice (requires a
real database transaction to exercise; no PostgreSQL available). The
script runs each `get_or_create_user` call within the same `async with
async_session() as db:` block as the rest of `run()`, so a raised
`ValueError` from the new canonical-role guard propagates up and aborts
the whole seed run before any commit — consistent with "fail fast, no
partial silent state" — but this was verified by code reading, not by an
executed rollback test.
