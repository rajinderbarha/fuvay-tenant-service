# Consultation/Session State Machine — Slice 2F-12 (Workstream 9)

## Actual statuses (from `app/engines/execution/constants.py`)
`confirmed`, `accepted`, `rejected`, `scheduled`, `started`, `completed`,
`no_show`, `reschedule_requested`, `cancelled`.

## `APPT_TRANSITIONS` (authoritative, unmodified)
```
confirmed:             {accepted, rejected, no_show, cancelled}
accepted:              {scheduled, started, no_show, reschedule_requested, cancelled}
scheduled:              {started, no_show, reschedule_requested, cancelled}
started:               {completed, no_show}
completed:              {}  (final)
no_show:                {}  (final)
reschedule_requested:   {accepted, cancelled}
rejected:               {}  (final)
cancelled:               {}  (final)
```

## Per-mutation documentation

| Mutation | Legal source states | Result | Reason required | Assignment-limited | Audit event |
|---|---|---|---|---|---|
| accept | `confirmed` | `accepted` | no | yes | `appointment_accepted` |
| reject | `confirmed` | `rejected` (final) | yes | yes | `appointment_rejected` |
| start | `accepted`, `scheduled` | `started` | no | yes | `appointment_started` |
| complete | `started` | `completed` (final) | no | yes | `appointment_completed` |
| no-show | `confirmed`, `accepted`, `scheduled`, `started` | `no_show` (final) | no | yes | `customer_no_show` |
| request-reschedule | `accepted`, `scheduled` | `reschedule_requested` | no | yes | `reschedule_requested` |
| cancel (provider) | most non-final states | `cancelled` (final) | yes | **no** (see below) | `appointment_cancelled` |

## Ordering (already correct, unmodified)
`_set_status` calls `self._assert_transition(old, new_status)`
**before** mutating `appt.status` or creating the
`CoachingAppointmentExecutionEvent` row — confirmed by direct source
read, same pattern as real estate. No "persistence before validation"
defect exists here.

## Verified this slice
- **Cancelled/completed/rejected/no-show appointments cannot be silently
  modified**: all 4 have empty transition sets — any further transition
  raises `ERR_INVALID_TRANSITION` before any mutation.
- **Customer cannot mark provider attendance/completion**: there is no
  customer-facing mutation of any kind in this router.
- **Technician cannot act on an unassigned session**: technician is
  denied at the persona layer entirely, for every mutation.
- **Reschedule cannot target another tenant's slot**: N/A — no slot
  concept exists in this router; `request_reschedule` only transitions
  the appointment's own status, it does not select a new slot/time at
  all (confirmed by service signature — no date/time parameter).
- **Invalid transitions produce no mutation**: `_assert_transition`
  raises before any `db.add`/status change.

## `cancel_appointment`'s non-assignment-limited design
Unlike the other 7 mutations, `cancel_appointment` never calls
`_assert_staff_owns_appt` — any tenant_owner/staff (not just the
assigned one) may cancel. This is documented, not fixed, as a plausible
intentional business design (front-desk/manager cancellation authority)
consistent with `require_owner_or_office_staff_mutation`'s own
business-wide (not assignment-scoped) persona set. Flagged in
`product-decisions-required.md` as a question worth an explicit product
decision if the business wants otherwise, but not treated as a security
defect — closure requires the acting role to be an authorized office
persona regardless (fixed this slice).
