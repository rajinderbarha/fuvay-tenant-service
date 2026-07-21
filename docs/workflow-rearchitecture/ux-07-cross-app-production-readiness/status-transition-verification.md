# Status-Transition Verification — Round 3 (Workstream 1 deepening)

Continuing Round 1's real job (`JOB-20260721-000008` /
`4284c162-1f78-45aa-b6b3-df8acf14f076`, booking `BK-20260721-000008`),
which was left at `accepted` at the end of Round 1. All transitions below
are real, live `POST` calls against the real backend, using the exact
literal actions from `mobile/staff-app/src/lib/transitions.ts`'s
`NEXT_ACTION` graph (no invented transitions).

## Full real transition sequence executed this round

| # | Action | Endpoint | Resulting status |
|---|---|---|---|
| 1 | `onTheWay` | `POST /v1/staff/service-jobs/{id}/on-the-way` | `on_the_way` |
| 2 | `reachedSite` | `POST /v1/staff/service-jobs/{id}/reached-site` | `reached_site` |
| 3 | `startInspection` | `POST /v1/staff/service-jobs/{id}/start-inspection` | `inspection_started` |
| 4 | `completeInspection` | `POST /v1/staff/service-jobs/{id}/complete-inspection` | `inspection_done` |
| 5 | `startService` | `POST /v1/staff/service-jobs/{id}/start-service` | `service_started` |
| 6 | `workDone` | `POST /v1/staff/service-jobs/{id}/work-done` | `work_done` |
| 7 | `complete` | `POST /v1/staff/service-jobs/{id}/complete` (body: `work_summary`, `collected_amount:775.0`, `payment_mode:"customer_pays_provider_directly"`) | `completed` |

**The job reached `completed` this round** — the full real graph
(`assigned -> accepted -> on_the_way -> reached_site -> inspection_started
-> inspection_done -> service_started -> work_done -> completed`) was
walked end-to-end via 8 real, legal actions (1 in Round 1, 7 this round),
with zero invented transitions and zero skipped states.

## Cross-app reflection, verified live

- **Tenant-portal**: `GET /v1/provider/service-jobs/{id}/execution-timeline`
  -> real event list showing `technician_on_the_way`,
  `technician_reached_site`, and subsequent events with real
  `old_status`/`new_status` pairs matching the table above exactly.
- **Customer-app**: `GET /v1/customer/bookings/{booking_id}` (re-fetched
  after each major transition) -> `status` field tracked the transitions
  in real time, ending at `status:"completed"`. The customer-safe response
  never exposed `completion_data.collected_amount` as an online-payment
  event — only the same `payment_mode:"customer_pays_provider_directly"`
  and `selected_price_amount` fields already present before completion (see
  `completion-commission-review-verification.md` for the full field list).

## What this resolves from Round 1's deferral

Round 1's `quote-checklist-parts-verification.md` said the job was left at
`accepted` as "a valid resumption point." This round picked it up from
exactly there and carried it, via the REAL graph, all the way to
`completed` — see `completion-commission-review-verification.md` for what
happened at that terminal state (real commission/credit deduction, real
customer_reviews submission).

## Real, honest note on the "quote_required" branch

The graph also defines `quote_required: ["complete"]` as an alternate
predecessor to `completed` — this round's real job never entered
`quote_required` (it took the direct `service_started -> work_done ->
completed` path), so that branch was NOT exercised. See
`quote-checklist-parts-live-evidence.md` for why (no real quote-creation
endpoint was found wired to this job family this round).
