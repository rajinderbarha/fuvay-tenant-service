# FINAL-L5-02B — Tenant Jobs Contract Certification

Compared `ServiceJobRecord` (frontend type, `lib/api.ts:2823`) against the live `GET /v1/provider/my-records/jobs` response captured this sprint.

| Field | Frontend type | Live response | Match |
|---|---|---|---|
| List envelope | `{items, total, limit, offset}` | `{"items":[...],"total":5,"limit":50,"offset":0}` | Yes |
| Detail schema | `ServiceJobRecord` | matches field-for-field | Yes |
| Status enums | `string` (not a literal union) | `new`, `assigned`, `in_progress`, `completed`, `cancelled` — matches the 5 seeded statuses and the Jobs page's filter `<Select>` options | Yes |
| Technician schema | `assigned_staff_id: string \| null` (raw ID only) | matches; no resolved name field exists in the response | Yes (honest, not fabricated) |
| Customer-safe fields | N/A (this is a tenant-facing endpoint) | `customer_id` raw only, no PII beyond ID | Yes |
| Price fields | `completion_data.collected_amount` | present on completed job (₹775 for `L501-JOB-0004`) | Yes |
| Payment wording | Rendered live: **"Customer Pays Provider Directly"** on the Customer Booking detail page (Tenant Jobs itself does not render payment wording — it's a Customer-facing string) | matches allowed wording exactly | Yes |
| Completion proof | `completion_data.work_summary`, `.completion_notes` | present | Yes |
| Deduction metadata | Not present on `ServiceJobRecord` — deduction is recorded separately in `usage_credit_ledger`, not embedded in the job payload | N/A — no gap, this is architecturally a separate table by design (per Sprint 9/23 ledger design) | Yes |
| Pagination metadata | `total`/`limit`/`offset` | present, matches | Yes |

## Forbidden wording check
Searched all Tenant Jobs and Customer Booking rendered text (both live browser capture and source): **zero occurrences** of "Wallet Balance", "Tenant Payout", "Escrow", "Provider Earnings Wallet", or "Platform Collected Service Payment" in the customer- or tenant-facing job/booking surfaces touched this sprint.

## Result
**PASS** — no `NOT_READY_FINAL_L5_02B_TENANT_JOBS_CONTRACT_FAILED` condition applies.
