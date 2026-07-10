# HS4B — API Mapping Report

## Real endpoint touched
`POST /v1/provider/status/refresh` — real, pre-existing route, **fixed
this sprint** (was a no-op, now performs real computation + DB write).
`GET /v1/provider/status` — real, pre-existing, unchanged (reads the
same table the fix now correctly populates).

## Ticket's suggested vs. real
| Ticket-suggested | Real |
|---|---|
| `POST /v1/provider/status/refresh` | Exact match — this is the real route, confirmed and fixed |
| `GET /v1/tenant/home-services/readiness` | Same as `GET /v1/provider/status` |
| `GET /v1/tenant/setup/checklist` | No dedicated endpoint — checklist is computed client-side in `TenantLayout.tsx` from `providerStatusApi.get()` + other calls |
| `POST /v1/tenant/home-services/services/publish` | Real — `POST /v1/tenant/catalog/enabled-services/{id}/publish` |
| `GET /v1/tenant/package/limits` | Real — `tenant_limits` table, read via `tenant_engine` |
| `GET /v1/tenant/usage-credits/balance` | Real — `tenant_billing.credit_balance`, now read directly by the new bookability computation |
| `GET /v1/tenant/security-deposit/status` | Real — `tenant_billing.security_deposit_paid`/`security_deposit_amount`, now read directly |
| `GET /v1/tenant/home-services/service-areas` | Real — `tenant_service_areas` table, now read directly |
| `GET /v1/tenant/home-services/availability` | Real — `provider_availability_rules` table, now read directly |

## No mock data
Every signal in the new `_evaluate_provider_bookability` function reads
a real table via direct SQL — confirmed live against the real dev DB
with 4 distinct verified scenarios (see Live Curl Verification Report).

## Verdict
API integration: **real**. The core fix consolidates reads from 5 real
tables into one computation function rather than requiring 5 separate
new endpoints — a pragmatic, real, DB-backed implementation matching
the ticket's intent.
