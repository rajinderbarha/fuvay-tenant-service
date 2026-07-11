# FINAL-L5-01D — Legacy `/v1/jobs` Deprecation Decision

## Classification: **ACTIVE_OTHER_DOMAIN** (not simply deprecated/removable)

`/v1/jobs` (`field_ops` engine, `jobs` table) is **not** a pure legacy leftover of the Tenant Jobs feature — it is a separately-designed, richer job-management system (job_type-aware repair/service/consultation workflow, quotes, checklists, SLA alerts, findings/recommendations, spawn-repair) that may serve non-Home-Services verticals or a different product surface than the canonical Home Services `service_jobs` model.

## Current consumers (after this sprint's migration)

| Consumer | Status |
|---|---|
| `app/(tenant)/jobs/page.tsx` (Tenant Jobs list) | **Migrated off** this sprint |
| `app/(tenant)/jobs/[id]/page.tsx` (Tenant Job detail) | **Migrated off** this sprint |
| `app/(tenant)/staff/[id]/page.tsx` (technician profile "recent jobs" widget) | **Still uses it** — not migrated this sprint (secondary consumer, out of scope) |
| `GET /v1/jobs/admin/all` (admin cross-tenant view, `require_super_admin`-gated) | Backend-only, no frontend page confirmed calling it this sprint |

## Reason retained
Cannot be removed or fully deprecated while `staff/[id]/page.tsx` and the admin cross-tenant view still call it, and its richer feature set (quotes/checklist/assessment) has no canonical replacement — removing it would delete real functionality, not just a duplicate.

## Canonical replacement (for the Tenant Jobs surface specifically)
`/v1/provider/my-records/jobs` (+ `/v1/provider/service-jobs/*` for lifecycle actions) — now the exclusive source for the Tenant Portal's primary Jobs pages.

## Deprecation warning
Not added to the backend this sprint (no `Deprecated` OpenAPI flag set) — premature while a real, unmigrated consumer (`staff/[id]/page.tsx`) still depends on it.

## Removal condition
1. Migrate `staff/[id]/page.tsx`'s recent-jobs widget to the canonical endpoint (or confirm it's intentionally showing legacy-domain jobs).
2. Confirm whether the quote/checklist/assessment workflow is a required Home Services feature; if so, design its canonical equivalent before removing the legacy path.
3. Confirm no other vertical (non-Home-Services) depends on `/v1/jobs`.

## Target
FINAL-L5-03 or a dedicated legacy-jobs-consolidation sprint — not this sprint.
