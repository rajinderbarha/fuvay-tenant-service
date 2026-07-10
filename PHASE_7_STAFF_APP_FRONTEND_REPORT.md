# Phase 7 — Staff/Technician App Frontend Report

## CRITICAL FINDING: No dedicated technician self-service frontend exists

A thorough search of `frontend/tenant-portal/app/` (the only frontend app
that could plausibly serve this role — confirmed in Phase 6 to be shared
by tenant-owners AND staff/technicians via role-gating, not two separate
apps) found:

- `app/(tenant)/staff/page.tsx` + `[id]/page.tsx` — the **tenant owner's**
  staff roster/detail management pages (calls `staffApi.list()` etc.),
  used to manage staff, not a technician's own view of themselves.
- `app/(tenant)/dashboard/page.tsx` — confirmed via source read to be
  entirely tenant/owner-facing: it calls `staffApi.list()`,
  `financeApi.wallet()` (tenant-level finance), `bookingsApi.list()`, and
  routes to category-specific dashboards (`HomeServiceDashboard`,
  `CoachingDashboard`, etc.) with **zero role branching for
  `technician`**.
- No `app/(tenant)/my-*` or `app/(tenant)/technician/*` route group exists.
- No frontend page anywhere calls `/v1/staff/me/jobs`, `/v1/staff/
  notifications`, `/v1/provider/team-members` (technician's own skills
  view), or `/v1/provider/availability` from a technician's own
  self-service perspective.

**In short: every one of this ticket's 17 in-scope modules has a real,
working backend endpoint (after this sprint's 3 bug fixes) — but there is
no frontend UI for a technician to actually use any of them.** A
technician who logs in today lands on tenant-owner-facing pages (staff
roster, tenant dashboard) that either don't apply to their role or would
show them tenant-management data inappropriate for their role, since none
of these pages check `role === "technician"` and branch to a different,
technician-appropriate view.

## Why this was not built this sprint

Building 10+ new frontend pages (technician dashboard, my profile, skills
view, service-area view, availability editor, documents upload, job list,
job detail, notifications, sessions, activity log) each with real API
wiring, loading/empty/error states, and forbidden-label-safe copy is a
substantial, multi-page feature-build project — not a "fix the bug" task
within this sprint's time budget, and rushing it risks producing exactly
the kind of unverified, potentially-broken code this session has
consistently avoided. This is reported honestly as a **real, unmet
requirement**, not glossed over or fabricated.

## TypeScript

**0 errors** on `frontend/tenant-portal` (confirmed — no frontend files
were changed this sprint, since the fixes needed were entirely backend-side
bugs affecting endpoints that have no frontend consumer yet).

## Forbidden label scan (backend, since no new frontend exists to scan)

Zero forbidden-term matches in any staff-facing backend router.

## Result: **Backend-only certified. Frontend for the technician self-service experience does not exist and is the primary reason this sprint cannot claim unqualified READY.**
