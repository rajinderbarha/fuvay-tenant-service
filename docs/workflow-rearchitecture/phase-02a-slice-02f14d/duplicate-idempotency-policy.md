# Duplicate & Idempotency Policy

## Unique constraints

No database-level unique constraint exists on `Job.booking_id` or `Job.parent_job_id` (confirmed
via model inspection — both are plain nullable columns). All duplicate protection in this
codebase is **application-level**, not DB-enforced.

## Existing Job lookup by booking_id / parent_job_id

Both now performed in `create_job` (fixed this slice, mirroring pre-existing patterns from
`Booking.convert_to_job` and `convert_to_repair`/`spawn_repair` respectively).

## Behavior per scenario

- **Same request repeated** (booking_id): `DUPLICATE_REJECTED` — the second call finds
  `booking.converted_job_id` already set (if the first call succeeded) or an existing
  `Job.booking_id` row, and raises `JOB_ALREADY_EXISTS_FOR_BOOKING` (409).
- **Same booking used twice**: `DUPLICATE_REJECTED`, same mechanism.
- **Same parent used to create multiple REPAIR jobs from a CONSULTATION**: `DUPLICATE_REJECTED`
  (`CONSULTATION_ALREADY_CONVERTED`, 409, fixed this slice).
- **Same parent used to create multiple non-REPAIR-from-CONSULTATION children**:
  `MULTIPLE_CHILDREN_ALLOWED` — no uniqueness constraint exists or was added; this is consistent
  with there being no evidenced product requirement for it (e.g. a `SERVICE` job might
  legitimately spawn several follow-up jobs).
- **Concurrent creation from one booking**: `CONCURRENCY_RISK_DOCUMENTED` — the
  existence-check-then-insert pattern (`select` then `db.add`) is not wrapped in a
  `SELECT ... FOR UPDATE` or unique constraint, so two simultaneous requests referencing the same
  `booking_id` could both pass the existence check before either commits, producing two Jobs for
  one booking. This is a pre-existing class of race condition already present in
  `Booking.convert_to_job` itself (same pattern, same risk, unmodified) — not newly introduced,
  and not fixed this slice (would require either a DB unique constraint migration or row-level
  locking, both beyond this slice's explicit "do not add a migration" scope unless already an
  approved repository pattern; no such lock pattern exists elsewhere in this codebase for this
  scenario to reuse).
- **Concurrent repair spawning**: same `CONCURRENCY_RISK_DOCUMENTED` class, same reasoning,
  matches the pre-existing risk profile of `convert_to_repair`/`spawn_repair` themselves.
- **Failure after Job creation but before checklist materialization**: not applicable to
  `create_job` — checklist materialization (the normalized `JobChecklistItem` system) never
  happens during `create_job` at all; only the legacy `Job.checklist` JSONB field is populated
  in-memory on the same `Job` object before `db.add`, so there is no separate persistence step
  that could fail independently.
- **Failure after assignment creation**: not applicable — `create_job` never creates an
  assignment.

## No migration added

No database migration was created or is required — this slice's fixes are entirely
application-level existence/consistency checks reusing existing tables.
