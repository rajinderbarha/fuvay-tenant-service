# CUSTOMER-L5-13 — Assignment Contract

## Canonical Assignment Source (Unchanged From CUSTOMER-L5-12)

`ServiceJobAssignment`/`ServiceJobAssignmentEvent`
(`app/engines/home_service_assignment/`) remain the canonical
technician-assignment records — this sprint does not introduce a second,
competing assignment model. `booking.assignment_status`/`job.status` are
kept in lockstep server-side (`_sync_booking`, documented in
CUSTOMER-L5-12's `status-projection.md`) — this sprint's own new
execution-engine statuses (`on_the_way`, `reached_site`, etc.) are written
onto the exact same `ServiceJob.status` column by a *different* real
engine (`execution/`), not a competing assignment concept — see
`baseline-verification.md`'s Central Findings #1.

## Lifecycle (Extended This Sprint)

```
pending_assignment → assigned → accepted → scheduled
  → on_the_way → reached_site → inspection_started → inspection_done
  → (quote_required) → service_started → work_done → completed
  (or → customer_not_available / cancelled / failed at various points)
```

The first four transitions are owned by `home_service_assignment`
(CUSTOMER-L5-12); everything from `on_the_way` onward is owned by
`execution` (this sprint). Both write to the same real `ServiceJob.status`
column, confirmed by direct source reading of both engines' service
files.

## Visibility

Unchanged from L5-12: the customer never sees a raw assignment ID,
technician ID, or internal actor identity — only `assignment_status`/
`job.status` (via the centralized registry) and the real, backend-authored
`assignment_message` (L5-12) or this sprint's own client-side
customer-safe execution-event labels (`execution-event-labels.ts`, since
the execution engine's endpoint does not provide its own labels the way
the assignment engine's does).

## Reassignment / Supersession

No new reassignment behavior was found or built this sprint —
`assignment_reassigned` (L5-12's own event type) remains the only real
reassignment signal. This sprint's execution timeline is scoped to a
single, current job (`ServiceJob.booking_id` unique-ish relation,
unchanged since L5-12's `booking-job-contract.md`) — there is no
multi-job/multi-assignment scenario to reconcile.

## Job Relation

This sprint's `ServiceTrackingScreen` requires a real `job.id`, obtained
via the reused CUSTOMER-L5-11 `useBookingDetail` hook
(`/v1/customer/my-activity/bookings/{bookingId}`) — the only real
customer endpoint that returns a raw job ID. When no job exists yet
(`job` is `null`), the screen shows an honest "No service activity yet"
state rather than attempting the tracking fetch at all.

## Contact Relation

No real contact/masked-call relation exists for either the assignment or
execution engine — confirmed absent (`contract-matrix.md`). The tracking
screen shows a static, non-interactive "Contact" informational row.

## Test Coverage

Covered by `booking-status-registry.test.ts`'s new assertions for every
real execution-engine status, and `execution-timeline-schema.test.ts`'s
real timeline/job-status parsing tests.
