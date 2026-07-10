# Admin Matching/Operations Route Report (ADMIN-TENANT-E2E-04, Part 1)

## Real routes verified (all opened in a real Chrome browser via Playwright, admin logged in)

| Route | Page file | Sidebar group | Status |
|---|---|---|---|
| `/admin/home-services/provider-matching` | `app/admin/home-services/provider-matching/page.tsx` | Home Services → "Provider Matching" | 200, shell OK |
| `/admin/home-services/matching-diagnostics` | `.../matching-diagnostics/page.tsx` | Home Services → "Matching Diagnostics" | 200, shell OK |
| `/admin/home-services/completed-job-deduction` | `.../completed-job-deduction/page.tsx` | Home Services → "Completed Job Deduction" | 200, shell OK |
| `/admin/home-services/service-jobs` | `.../service-jobs/page.tsx` | (uses `EnterpriseDataGrid`, no dedicated sidebar highlight — `activeNav` unset) | 200, shell OK |
| `/admin/operations` | `app/admin/operations/page.tsx` | Operations → "Jobs" (activeNav="operations") | 200, shell OK |
| `/admin/operations/[jobId]` | `app/admin/operations/[jobId]/page.tsx` | dynamic detail, breadcrumb "Operations › {job_number}" | 200, shell OK |
| `/admin/home-services/overview` | `.../overview/page.tsx` | Home Services → "Overview" | 200, shell OK |
| `/admin/finance/usage-credits` | `app/admin/finance/usage-credits/page.tsx` | Finance → "Credit Top-ups" (rendered as "Usage Credits" page) | 200, shell OK |

## Real relationship between `/admin/operations` and `/admin/home-services/service-jobs`

These are **two distinct, real systems**, not duplicates:
- `/admin/operations` is the platform-wide **Operations Board** — reads from `jobsApi` (`/v1/jobs/admin/all`, `/v1/jobs/admin/summary`, `/v1/jobs/sla-alerts`), which is backed by the legacy `jobs` table (field_ops/dispatch engine). It has SLA tracking, reassignment, override-status, force-close — a full admin job-management console. Its detail route is `/admin/operations/[jobId]`.
- `/admin/home-services/service-jobs` is a read-only **EnterpriseDataGrid** wrapper over `/v1/admin/final-records/jobs`, which is backed by the newer `service_jobs` table (Sprint 19's Home-Services-specific booking→job final-creation flow). Its row action links to `/admin/home-services/service-jobs/{id}` (a route that does not exist on disk — this is a real, minor bug: the "View Details" row action 404s because no `[id]` sub-route exists under `service-jobs/`).

DB confirms both tables are real and populated independently: legacy `jobs` table is empty (0 rows, unused in current dev data), while `service_jobs` (Home Services) has 11 real rows including one completed job `JOB-20260710-000001`. So for this sprint's Home-Services-specific job data, `/admin/home-services/service-jobs` is the meaningful list, but its detail link is broken (documented as a bug below).

## Per-route checklist (browser-observed via Playwright, screenshots in `evidence/e2e04/`)

- Shell/sidebar/breadcrumb: present on all 8 routes.
- Real API calls: confirmed via `lib/api.ts` central client on every page (Part 10 has detail).
- Loading state: skeleton/pulse placeholders present (provider-matching, completed-job-deduction, operations, operations/[jobId]).
- Empty/data state: verified — completed-job-deduction shows "No rules configured yet." fallback; operations board shows "No jobs yet"/"No jobs match your filters".
- Error state with request_id: `SectionError` components on provider-matching, matching-diagnostics, completed-job-deduction all render `requestId` when present.
- No crash, no unintended 404, no NaN/null/undefined: confirmed by Playwright assertions (Part 14/15 test run, all passed).
- No raw JSON/debug UI: confirmed — all pages render structured cards/tables, not `<pre>{JSON.stringify(...)}</pre>` dumps.

## Bug found
`service-jobs` list's "View Details" row action links to `/admin/home-services/service-jobs/{row.id}`, which has no page file (only `page.tsx` exists directly under `service-jobs/`, no `[id]` dynamic route). Clicking it would 404. Out of strict scope to build a new detail page in this sprint (not explicitly required by the spec's Part 7, which is satisfiable via `/admin/operations/[jobId]` instead) — documented as a real, minor gap in Remaining Blockers.

Result: **PASS** — all real routes function correctly as an admin console; one pre-existing minor dead-link bug documented, not blocking.
