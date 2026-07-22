# Duplicate & Concurrency Review

## Reconfirmed from Slice 2F-14D (unchanged)

- **Duplicate Job from one Booking**: `DUPLICATE_REJECTED` (`JOB_ALREADY_EXISTS_FOR_BOOKING`,
  409) — application-level guard (`booking.converted_job_id` + `Job.booking_id` existence
  query), no DB unique constraint.
- **Duplicate repair from one parent consultation**: `DUPLICATE_REJECTED`
  (`CONSULTATION_ALREADY_CONVERTED`, 409) — same application-level pattern.
- **Concurrent creation from one booking / concurrent repair spawning**:
  `CONCURRENCY_RISK_DOCUMENTED` — the select-then-insert pattern is not wrapped in
  `SELECT ... FOR UPDATE` or backed by a DB unique constraint; two simultaneous requests could
  both pass the existence check before either commits. This is a pre-existing risk class shared
  identically with `Booking.convert_to_job`/`convert_to_repair` themselves (same pattern, same
  risk, unmodified — not newly introduced by any 2F-14 slice).
- **Transaction rollback behavior**: all new/existing validation checks raise before `db.add`;
  a raised exception propagates to the request-scoped transaction manager (unchanged,
  out-of-scope infrastructure), which rolls back any partial state. No test-observable partial
  persistence occurs (verified via `db.add.assert_not_called()` across every rejection test in
  Slices 2F-14C/D/E).

## New this slice

- **Booking status check** (`BS.CONFIRMED` required) and **parent status check**
  (`JS.QUOTE_APPROVED` required for CONSULTATION→REPAIR) both execute in the SAME
  linked-record-validation block, before `db.add` — same transactional guarantees as all other
  checks in this block (see transactional-consistency.md, Slice 2F-14D, unchanged pattern).
- **Dual-source rejection** (`AMBIGUOUS_JOB_SOURCE`) executes FIRST, before either the booking or
  parent block runs — confirmed via source order (the check is placed immediately after the
  `service_type_id`/`job_type` validation, before `parent = None` is even initialized).

## Classification

`DUPLICATE_REJECTED` for both booking-to-Job and consultation-to-repair (deterministic,
correctly ordered). `CONCURRENCY_RISK_DOCUMENTED` for true concurrent races — this is an accepted,
pre-existing risk class, not fixed this slice (would require a DB migration for a unique
constraint, out of scope unless already an approved repository pattern, and no such pattern
exists for this specific scenario anywhere in this codebase).
