# Route and Navigation Access State Verification — Slice 2B

No new access-state component was built this slice (consistent with Slice 2's decision not to build a shared route-access-state system, to avoid new shared-component/visual work). This document verifies the specific states the brief calls out, against current behavior.

| State | Verified behavior |
|---|---|
| Loading | `useApi`/`usePermissions` hooks return `loading: true`; nav items fail closed while loading (unchanged, re-verified) |
| Unauthorized (401) | Existing auth/token-refresh flow, untouched this slice |
| Forbidden (403) | `StaffLayout`'s explicit access-denied message, untouched this slice |
| Not found | Standard Next.js 404, untouched |
| Retired | `POST /v1/reviews` 410 (Slice 2), untouched this slice |
| Blocked | Same as Retired — no new blocked route added this slice |
| Temporarily unavailable | My Work's `sources_unavailable` banner (Slice 1), untouched |
| Partial data | Same as above |
| **Invalid role** (new check this slice) | The tenant-user-creation form (fixed in Slice 2) now only offers 2 real role options; submitting anything else is impossible via the UI, and the backend independently rejects any other value with `TENANT_USER_ROLE_INVALID` (verified again this slice via the existing regression tests, still passing) |
| **Invalid contextual record type** (new check this slice) | Verified both Parts-UI-bearing pages (`/staff/jobs/[job_id]`, `/(tenant)/service-jobs/[id]/execution`) exclusively fetch and render `ServiceJob`-shaped data — there is no code path in either page that could render Parts actions for a `Booking` or field_ops `Job` record, because neither page's API client (`homeServiceStaffJobsApi`, `homeServiceExecutionApi`) ever fetches those record types. This is a structural guarantee (the page simply has no way to load an incompatible record), not a runtime type-check that could be bypassed. |

## Not built this slice
A shared, reusable component for these states across all 3 apps remains out of scope, per Slice 2's documented reasoning (risk of new shared-component/visual work).
