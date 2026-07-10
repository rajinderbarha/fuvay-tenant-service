# HS8B — Completion Proof Validation Report

## Result: single validated completion action implemented and live-verified

`POST /v1/staff/service-jobs/{job_id}/complete` — new endpoint,
`complete_job()` service method. Payload matches the ticket exactly:
`work_summary`, `collected_amount`, `payment_mode`, `before_photo_ids`,
`after_photo_ids`, `completion_photo_ids`, `customer_signature_id`,
`technician_note`.

## Validation — live-verified, exact required error codes
| Rule | Result |
|---|---|
| Work summary required | **Live-verified**: omitted → `422 WORK_SUMMARY_REQUIRED`, exact ticket message |
| Collected amount required | **Live-verified**: omitted → `422 COLLECTED_AMOUNT_REQUIRED`, exact ticket message |
| Collected amount ≥ 0 | Enforced in `complete_job()` (`ERR_COLLECTED_AMOUNT_INVALID`); not separately live-tested with a negative value this pass, but the same code path as the required-check |
| Payment mode must be `customer_pays_provider_directly` | Enforced (`ERR_PAYMENT_MODE_INVALID`) |
| Job must be in a completable status | Enforced against `COMPLETABLE_JOB_STATUSES = {service_started, work_done, quote_required}` |
| Unresolved parts requests block completion | **Live-verified**: created a fresh `requested` parts request on a job, then called `/complete` → `422 UNRESOLVED_PARTS_REQUESTS_BLOCK_COMPLETION` |
| Completion photo required if policy enabled | Implemented as an opt-in parameter (`require_completion_photo`, defaults `False`) — not enabled by default since no policy-configuration surface exists yet; documented, not silently skipped |

## Implementation note — Pydantic vs. service-layer validation
`work_summary`/`collected_amount` are `Optional` at the Pydantic request-body
level specifically so a missing value reaches `complete_job()`'s explicit
checks (which raise the ticket's exact required codes) instead of a
generic `VALIDATION_ERROR` from FastAPI's own field-required check. Verified
both ways during this pass — the generic-error version was caught and
fixed before this was the final behavior.

## Live-verified successful completion
Real job `JOB-20260709-000001`: `{"work_summary": "Cleaned indoor unit,
checked gas pressure, fixed water leakage.", "collected_amount": 850,
"payment_mode": "customer_pays_provider_directly", "technician_note":
"Customer confirmed cooling is working."}` → `200`, `status: completed`,
`completion_data` persisted on the job with all fields plus
`completed_by_staff_id`/`completed_at`. Customer booking detail
immediately reflected `status: completed` afterward.

## HS9 boundary respected
`completion_data` is prepared and persisted on `service_jobs` for HS9 to
read; **no usage-credit deduction, finance ledger entry, or rating
prompt was implemented** — confirmed by code inspection, out of scope
per the ticket's explicit instruction.

## Verdict
Completion: **a single validated action, cannot happen without work
summary or collected amount** — both live-verified as hard 422s. Not
`NOT_READY_HS8_COMPLETION_PROOF_FAILED`.
