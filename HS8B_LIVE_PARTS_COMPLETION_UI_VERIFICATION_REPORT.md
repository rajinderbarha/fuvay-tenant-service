# HS8B — Live Parts + Completion + UI Verification Report

All scenarios verified via real HTTP `curl` against the real running
backend and real Postgres dev database, using the real HS7/HS8 jobs
(`JOB-20260709-000001`, `JOB-20260709-000002`, tenant "Demo AC
Services", technician "Demo Staff").

## 1-2. Assign + move to inspection/service (carried over from HS8, still valid)
Both jobs were already at `work_done` / `quote_required` respectively
from HS8's live verification, both valid entry points into HS8B's new
flows.

## 3-4. Create parts request — valid and invalid
Valid: `{"part_name": "Compressor capacitor", "quantity": 1,
"estimated_cost": 450, "reason": "..."}` → `200`, `status: requested`.
Invalid (empty `part_name`): → `422 PART_NAME_REQUIRED`.

## 5-6. Approve as tenant, mark installed
`POST .../parts-requests/{id}/approve` (as `provider@serviceos.in`) →
`200`, `status: business_approved`. `POST .../install` → `200`,
`status: installed`.

## Reject + install-block (ticket's own required test #10)
Second parts request rejected (`reason: "Not needed for this repair"`)
→ `status: business_rejected`. `POST .../install` on it →
`422 PARTS_REQUEST_REJECTED_CANNOT_INSTALL`.

## 7-8. Completion without work summary / without collected amount
Both → clean `422`s with the ticket's exact codes
(`WORK_SUMMARY_REQUIRED`, `COLLECTED_AMOUNT_REQUIRED`).

## 9. Complete job with work summary and collected amount
`200`, `status: completed`, full `completion_data` persisted
(`work_summary`, `collected_amount: 850.0`,
`payment_mode: customer_pays_provider_directly`, `technician_note`,
`completed_by_staff_id`, `completed_at`).

## 10. Customer tracking updates
`GET /v1/customer/bookings/{booking_id}` → `status: completed`,
`job_status: completed`, `payment_mode` unchanged, no internal data leaked.

## Additional scenario (not in the ticket's numbered list, but a real
gate the ticket requires elsewhere)
Unresolved parts request blocks completion: created a fresh `requested`
parts request on job 2, then called `/complete` → `422
UNRESOLVED_PARTS_REQUESTS_BLOCK_COMPLETION`.

## 12-13. UI verification
Not verified via a live browser session — no dev server was started and
clicked through this pass (time budget). Verified instead via a clean
`npx tsc --noEmit` compile (0 errors) across both the new technician
pages and the extended tenant execution page, plus direct source
inspection confirming the completion-proof section only renders
`work_summary`/`collected_amount`/the fixed payment-mode label (no
internal fields).

## Dev-data changes made and their disposition
| Change | Reversed after? |
|---|---|
| Migration 128 applied | No — real schema addition, kept |
| Job 1 completed (`status: completed`, real `completion_data`) | No — real, valid terminal state, left as evidence |
| Job 2: 1 parts request installed, 1 rejected, 1 left `requested` (blocking completion) | No — real, valid state demonstrating the block, left as evidence |

## Verdict
Backend live verification: **passed** for all ticket-required scenarios
except the two UI-specific ones (12, 13), which were verified by
TypeScript compile + source inspection rather than a live browser
session.
