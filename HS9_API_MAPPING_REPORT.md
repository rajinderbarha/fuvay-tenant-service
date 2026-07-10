# HS9 — API Mapping Report

| Ticket suggestion | Real route | Notes |
|---|---|---|
| `POST /v1/tenant/home-services/jobs/{job_id}/complete` | `POST /v1/staff/service-jobs/{job_id}/complete` | Same HS8B completion endpoint — deduction is wired into it, not a separate call |
| `POST /v1/staff/jobs/{job_id}/complete` | `POST /v1/staff/service-jobs/{job_id}/complete` | Prefix is `/service-jobs` |
| `POST /v1/home-services/jobs/{job_id}/finalize-completion` | *(does not exist — not needed)* | Completion + deduction happen atomically in one call, no separate finalize step |
| `POST /v1/home-services/jobs/{job_id}/deduct-usage-credits` | *(does not exist as a standalone endpoint)* | Deliberate — deduction is never a separate customer/tenant-triggerable action, only an automatic side effect of completion, per the hard gate "do not deduct credits before job is completed" |
| `GET /v1/tenant/usage-credits/balance` | `GET /v1/provider/usage-credits/balance` | Real prefix is `/v1/provider`, matches every other tenant-facing endpoint |
| `GET /v1/tenant/usage-credits/ledger` | `GET /v1/provider/usage-credits/ledger` | Same prefix note |
| `GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` | Matches exactly | New this pass |
| `GET /v1/customer/bookings/{booking_id}` | Matches (from HS7) | Unchanged, still correct |
| `POST /v1/customer/bookings/{booking_id}/rating` | *(does not exist)* | See `HS9_CUSTOMER_REVIEW_REPORT.md` |
| `GET /v1/admin/home-services/completed-job-deductions` | *(does not exist — only per-tenant ledger)* | See `HS9_ADMIN_FINANCE_VISIBILITY_REPORT.md` |
| `GET /v1/admin/home-services/jobs/{job_id}/audit` | *(does not exist — HS8's execution-timeline is the closest real equivalent)* | Not deduction-aware |

## New this pass (all additive)
- Deduction wired into the existing `/complete` endpoint's response (`usage_credit_deduction` key).
- `GET /v1/provider/usage-credits/balance`, `GET /v1/provider/usage-credits/ledger` (tenant-facing).
- `GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` (admin).
- New table `usage_credit_ledger` (migration 129).

## Verdict
API integration uses real data. Deduction is deliberately not exposed as
a separately-callable action — this is a design choice enforcing the
hard gate, not a gap.
