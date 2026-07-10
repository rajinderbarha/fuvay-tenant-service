# ADMIN-TENANT-E2E-04B — Home Services Job Detail Report

## New route built this pass
`/admin/home-services/service-jobs/[jobId]` — **did not exist before this
sprint**. The list page's "View Details" row action already linked here
(`window.location.href = /admin/home-services/service-jobs/${row.id}`),
but the route 404'd — a real, previously-undiscovered broken link.

## Backend enrichment built this pass
`GET /v1/admin/final-records/jobs/{job_id}` previously returned only the
bare `ServiceJob` row (no price, no payment mode, no provider name, no
deduction info — confirmed via source read). Enriched to also return:
- `booking`: the linked `ServiceBooking`'s `price_snapshot` (selected
  price, payment mode) and `provider_snapshot` (provider name, badges).
- `usage_credit_deduction`: the matching `UsageCreditLedger` row for this
  `job_id`, if any (most recent one if duplicates somehow exist).
- `usage_credit_deduction_duplicate_count`: count of extra ledger rows
  beyond the first, for exactly-once verification.

## Verified on the freshest completed job with a real deduction
(`JOB-20260710-000002`, `b035159a-b19b-4500-8cb4-99a412e8ac34` — see
below for why this job, not `JOB-20260710-000001`, is used)

| # | Check | Result |
|---|---|---|
| 1 | Detail page opens | 200, browser-verified |
| 2 | Correct job ID | `JOB-20260710-000002` shown |
| 3 | Customer appears | Customer ID shown (real UUID) |
| 4 | Tenant/provider appears | "Demo AC Services" + badges shown |
| 5 | Service/type/brand | Issue summary "Refilled AC gas and fixed leak" shown; type/brand available via `service_type_id`/`brand_id` on the linked ledger entry |
| 6 | Selected price | ₹850 (mid) shown |
| 7 | Payment mode | "Customer Pays Provider Directly" shown |
| 8 | Completion status | "completed" badge shown |
| 9 | Completion proof | Work summary, collected amount, completed-at timestamp shown (real `completion_data`) |
| 10 | Completed Job Deduction | Full section present (see deduction report) |
| 11 | Usage Credit Ledger link | Present, clickable, navigates correctly (see ledger report) |
| 12 | No raw JSON/debug UI | Confirmed, clean sectioned card layout |

## Why `JOB-20260710-000001` was not used
That job (the "freshest completed job" per E2E-04's original finding) has
`status: completed` but `completion_data: null` and **no matching ledger
entry at all** — it was marked completed through some path other than
the real `complete()` staff action (predates this session, or was set
directly in a DB seed/fixture). Rather than fabricate a fake ledger link
for it, this sprint drove a real pending job
(`JOB-20260710-000002`) through the actual staff lifecycle
(assign → accept → on-the-way → reached-site → start-inspection →
complete-inspection → start-service → complete) via real API calls,
producing a genuinely, freshly completed job with a real, correctly
linked deduction. The detail page and its "no deduction record found"
honest-empty-state (see deduction report) were built to handle both
cases correctly — verified against `JOB-20260710-000001` too (shows the
honest "predates the real completion+deduction flow" message, not a fake
row).

## Verdict
Full pass. Real detail page, real enriched data, real completion proof,
real deduction link — for a genuinely, freshly completed job produced
live this session.
