# Tenant My Status — Integration Report

## Live-verified endpoint matrix (provider@serviceos.in, tenant_owner, tenant 34b427a7-b2be-496c-b826-6d51bb181248)

| Endpoint | Method | Status before fix | Status after fix |
|---|---|---|---|
| `/v1/provider/status` | GET | **500** (UndefinedTableError: `provider_visibility_statuses`) | 200 |
| `/v1/provider/status/offerings` | GET | **500** (UndefinedTableError: `provider_offering_bookable_statuses`) | 200 |
| `/v1/provider/offerings/enabled` | GET | **500** (UndefinedTableError: `provider_enabled_offerings`) | 200 |
| `/v1/provider/status/refresh` | POST | 200 (stub, no-op) | 200 (stub, no-op) |
| `/v1/provider/onboarding/package-summary` | GET | 200 | 200 |
| `/v1/tenant/security-deposit` | GET | 200 | 200 |
| `/v1/tenant/credit-wallet` | GET | 200 | 200 |
| `/v1/tenant/service-areas` | GET | 200 | 200 |
| `/v1/provider/team-members` | GET | 200 | 200 |
| `/v1/provider/availability` | GET | 200 | 200 |
| `/v1/tenants/{id}/audit-log` | GET | 200 | 200 |
| `/v1/auth/me` | GET | 200 | 200 |

## Root cause

The current page's generic "Unexpected error." was not a frontend bug — it was three
production database tables never having been created: `provider_visibility_statuses`,
`provider_offering_bookable_statuses`, `provider_enabled_offerings`. Every call the existing
page made to `/v1/provider/status` and `/v1/provider/status/offerings` was hitting a live 500
(`asyncpg.exceptions.UndefinedTableError`), which the frontend's generic error handler flattened
into "Unexpected error." with no further detail.

## Fix

`alembic/versions/115_provider_status_offerings_tables.py` — idempotent-guarded migration
creating all three tables, matching each router's INSERT/SELECT/UPDATE column list exactly (read
directly from `app/engines/provider_portal/router.py`, not guessed). Ran `alembic upgrade head`
against the live database; re-verified all three endpoints return `200` with correct
zero-state data for a tenant with no rows yet.

## Real data observed for the certified test tenant (Demo AC Services)

- Package: "Starter Home Services", status `paid_pending_approval` ("Your package will start
  after admin approval."), included credits 1000.
- Usage credit balance: 0 (not yet approved/credited — consistent with package not active).
- Security deposit: required ₹5,000, paid ₹0, status `unpaid`.
- Service areas: 1 (Ludhiana, 141001).
- Team members: 1 active technician (Demo Staff).
- Availability: 0 rules configured.
- Enabled offerings: 0.
- This produces a realistic, fully "Not Bookable" scenario with 5 of 7 required actions blocked
  — exactly the kind of state the page needed to render correctly, and did.

## request_id propagation

Every section (`useApi`/`useAction`) exposes `requestId` from `ServiceOSError`, and every
section-level error state (`TenantStatusSectionError`) renders it, along with which API/section
failed and a Retry action.
