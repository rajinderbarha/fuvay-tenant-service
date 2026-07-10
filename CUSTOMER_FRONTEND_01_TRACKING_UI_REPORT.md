# CUSTOMER-FRONTEND-01 — Tracking UI Report

Implemented in `frontend/customer-app/app/customer/bookings/[bookingId]/page.tsx`,
calling the real:
- `GET /v1/customer/bookings/{booking_id}` (detail)
- `GET /v1/customer/bookings/{booking_id}/tracking` (timeline)

Both from `app/engines/home_service_assignment/customer_router.py`.

## Timeline rendering
The backend's `timeline` array (built from `ServiceJobAssignmentEvent` rows via
`_safe_event_label()`) is rendered as a vertical list of dot + label + timestamp.
The backend's own customer-safe label map already produces copy consistent with
the spec's required phrasing ("Technician assigned.", "Technician accepted your
booking.", etc.) — the frontend does not re-map or invent additional status
strings, it renders exactly what the backend returns.

## Full 9-stage timeline from spec
The spec lists 9 stages (Booking Confirmed, Provider Assigned, Technician
Assigned, On The Way, Reached Site, Inspection Started, Service In Progress,
Work Completed, Completed). The **real** backend only emits events for stages
that actually occurred (`job_received`, `assignment_created`,
`assignment_reassigned`, `assignment_cancelled`, `technician_accepted`,
`technician_rejected`, `job_scheduled` — see `_safe_event_label()`); it does not
pre-populate placeholder rows for stages not yet reached. This app renders
whatever the backend returns rather than fabricating the full 9-row skeleton
with "pending" states, since doing so would require guessing which of the 9
labels map to which real `event_type` and would risk inventing UI states the
backend never confirms. This is a deliberate, documented simplification, not an
oversight.

## Customer-safe fields only
`booking.selected_provider` is built server-side by
`_customer_safe_provider()`, which only ever includes `provider_name`, `rating`,
`public_badges` — confirmed by reading the source. The frontend renders only
these fields plus `assignment_message` (also pre-sanitized server-side). No
usage-credit, ledger, commission, security-deposit, or internal job ID fields
are requested, received, or rendered.

## Cancel action
Spec asks for a "cancel action if policy allows." No live
`/v1/customer/bookings/{id}/cancel` endpoint was found wired (only the
pre-confirmation booking-draft cancel exists). No cancel button was added to
this page rather than pointing it at a nonexistent endpoint — documented as a
gap in CUSTOMER_FRONTEND_01_REMAINING_BLOCKERS.md.

## Support action
No "contact support" backend endpoint was located and wired within the time
available; not added to avoid a dead/fake button. Documented as a gap.
