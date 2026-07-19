# Frontend Adapter Contract

`Ux04OperationsAdapter` (`lib/ux04/types.ts`) defines one method per
required surface: command-center queue, search, booking list/detail, job
list/detail, assignment candidates, status transition, inspection, quote,
checklist, parts requests, invoice, credit/commission, communication,
complaint, compliance submissions.

Per-method contract detail (route/shape/permission/readiness/error
mapping/loading/optimism/cache-invalidation) is **not written out
per-method this pass** — only the typed method signatures exist. This is a
real gap: the brief asked for a documented contract per adapter method
(intended route, request/response shape, required permission, readiness,
error mapping, loading behavior, optimistic-allowed-or-not,
cache-invalidation expectation, product/security blocker) and this pass
only delivered the TypeScript signatures + the `OperationalViewMeta`
envelope (`readiness`, `sourceAdapter`, `lastRefreshedAt`) that every
result carries. A follow-up pass should add a markdown table per method
using UX-03's `frontend-adapter-contract.md` as the format template.
