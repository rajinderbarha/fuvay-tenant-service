# Lead/Inquiry State Machine — Slice 2F-11 (Workstream 9)

## Actual statuses (from `app/engines/execution/constants.py`)
`new`, `accepted`, `rejected`, `contacted`, `follow_up`,
`site_visit_planned`, `site_visit_completed`, `qualified`, `unqualified`,
`converted`, `closed_lost`.

## `LEAD_TRANSITIONS` (authoritative, unmodified)
```
new:                  {accepted, rejected}
accepted:             {contacted, unqualified, closed_lost}
contacted:            {follow_up, site_visit_planned, qualified, unqualified, closed_lost}
follow_up:            {contacted, site_visit_planned, converted, closed_lost, unqualified}
site_visit_planned:   {site_visit_completed, closed_lost}
site_visit_completed: {qualified, follow_up, converted, closed_lost}
qualified:            {converted, closed_lost}
unqualified:          {}  (final)
converted:            {}  (final)
closed_lost:          {}  (final)
rejected:             {}  (final)
```

## Per-mutation documentation

| Mutation | Legal source states | Result | Reason required | Audit event |
|---|---|---|---|---|
| accept | `new` | `accepted` | no | `lead_accepted` |
| reject | `new` | `rejected` (final) | yes | `lead_rejected` |
| mark-contacted | `accepted` | `contacted` | no | `customer_contacted` |
| schedule-follow-up | `contacted`, `follow_up`, `site_visit_completed` | `follow_up` | no | `follow_up_scheduled` |
| plan-site-visit | `contacted`, `follow_up` | `site_visit_planned` | no | `site_visit_planned` |
| complete-site-visit | `site_visit_planned` | `site_visit_completed` | no | `site_visit_completed` |
| qualify | `contacted`, `follow_up`, `site_visit_completed` | `qualified` | no | `lead_qualified` |
| disqualify | `accepted`, `contacted`, `follow_up`, `site_visit_completed` | `unqualified` (final) | yes | `lead_unqualified` |
| convert | `follow_up`, `site_visit_completed`, `qualified` | `converted` (final) | no | `lead_converted` |
| close-lost | most non-final states | `closed_lost` (final) | yes | `lead_closed_lost` |

## Ordering (already correct, unmodified)
`_set_status` calls `self._assert_transition(old, new_status)`
**before** mutating `lead.status` or creating the
`RealEstateLeadExecutionEvent` row — confirmed by direct source read.
No "persistence before validation" defect exists here (unlike the
historical complaints-module bugs); no fix was needed.

## Verified this slice
- **Closed/lost leads cannot be silently modified**: `unqualified`,
  `converted`, `closed_lost`, `rejected` all have empty transition sets —
  any further transition attempt raises `ERR_INVALID_TRANSITION` before
  any mutation.
- **Repeated conversion does not create duplicate downstream records**:
  `convert_lead` has no downstream record creation at all (no
  booking/customer record is spawned) — confirmed absent, not merely
  untested; a repeated conversion attempt from `converted` (empty
  transition set) is rejected outright.
- **Provider cannot fabricate customer acceptance**: there is no
  "customer accepted" concept in this state machine at all — every
  transition here is provider/agent-actor-only (`actor_role="agent"`
  hardcoded in `_set_status` calls). Customer involvement is read-only
  (`/tracking`).
- **Customer cannot perform provider-only lead transitions**: structurally
  impossible — `customer_router` has no mutation route at all.
- **Invalid state attempts create no mutation**: `_assert_transition`
  raises before `lead.status = new_status` executes — proven directly
  via the pre-existing service-layer test suite
  (`tests/test_sprint21_execution.py::TestRealEstateExecution`, re-run
  unchanged this slice).

## Not a CRM pipeline invention
This is the actual, existing, unmodified `LEAD_TRANSITIONS` map — no new
status or transition was added or inferred.
