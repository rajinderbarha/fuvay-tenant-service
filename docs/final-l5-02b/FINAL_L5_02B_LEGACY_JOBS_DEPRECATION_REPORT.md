# FINAL-L5-02B — Legacy `/v1/jobs` Deprecation Report

## Current consumers (as of this sprint)
| Application | Files | Domain purpose |
|---|---|---|
| **Tenant Portal** | none (0 active consumers, confirmed via source grep) | — |
| **super-admin** | `frontend/super-admin/lib/api.ts` (`jobsApi`, a separate module from tenant-portal's), consumed by `app/admin/operations/page.tsx`, `app/admin/operations/[jobId]/page.tsx`, `app/admin/tenants/[id]/page.tsx` | **Platform-wide, cross-tenant field-ops oversight** — a genuinely different domain from Tenant Portal's tenant-scoped "my jobs" view; super-admin needs to see jobs across *all* tenants, which `/v1/provider/my-records/jobs` (tenant-scoped by JWT) cannot serve by design |

## Required result for Tenant Portal
**0 active Tenant Jobs page requests to `/v1/jobs`** — **confirmed** via source grep (zero `jobsApi.` references) and live browser network capture (zero `/v1/jobs` requests across dashboard, jobs list, and jobs detail navigation).

## Deprecation status
`/v1/jobs` is **NOT removed** — per rule 2 ("do not keep `/v1/jobs` as the active Tenant Jobs source") the Tenant Portal source dependency is what had to end, and it now has none. Per the mission's own Part 8 instruction ("do not remove the backend route if another verified domain still uses it"), the backend route is retained because super-admin has a real, currently-wired, architecturally-legitimate use for it.

## Removal condition
The backend `/v1/jobs*` route family (and its underlying `jobs`/field_ops table) can be considered for removal only if/when super-admin's platform-wide oversight views are separately migrated to a cross-tenant-capable canonical endpoint (e.g. a `/v1/admin/service-jobs` family reading `service_jobs` with no tenant filter) — not attempted this sprint, as it is outside the Tenant Jobs / Customer Booking scope this mission defines.

## Target sprint/version
Not scheduled — no canonical cross-tenant `service_jobs` admin endpoint currently exists to migrate super-admin onto. Flagged as a real, legitimate follow-up item, not silently dropped.
