# Relationship Revocation Semantics

## Distinguishing "was a relationship legitimately established" from "is a new Job creatable now"

These are evaluated **independently, at each `create_job` call** — there is no persisted
"relationship" record to revoke; the predicate is re-evaluated fresh from current Booking/Job
state every time.

| Event | Effect on a PREVIOUSLY-created Job | Effect on a NEW create_job attempt |
|---|---|---|
| Booking cancellation (after CONFIRMED) | `RELATIONSHIP_PERSISTS_HISTORICALLY` — the already-created Job is unaffected retroactively; it exists regardless of the Booking's later status. | The Booking no longer appears in `QUALIFYING_BOOKING_STATUSES` (`cancelled` excluded) — a fresh relationship check re-run today would need OTHER qualifying evidence (e.g. a resulting Job with `booking_id` set, which DOES still qualify per the Job-lineage rule). |
| Booking expiration | Same as cancellation. | Same as cancellation — `expired` is non-qualifying. |
| Booking rejection | Not applicable (rejection means it never reached `CONFIRMED`; no Job could have resulted from it). | `rejected` is non-qualifying. |
| Job cancellation/voiding | `RELATIONSHIP_PERSISTS_HISTORICALLY` — a Job's own `booking_id`/`parent_job_id` fields are set at creation and never cleared by later status changes; the Job-lineage query has no status filter, so a cancelled/voided Job with a non-null `booking_id`/`parent_job_id` still qualifies. | Same — `RELATIONSHIP_PERSISTS_HISTORICALLY`. |
| Job completion | `RELATIONSHIP_PERSISTS_HISTORICALLY` — same reasoning. | Same. |
| Customer account disablement | `ACCOUNT_STATE_BLOCKS_NEW_JOB` — the pre-existing `customer_user.is_active`/`deleted_at` check (Slice 2F-14F, unmodified) independently blocks ANY new Job (standalone, booking-referenced, or parent-derived) referencing this customer, regardless of relationship history. | Same. |
| Customer account deletion | Same as disablement. | Same. |

## Key distinction

Legitimate relationship **history** is never revoked by a later status change on the Booking or
Job that established it (per the mission's explicit instruction not to revoke legitimate history
merely because the record later concluded). What changes is only whether a **fresh** evaluation
(for a brand-new Job creation) finds CURRENTLY-qualifying evidence — a Booking that has since
moved to a non-qualifying terminal status no longer counts for a NEW attempt, but any Job it
already produced (which itself has `booking_id` set) continues to count indefinitely, since the
Job-lineage rule has no status filter.
