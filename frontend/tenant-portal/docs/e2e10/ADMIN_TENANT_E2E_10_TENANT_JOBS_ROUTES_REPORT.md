# ADMIN-TENANT-E2E-10 — Tenant Jobs Routes Report

## Static Analysis Only

## Routes Discovered

### Primary Jobs Routes (Field Operations)
| Route | File | Purpose |
|-------|------|---------|
| `/jobs` | `app/(tenant)/jobs/page.tsx` | Jobs board — full list with SLA alerts, status filter, search |
| `/jobs/[id]` | `app/(tenant)/jobs/[id]/page.tsx` | Job detail — 360° view, status transitions, quotes, checklist, photos |

### Service Jobs Routes (Assignment/Execution)
| Route | File | Purpose |
|-------|------|---------|
| `/service-jobs` | `app/(tenant)/service-jobs/page.tsx` | Service jobs grid via EnterpriseDataGrid |
| `/service-jobs/[id]` | `app/(tenant)/service-jobs/[id]/page.tsx` | Job assignment detail — assign technician, schedule, cancel |
| `/service-jobs/[id]/execution` | `app/(tenant)/service-jobs/[id]/execution/page.tsx` | Execution tracking — timeline, notes, parts, completion proof |
| `/service-jobs/[id]/quotes` | `app/(tenant)/service-jobs/[id]/quotes/page.tsx` | Quote management for service jobs |

### Finance — Usage Credit Ledger
| Route | File | Purpose |
|-------|------|---------|
| `/finance/usage-credit-ledger` | `app/(tenant)/finance/usage-credit-ledger/page.tsx` | Usage credit balance and ledger transactions |

## Layout Architecture
- All `(tenant)/*` routes are wrapped by `app/(tenant)/layout.tsx` which applies `TenantLayout` globally.
- `jobs/page.tsx` and `jobs/[id]/page.tsx` additionally call `<TenantLayout>` explicitly — this is legacy (pre-Sprint-34K) and results in double-wrapping. The inner TenantLayout's activeNav override is the intended active-nav hint.
- `service-jobs/*` pages render bare — correctly relying on the shell layout for TenantLayout.

## API Endpoints Used
- `jobsApi.list()` → `GET /v1/jobs`
- `jobsApi.get(id)` → `GET /v1/jobs/{id}`
- `jobsApi.slaAlerts()` → `GET /v1/jobs/sla-alerts`
- `serviceJobAssignmentApi.*` → `GET/POST /v1/provider/service-jobs/*`
- `homeServiceExecutionApi.*` → `GET/POST /v1/provider/service-jobs/{id}/execution/*`
- `usageCreditsApi.getBalance()` / `getLedger()` → usage-credit endpoints

## Status: PASS
All routes exist and are wired to real API endpoints via `apiFetch`/`useApi`.
