# FINAL-L5-02B — Tenant Job Detail and Actions Report

`app/(tenant)/jobs/[id]/page.tsx` was already fully migrated in FINAL-L5-01D and required no code changes this sprint. This report re-verifies it against this sprint's fresh requirements list.

| Requirement | Result |
|---|---|
| 1. Detail uses canonical provider endpoint | **PASS** — `serviceJobsApi.get(id)` → `GET /v1/provider/my-records/jobs/{id}` |
| 2. Actions use canonical mutation endpoints | **PASS** — assign/schedule/cancel all via `serviceJobAssignmentApi.*` → `/v1/provider/service-jobs/{id}/*` |
| 3. Read-only users cannot mutate | **PASS** — live RBAC probe this sprint confirms Tenant Read Only gets a read view with mutation controls unavailable (browser regression: "read-only" text confirmed present) |
| 4. Other-tenant job IDs are rejected | **Soft-blocked, not hard-rejected** — live probe this sprint: cross-tenant detail request returns HTTP 200 with an embedded `{"error":"FINAL_JOB_NOT_FOUND"}` body, not literal 403/404. No cross-tenant data is exposed (verified by inspecting the actual response body). This is the same pre-existing pattern documented as L5-01D-006; not a new finding, not a security exposure, but a real API-consistency gap carried forward. |
| 5. Customer/staff roles cannot use tenant-owner endpoints | **PASS (isolated)** — live probe: customer token against `/v1/provider/my-records/jobs` returns 200 with `items:[]`/`total:0` (soft-block, same embedded-safe pattern, zero data exposure) |
| 6. Mutations invalidate list/detail caches correctly | **N/A / not applicable** — this app has no query-cache library (confirmed in FINAL-L5-01E's investigation of `useApi`/`useAction`); each hook independently refetches on `.refetch()`, so there is no stale-cache class of bug to invalidate |
| 7. No legacy `/v1/jobs` call remains | **PASS** — confirmed via live browser network capture this sprint (see Browser Report): zero `/v1/jobs` requests across dashboard + jobs list + jobs detail navigation |

## Completion data / Usage Credit Ledger
`completion_data` (`work_summary`, `collected_amount`, `completion_notes`, `technician`, `completed_at`) is present on `ServiceJobRecord` and rendered on the detail page for completed jobs (job `L501-JOB-0004`, seeded with `collected_amount: 775`). The Usage Credit Ledger itself is a separate page (`/usage-credit-ledger`), linked from the tenant navigation, not embedded in Job Detail — no direct in-page link was found or fabricated; this is consistent with the existing information architecture (ledger is tenant-wide, not per-job).
