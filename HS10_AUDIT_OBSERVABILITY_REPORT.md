# HS10 — Audit / Observability Report

## Real, confirmed audit-adjacent trails
| Event | Real record |
|---|---|
| Provider matched | `HomeServiceBookingDraftEvent` (`draft_confirmed`, etc.) |
| Booking created | `FinalCreationAuditLog` (real table, fixed missing `updated_at` in HS7) |
| Technician assigned | `ServiceJobAssignmentEvent` (real, live-verified HS8) |
| Job status changed | `ServiceJobExecutionEvent` (real, live-verified HS8/HS10) |
| Parts request created/approved/rejected | Logged via `ServiceJobExecutionEvent` (`EV_PARTS_REQUIRED` etc.), not a dedicated parts-audit table |
| Job completed | `ServiceJobExecutionEvent` (`EV_WORK_DONE`) + `service_jobs.completion_data` |
| Usage credits deducted | `usage_credit_ledger` row (itself an audit-grade record: actor context via `request_id`, before/after values) |
| Customer review submitted | `Review` row, real, pre-existing Sprint 24 engine |

## Not confirmed as a single, unified event
- "Admin catalog changed" / "Pricing rule changed" / "Tenant service
  published" / "Bookability refreshed" — not verified this session as
  producing a row in a single canonical audit table; these are earlier
  sprints' concerns (HS2-HS5) not re-investigated.
- No single `GET /v1/admin/home-services/jobs/{job_id}/audit` endpoint
  joining all of the above event streams for one job exists — an admin
  investigating a specific job today would need to query
  `execution-timeline`, `assignment-timeline`, and the usage-credit
  ledger separately (all three individually real and correct).

## Audit field completeness (per-event, spot-checked)
`ServiceJobExecutionEvent` and `usage_credit_ledger` rows both include
actor context (`actor_user_id`/`staff_member_id` or
`created_by`/deduction attribution), timestamps, and `request_id` —
confirmed via live response payloads this session. Old/new value pairs
present on execution events (`old_status`/`new_status`).

## Verdict
Audit trails: **real and correct for every event this session directly
exercised**, but scattered across multiple tables/endpoints rather than
unified into one queryable audit log, and not independently verified
for the earlier admin-catalog-side events.
