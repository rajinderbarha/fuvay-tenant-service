# HS8 — Job Status Mapping Report

Actual statuses used (`app/engines/execution/constants.py`), mapped to
the ticket's suggested vocabulary:

| Ticket status | Real status | Notes |
|---|---|---|
| Booking Confirmed | `pending_assignment` (job) / `confirmed` (booking, HS7) | Job starts here, immediately after booking confirmation |
| Assigned | `assigned` | Set by `provider_router.py`'s `/assign` |
| Scheduled | `scheduled` | Optional — only if `/schedule` is called |
| Accepted | `accepted` | Technician-initiated |
| On The Way | `on_the_way` | |
| Arrived | `reached_site` | Same concept, different name |
| In Progress | `inspection_started` → `inspection_done` → `service_started` | Real graph has 3 sub-states the ticket collapses into one "In Progress" |
| Parts Requested | `quote_required` | **Collapsed** — no distinct parts-requested state; see Parts Request report |
| Parts Approved | *(does not exist)* | See Parts Request report |
| Work Completed | `work_done` | Terminal in the current graph |
| Completion Review | *(does not exist)* | No separate review step before "Completed" |
| Completed | *(does not exist as a job status)* | `work_done` is the final job status this pass reaches; a true "Completed" (post usage-credit-deduction, HS9) status was not found |
| Cancelled | `cancelled` | Real, terminal |
| Disputed | *(not part of the execution status graph)* | Handled by a separate complaints/dispute engine (Sprint 75), not the job status field |

## Verdict
Real statuses map reasonably to the ticket's simplified lifecycle option
(`Confirmed → Assigned → On The Way → In Progress → Completed → Cancelled`)
with extra real granularity (inspection/service sub-states) the ticket
didn't ask for removed. The two genuine gaps are Parts
Approved/Completion-Review/true-Completed, documented in their own
reports rather than silently mapped over.
