# HS9B — API Mapping Report

| Ticket suggestion | Real route | Notes |
|---|---|---|
| `GET /v1/tenant/usage-credits/balance` | `GET /v1/provider/usage-credits/balance` | Real prefix `/v1/provider`, built in HS9 |
| `GET /v1/tenant/usage-credits/ledger` | `GET /v1/provider/usage-credits/ledger` | Same prefix note |
| `GET /v1/tenant/home-services/jobs/{job_id}` | `GET /v1/provider/service-jobs/{job_id}/assignment-context` | From HS8, unchanged |
| `GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` | Matches exactly | Built in HS9 |
| `GET /v1/admin/home-services/completed-job-deductions` | *(does not exist — cross-tenant view not built)* | See HS9B_ADMIN_FINANCE_UI_REPORT.md |
| `GET /v1/admin/finance/usage-credits` | *(does not exist as a summary route — per-tenant ledger only)* | Same |
| `POST /v1/admin/tenants/{tenant_id}/usage-credits/adjust` | `POST /v1/admin/tenants/{tenant_id}/add-usage-credits` | Real, pre-existing (not built this pass), now wired into the new admin UI |
| `POST /v1/customer/bookings/{booking_id}/rating` | Matches exactly | New this pass |
| `GET /v1/customer/bookings/{booking_id}/rating` | Matches exactly | New this pass |
| `POST /v1/provider/status/refresh` | Matches (pre-existing, HS4B) | Used for live low-credit verification |
| `POST /v1/home-services/matching/select-provider` | `select_best_provider()` (internal function, called from `/booking-drafts/{id}/match-and-price`) | Unchanged from HS6/HS6B/HS7 |
| `POST /v1/admin/home-services/matching-diagnostics` | Matches (pre-existing, HS6B) | Now surfaces `INSUFFICIENT_USAGE_CREDITS` reason |

## New this pass (all additive)
- `POST /v1/customer/bookings/{booking_id}/rating`, `GET .../rating`.
- Matching engine surfaces a more specific `INSUFFICIENT_USAGE_CREDITS` reason code.
- Frontend: `usageCreditsApi` (tenant-portal), `usageCreditsAdminApi` (super-admin).

## Verdict
API integration uses real data; routes consistently use the established
`/v1/provider/*` and `/v1/customer/bookings/*` prefixes rather than the
ticket's suggested `/v1/tenant/*` naming.
