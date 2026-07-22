# Frontend / Internal Caller Audit

## Searched

All of `frontend/` for callers of `create_job`, `convert_to_repair`, `spawn_repair`,
`respond_to_quote`, `create_quote`, `create_job_quote`, `approve_job_quote`, `reject_job_quote`,
`send_job_quote`.

## Found

`frontend/tenant-portal/lib/api.ts` defines client functions targeting `spawn-repair` and
`quotes/{id}/respond` (`spawnRepair`, `respondToQuote` or equivalent). Zero page/component call
sites exist anywhere under `frontend/*/app/**` — confirmed via grep across all frontend apps.

The one relevant page, `frontend/tenant-portal/app/(tenant)/jobs/[id]/page.tsx`, carries an
explicit migration comment (`FINAL-L5-01D`) stating it was moved off the legacy `jobsApi`/
`quotesApi` field_ops surface onto the canonical `service_jobs` pipeline, and that "the legacy
detail page's quote/checklist/assessment/spawn-repair sections have NO equivalent in the
canonical service_jobs model" — i.e., this capability was deliberately abandoned by the frontend,
not merely unwired.

## Result

**FRONTEND_MUTATION_SURFACE_ABSENT** for all 9 routes in this slice's scope. No live caller
exists; the dead `api.ts` client functions are not built, modified, or removed — they are simply
confirmed inert, consistent with the same finding pattern established in Slice 2F-14's own
frontend-mobile-exposure-audit.md. No regression risk from any guard change made this slice.
