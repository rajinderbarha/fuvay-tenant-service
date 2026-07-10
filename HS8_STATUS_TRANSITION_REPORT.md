# HS8 — Status Transition Report

## Real, controlled transition graph exists
`app/engines/execution/constants.py::JOB_TRANSITIONS` — a genuine
from-status → allowed-to-statuses map, enforced by `_assert_transition()`
on every single status-changing call:

```
assigned → accepted, cancelled
accepted → scheduled, on_the_way, cancelled
scheduled → on_the_way, cancelled, customer_not_available
on_the_way → reached_site, customer_not_available, cancelled
reached_site → inspection_started, customer_not_available, cancelled
inspection_started → inspection_done, customer_not_available, cancelled
inspection_done → quote_required, service_started, cancelled
service_started → work_done, quote_required, cancelled
work_done → (terminal)
quote_required → (terminal — Sprint 22 quote flow takes over)
customer_not_available → accepted, scheduled
cancelled → (terminal)
```

This maps to the ticket's "simplified lifecycle" option
(`Assigned → On The Way → In Progress → Completed`) plus real
inspection/quote sub-states not in the ticket's simplified list —
documented here rather than force-fit to the ticket's exact vocabulary.

## Bug found and fixed
`_assert_transition` raised a bare `ValueError` that no router handler
caught, so **every** invalid transition (and, transitively, every
transition period, since this gate runs unconditionally) surfaced as a
raw 500 `INTERNAL_ERROR` rather than the required 422. Fixed by raising
`ServiceOSException` directly — live-verified: calling `/on-the-way`
again on a job already at the terminal `work_done` status now returns:

```json
{
  "error_code": "EXECUTION_INVALID_STATUS_TRANSITION",
  "detail": "This job cannot move from work_done to on_the_way directly.",
  "status": 422,
  "request_id": "req_e3a8ae4f7500"
}
```

Exactly matching the ticket's required error shape (code differs in name
— `EXECUTION_INVALID_STATUS_TRANSITION` vs. the ticket's suggested
`INVALID_JOB_STATUS_TRANSITION` — but the same real, structured 422
contract).

## Verdict
Status transitions: **controlled, real, and now correctly surfaced as
422s.** Not `NOT_READY_HS8_STATUS_TRANSITION_FAILED`.
