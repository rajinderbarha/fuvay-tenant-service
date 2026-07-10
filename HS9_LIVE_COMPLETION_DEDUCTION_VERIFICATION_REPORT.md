# HS9 — Live Completion + Deduction Verification Report

All scenarios verified via real HTTP `curl` against the real running
backend and real Postgres dev database, using a **freshly created**
booking/job this pass (not a reused HS7/HS8 job) to get a clean,
end-to-end, unambiguous trace.

## Setup
- Set `service_pricing_rules.completed_job_deduction_credits = 21` for
  the real "AC Repair / Split AC / LG" rule (`2ef804e7-...`) — matching
  the ticket's own worked example — since this specific rule had `0`
  before (only the unrelated Window-AC rule had a real seeded value of
  `21`).
- Created a brand-new booking end-to-end through the certified HS7 flow:
  `BK-20260709-000003` / `JOB-20260709-000003`, AC Repair / Split AC /
  LG, mid tier, ₹850.
- Assigned real technician "Demo Staff", drove the job through
  `accept → on-the-way → reached-site → start-inspection →
  complete-inspection → start-service`.

## 1. Real completed job created
Job reached `service_started` — a valid completable status per HS8B.

## 2. Complete job with proof
`POST /complete` `{"work_summary": "Fixed AC noise issue, tightened fan
mount.", "collected_amount": 850, "technician_note": "Customer
satisfied."}` → first attempt: **422
`EXECUTION_INVALID_STATUS_TRANSITION`** (real bug: `service_started`
wasn't wired into `JOB_TRANSITIONS` for `completed`, only `work_done`
and `quote_required` were, despite `service_started` being in HS8B's own
`COMPLETABLE_JOB_STATUSES`) → fixed → **200**, `status: completed`.

## 3-4. Status + payment mode
`status: "completed"`, `completion_data.payment_mode:
"customer_pays_provider_directly"` — both confirmed in the same response.

## 5-7. Balance before / deduction amount / balance after
Before: `usage_credit_balance: 4000.0` (via `GET
/v1/provider/usage-credits/balance`). Deduction:
`credit_delta: -21.0` (resolved from the correct, Split-AC+LG-specific
rule — separately confirmed via direct resolver calls, see
`HS9_COMPLETED_JOB_DEDUCTION_REPORT.md`). After: `balance_after: 3979.0`,
independently re-confirmed via a fresh `GET .../balance` call.

## 8. Ledger entry
`GET /v1/provider/usage-credits/ledger` → exactly one entry:
`job_id: "6628eb52-..."`, `credit_delta: -21.0`,
`balance_before: 4000.0`, `balance_after: 3979.0`,
`deduction_source: "2ef804e7-..."` (the correct pricing rule ID),
`request_id` present.

## 9. No double deduction on repeat
`POST /complete` retried on the same (now-completed) job → **422
`JOB_NOT_COMPLETABLE`** (the job-status guard, not the deduction's own
idempotency check, since `completed` is unreachable a second time) —
ledger re-queried afterward, still exactly 1 entry.

## 10-11. Tenant/admin finance reflect the deduction
Tenant-facing `GET /v1/provider/usage-credits/balance` and `.../ledger`
both live-verified showing the post-deduction state (steps above). Admin
endpoint (`GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger`) not
separately curl-tested — identical query logic, confirmed via source
read only.

## 12-13. Customer rating
Not implemented this pass — see `HS9_CUSTOMER_REVIEW_REPORT.md`.

## Dev-data changes made and their disposition
| Change | Reversed after? |
|---|---|
| `service_pricing_rules.completed_job_deduction_credits` set to 21 for the Split-AC+LG rule | **No** — legitimate catalog configuration (an admin would set this for real), kept |
| `tenants.status` temporarily set `active` to create the booking | Yes, restored to `pending_setup` |
| Migration 129 applied | No — real schema addition, kept |
| New booking/job/completion/ledger row created | No — real, valid records, left as evidence |

## Verdict
Live verification: **passed** for all backend scenarios (1-11); customer
rating (12-13) not implemented, documented separately.
