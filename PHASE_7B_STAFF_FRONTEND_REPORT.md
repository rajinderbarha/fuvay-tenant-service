# Phase 7B — Technician Self-Service Frontend Build + Certification Sprint

## 1. Summary

Phase 7 ended `PARTIAL_READY_WITH_STAFF_APP_BLOCKERS` because no dedicated technician/staff
self-service frontend existed anywhere in the codebase, even though the backing `/v1/staff/*`
and `/v1/provider/*` APIs were already certified. Phase 7B builds that frontend inside
`frontend/tenant-portal` (the same Next.js app that already serves tenant-owners), gated by
role, using only already-certified Phase 7 backend endpoints — plus two small, necessary
backend fixes discovered via live smoke testing during this sprint (see Bug Fix Report).

## 2. What was built

13 pages under `frontend/tenant-portal/app/staff/*`, one shared layout
(`components/layout/StaffLayout.tsx`), one context-guard hook
(`hooks/useStaffContext.ts`), and one new API surface (`staffSelfApi` in `lib/api.ts`):

| # | Page | Route | Backend source |
|---|------|-------|-----------------|
| 1 | Staff Login | `/staff/login` | `POST /v1/auth/login` (role-checked client-side) |
| 2 | Context Guard | (cross-cutting, `StaffLayout`) | `GET /v1/auth/me` |
| 3 | Dashboard | `/staff/dashboard` | team-members, jobs, notifications, service-areas, provider status |
| 4 | My Profile | `/staff/profile` | `GET/PUT /v1/auth/me` (full_name only) |
| 5 | Skills & Assigned Services | `/staff/skills` | `GET /v1/provider/team-members` |
| 6 | Service Areas | `/staff/service-areas` | `GET /v1/tenant/service-areas` (read-only) |
| 7 | Availability | `/staff/availability` | `GET /v1/provider/availability` (read-only) |
| 8 | Documents | `/staff/documents` | none — honest "not yet available" state |
| 9 | Assigned Work (list) | `/staff/jobs` | `GET /v1/staff/me/jobs` |
| 10 | Job Detail (shell) | `/staff/jobs/[job_id]` | `GET /v1/staff/me/jobs/{id}` — no runtime actions |
| 11 | Notifications | `/staff/notifications` | `GET/POST /v1/staff/notifications*` |
| 12 | Security / Sessions | `/staff/security/sessions` | none — honest "not yet available" state |
| 13 | Activity | `/staff/activity` | none — honest "not yet available" state (see Bug Fix Report) |

## 3. Role isolation design

`useStaffContext()` never trusts `localStorage` alone — every page load re-verifies the
session against the live `GET /v1/auth/me` endpoint and only treats the user as staff if
`role === "technician" || role === "staff"`. `StaffLayout` hard-blocks (renders a
"staff/technician accounts only" screen with a link back to `/staff/login`) for any other
role or missing session, before rendering any page content or making any further API calls.

Tenant/data isolation is enforced backend-side (Phase 7's `FieldOpsService.list_jobs` fix —
`tenant_id`/`staff_id` are always overridden from the JWT regardless of query params) — the
frontend passes the client's own `tenant_id` for clarity but does not rely on it for security.

## 4. Forbidden runtime actions

The Job Detail shell explicitly lists the 7 forbidden actions (Start Job, On The Way, In
Progress, Complete Job, Collect Payment, Confirm Payment, Deduct Credits) as **disabled**
buttons labeled "Not certified in this phase" — present in the UI as documented placeholders,
never wired to any mutation call. Confirmed via the forbidden-label and runtime-action-exposure
scans (see those reports) and via `tests/test_phase7b_staff_frontend_certification.py`.

## 5. Honest gaps (not fabricated)

Three pages (Documents, Security/Sessions, Activity) show explicit "not yet available in this
app" empty states rather than fake data, because no backend endpoint exists for these features
yet. Details and reasoning in `PHASE_7B_STAFF_FRONTEND_REMAINING_BLOCKERS.md`.

## 6. Verification performed

- `npx tsc --noEmit` in `frontend/tenant-portal`: **0 errors**.
- `npm run build`: succeeds for all new `/staff/*` routes; one **pre-existing, unrelated**
  failure on `/service-jobs` (a `useSearchParams` Suspense-boundary issue inside
  `EnterpriseDataGrid.tsx`, confirmed untouched by this sprint and unrelated to any `/staff/*`
  page) — see Test Results report.
- `pytest tests/test_phase7b_staff_frontend_certification.py`: 18/18 passed.
- Full backend suite `pytest tests/`: see Test Results report.
- Live evidence-based smoke test against the real backend + real Postgres, using the real
  technician fixture `staff@serviceos.in` — see Manual Smoke Report.

## 7. Final recommendation

**READY_STAFF_TECHNICIAN_APP_FOUNDATION_FRONTEND_BACKEND_CERTIFIED**

(pending full-suite regression confirmation captured in the Test Results report — see that
document for the final passed/failed counts).
