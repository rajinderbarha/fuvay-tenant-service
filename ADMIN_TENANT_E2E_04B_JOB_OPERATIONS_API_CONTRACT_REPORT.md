# ADMIN-TENANT-E2E-04B — Job Operations API Contract Report

## Actual API client functions (this codebase's real module names, not
the ticket's assumed `src/lib/api/admin-home-services.ts` paths — this
project uses a single `frontend/super-admin/lib/api.ts`)

| Ticket's assumed function | Real equivalent | Status |
|---|---|---|
| `getAdminHomeServiceJobs()` | `enterpriseApi` + inline `fetch` to `/v1/admin/final-records/jobs` in `service-jobs/page.tsx` | Works (fixed 401 this pass) |
| `getAdminHomeServiceJobDetail(jobId)` | `finalRecordsAdminApi.getJob(jobId)` (**new this pass**) → `GET /v1/admin/final-records/jobs/{id}` | Works, newly built |
| `getAdminJobCompletedDeduction(jobId)` | Folded into `finalRecordsAdminApi.getJob()`'s `usage_credit_deduction` field (**new this pass**, server-side join) | Works, newly built |
| `getAdminUsageCreditLedger(params)` | `usageCreditsAdminApi.getTenantLedger(tenantId, jobId?)` (extended this pass with optional `job_id`) | Works |
| `getAdminOperationJobs()` | `jobsApi.adminList(params)` → `GET /v1/jobs/admin/all` | Works (pre-existing, unaffected) |

## Rules checked
1. Central API client used — **yes**, `finalRecordsAdminApi` and
   `usageCreditsAdminApi` both go through the shared `apiFetch` helper in
   `lib/api.ts` (auth header, error handling, request_id parsing all
   centralized). The job **list** page (`service-jobs/page.tsx`) does use
   a raw inline `fetch` (pre-existing, not changed this pass) — noted as
   a minor inconsistency, not fixed (out of the "browser-only fix" scope
   for a pre-existing, working pattern).
2. Auth token included — confirmed on all new/modified calls.
3. `request_id` parsed — confirmed, `meta.request_id` present in every
   response and surfaced via `useApi`'s `requestId`.
4. No direct fetch in page components where a central client exists —
   mostly true; the one exception (service-jobs list) is pre-existing.
5. No fake runtime jobs — confirmed via mock-data scan.
6. Job detail and ledger link use the same job/booking reference — **yes**,
   verified: the ledger link URL's `job_id` param is `d.id` (same UUID
   passed through the whole chain), and the ledger API filters
   server-side on the exact same `job_id`.
7. Ledger filter deterministic — **yes**, exact equality filter
   (`UsageCreditLedger.job_id == job_id`), no fuzzy matching.

## Verdict
Real APIs used throughout, auth/request_id/error handling centralized
for all new code. One pre-existing minor inconsistency (list page's raw
fetch) documented, not fixed (unrelated to this sprint's blocker).
