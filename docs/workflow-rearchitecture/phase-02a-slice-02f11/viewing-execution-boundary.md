# Viewing/Execution Boundary — Slice 2F-11 (Workstream 10)

## What actually exists
There is no standalone "viewing" or "site visit" record — `site_visit_planned`
and `site_visit_completed` are two ordinary statuses within
`RealEstateLead`'s own `LEAD_TRANSITIONS` state machine (see
`lead-inquiry-state-machine.md`), not a separate Booking, ServiceBooking,
Job, ServiceJob, or Assignment record. The "viewing" is simply a phase of
the lead's own lifecycle, executed by the same assigned agent who owns
the lead throughout.

## No adapter between pipelines
Per the mission's explicit instruction, no adapter was created or
implied between this lead-status-based "site visit" concept and the
canonical `Booking`/`ServiceBooking`/`Job`/`ServiceJob` pipelines — they
remain entirely separate, unconnected concepts. `RealEstateLead` has no
foreign key to any booking/job table.

## Requirements review
- **Customer cannot schedule or complete a provider-side viewing**:
  confirmed — `plan-site-visit`/`complete-site-visit` are both
  agent-only mutations (`require_owner_or_office_staff_mutation`, fixed
  this slice); no customer-facing equivalent route exists.
- **Technician cannot complete an unassigned viewing**: technician is
  excluded from the mutation guard entirely (no caller evidence exists
  for technician involvement in this vertical) — a technician cannot
  reach `complete-site-visit` (or any other mutation) at all now,
  regardless of assignment.
- **Provider cannot record customer acceptance without an explicit
  supported workflow**: there is no "customer acceptance" concept in this
  state machine (see `lead-inquiry-state-machine.md`) — nothing to
  fabricate.
- **Completed/cancelled execution cannot be silently changed**:
  `site_visit_completed`'s own transition set (`qualified`, `follow_up`,
  `converted`, `closed_lost`) is the only further movement permitted —
  correct, unmodified, and does not represent "silent" reversal of the
  visit itself.
- **Invalid transition causes no partial record creation**: confirmed —
  `_assert_transition` raises before any mutation or event-row creation.
