# FINAL-L5-04B — Canonical Seed Alignment Report

## Real seed script: `scripts/seed_entitlements.py`
Deterministic, idempotent, uses `EntitlementService.assign_module_entitlement`/`assign_category_entitlement` (the same production code path the Admin API uses — no separate/parallel seed logic).

## Required setup — matches the mission exactly
| Tenant | Module | Category |
|---|---|---|
| Tenant One (`demo-ac-services`) | Home Services — **ACTIVE** | AC Services — **ACTIVE** |
| Tenant Two (`isolation-test-services`) | Home Services — **ACTIVE** | Plumbing — **ACTIVE** |

## Determinism and idempotency — real, verified
Ran the script **twice** in immediate succession (real command execution, not simulated): first run created 2 module rows + 2 category rows + 4 audit log entries; second run produced **identical row counts** (2/2/4) — the service's idempotent-assign logic (return the existing ACTIVE row unchanged, no new INSERT) was proven, not assumed.

```
module rows: 2   category rows: 2   audit rows: 4   (after first AND second run)
```

## Tenant One cannot inherit Tenant Two categories (and vice versa) — real, verified
Live API check (`GET /v1/tenant/me/entitlements` under each tenant's own JWT):
- Tenant One: `categories: ["ac_services"]` — does not contain `"plumbing"`.
- Tenant Two: `categories: ["plumbing"]` — does not contain `"ac_services"`.

Also verified via real Playwright Chromium E2E (`final-l5-04b-entitlement.spec.ts`, "Tenant isolation" test) — 2/2 assertions passed on live browser sessions.

## Existing `service_jobs`/`service_bookings` remain valid
No historical job/booking rows were modified by this seed — it only inserts new rows into the 3 new entitlement tables, touching nothing else.

## Result
Seed is deterministic, idempotent (proven by double-run), and produces the exact distinct entitlement sets the mission specifies for isolation testing. See `entitlement-seed-manifest.json`.
