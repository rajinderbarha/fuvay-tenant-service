# Booking Reference Semantics

## Classification: AUTHORITATIVE_LINEAGE_REFERENCE

`field_ops.Job.booking_id` references `app.engines.booking.models.Booking` (the same model
`Booking.convert_to_job` itself uses — confirmed, no distinct/duplicate booking model exists).

## Evidence for the classification

- **Database FK**: none — `Job.booking_id` and `Booking.id` are not linked by a DB-level foreign
  key constraint (confirmed via model inspection, unchanged across all prior slices).
- **Job status**: `booking_id` does NOT affect the new Job's initial status — always `JS.DRAFT`
  regardless (unlike `Booking.convert_to_job`, which sets `JS.PENDING_ASSIGNMENT`/`JS.ASSIGNED`
  directly).
- **Customer notifications**: `create_job` does not itself fire any user-facing notification; the
  `job.created` domain event carries whatever `customer_id` the Job ends up with (now guaranteed
  consistent with the booking's own, see below).
- **Service selection**: cross-checked (Slice 2F-14D) — a supplied `service_type_id` must match
  `booking.service_type_id`.
- **Assignment**: not affected — `create_job` never creates an assignment.
- **Checklist materialization**: not affected by `booking_id` specifically (driven by
  `service_type_id`'s catalog entry, independent of whether a booking is referenced).
- **Billing/invoice/commission**: not affected — these are separate, later lifecycle events.
- **History/audit**: `booking_id` is stored on the `Job` row itself but not separately mentioned
  in `JobStatusHistory`'s `reason` field (`"Job created"`, generic).
- **Reverse lookups**: `Booking.convert_to_job` performs a reverse lookup
  (`select(FieldJob).where(FieldJob.booking_id == booking_id)`) to guard against a booking already
  having a Job — `create_job` now performs the identical reverse lookup (fixed in Slice 2F-14D).
- **Duplicate prevention**: **YES** — this is the strongest evidence against "informational."
  `create_job` (fixed in 2F-14D) and `Booking.convert_to_job` (pre-existing) both treat
  `booking_id` as unique-per-Job.
- **Frontend/internal callers**: none (`FRONTEND_MUTATION_SURFACE_ABSENT`, re-confirmed).

## Why not AUTHORITATIVE_JOB_SOURCE

`create_job`'s generic endpoint does not derive the Job's initial status, address, pricing, or
assignment from the booking the way `Booking.convert_to_job` does — those fields remain
independently client-supplied/manual. Only customer, service, and uniqueness are authoritative.
This distinguishes it from the full `AUTHORITATIVE_JOB_SOURCE` `Booking.convert_to_job` itself
represents.

## Fixed this slice

Per the mission's explicit instruction ("If booking_id is authoritative or authoritative lineage,
enforce all established source-state prerequisites"), `booking.status == BS.CONFIRMED` is now
required — the same precondition `Booking.convert_to_job` enforces on its own dedicated route.
See booking-status-eligibility.csv for the full per-status adjudication.
