# CUSTOMER-L5-12 — Status Projection

## Source of Truth: `ServiceBooking.status`, Kept in Sync Server-Side

This sprint's research found that `ServiceBooking.status` is not
independently derived by this client from a separate booking/job
precedence rule — it is **kept in lockstep with the job's status by the
backend itself**, via `home_service_assignment/service.py`'s
`_sync_booking()` helper, called from every real assignment transition
(`assign_job`, `technician_accept_job`, `technician_reject_job`,
`cancel_assignment`, `schedule_job`):

```python
async def _sync_booking(self, booking_id, assignment_status, status):
    booking.assignment_status = assignment_status
    booking.status = status
```

**Consequence**: this client trusts `booking.status` (and
`booking.assignment_status`) directly as the single, already-correct
current-status signal — there is no "before job creation, trust booking;
after job creation, combine booking and job" precedence rule to
implement, because the backend already performs that combination
server-side, atomically, on every real transition. `job_status` (returned
separately by the detail endpoint) is shown as an additional, real data
point when present, but this client never needs to reconcile a divergence
between it and `booking.status`, since the backend's own sync keeps them
aligned by construction.

## The Real, Reachable Status Sequence

Confirmed exhaustively (own research + independent cross-check):

```
pending_assignment → assigned → accepted → scheduled
        ↑_______________|                (cancel/reject)
```

No real code path anywhere in the repository advances a booking or job
past `scheduled` to `dispatched`, `in_progress`, `completed`, or
`cancelled` — those four values are real, defined constants
(`final_records/constants.py`) that are never assigned. This is not a
frontend limitation; it is the actual, current backend implementation
boundary (execution/dispatch/completion is a separate, real, but
currently unwired system — `app/engines/execution/`).

## Provider Acceptance — Re-Scoped

The spec's aspirational "provider accepts or rejects the booking" concept
does not exist as a tenant/provider-level decision in this backend.
What's real is **technician (staff)-level** acceptance:
`ServiceJobAssignment.assignment_status` (`assigned → accepted` via a
real `POST /v1/staff/service-jobs/{job_id}/accept` endpoint, or
`assigned → rejected` reverting to `pending_assignment` via
`.../reject`). This sprint's UI never claims "the provider accepted your
booking" — it renders the backend's own `assignment_message` sentence
verbatim (e.g., "Technician accepted your booking."), which is
technically about the technician, not a separate business-level
acceptance.

## Assignment State

`assignment_status` real values: `unassigned`, `assigned`, `accepted`,
`rejected`, `cancelled`, `reassigned` — each already mapped to a real,
backend-authored customer-safe sentence (`_ASSIGNMENT_DISPLAY` in
`home_service_assignment/customer_router.py`), rendered verbatim by this
client rather than re-derived from the raw code client-side.

## Unknown-State Behavior

Any status code not in `booking-status-registry.ts`'s `REGISTRY` (i.e.,
anything beyond the real, confirmed set) falls back to a generic
"Processing" state — `group: "active"`, `terminal: false`, `success:
false` — per §26's hard requirement that an unknown status never
defaults to a success/terminal/completed presentation. Verified by a
dedicated test (`booking-status-registry.test.ts`'s "fails safe on an
unrecognized status" case).

## Cancellation Behavior

No real booking ever reaches `cancelled` today (per the reachability
finding above) — this sprint's registry maps it correctly for
forward-compatibility, but this is honestly disclosed as untested-in-practice
in `known-gaps.md`, not presented as observed behavior.
