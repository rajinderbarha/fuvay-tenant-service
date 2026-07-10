# Phase 7 — Remaining Blockers

## Primary blocker (deciding factor for this sprint's recommendation)

1. **No dedicated technician self-service frontend exists anywhere in the
   codebase.** Every one of this ticket's 17 in-scope modules has a real,
   working backend endpoint (after this sprint's 3 bug fixes), but there is
   no frontend page for a technician to log in and see their own
   dashboard, profile, skills, service areas, availability, documents,
   assigned jobs, notifications, sessions, or activity log. A technician
   who logs in today lands on tenant-owner-facing pages (the staff roster,
   the tenant dashboard) that don't branch for their role at all. This is
   a genuine, large feature-build gap — not a bug to patch, and building
   10+ new pages correctly (with real API wiring, loading/empty/error
   states, and compliant copy) is out of this sprint's time budget. Given
   this ticket's own explicit rule ("Do not certify backend only"), this
   is the reason the final recommendation cannot be an unqualified READY.

## Secondary, non-blocking gaps

2. **No self-service session/device-management endpoint** for staff (only
   tenant-owner-managed staff lock/unlock/revoke-sessions exists).
3. **No staff-specific document upload/verification-status endpoint**
   exists (the only document router found is a generic e-signature
   engine, unrelated to staff onboarding documents).
4. **AC Repair skill was seeded but the tenant's corresponding enabled
   service is still empty** (a Phase-6-era gap, not introduced or
   responsible-to-fix in Phase 7).
5. **No staff-to-service-area assignment exists yet** (`service_area_ids`
   is empty on the seeded team-member row) — the tenant has Ludhiana
   141001 configured, but nothing links it to this specific technician.
6. **Two unrelated files** (`package_commerce/public_router.py`,
   `location_engine/router.py`) still carry the `request_id`-placeholder
   pattern from earlier sprints — neither is staff-facing, left as a
   carried-forward note.
7. **The `technician` role's permission set includes `FIELD_OPS_JOBS_CLOSE`
   and `FIELD_OPS_QUOTES_MANAGE`**, which exceed a strict foundation-only
   reading — pre-existing, unchanged configuration, and nothing in this
   phase's actual surface exposes an action that would exercise them.

## What is genuinely solid

The backend foundation itself — auth, JWT-scoped context, tenant/staff
isolation (after the fix), job-list shell, job-detail shell, skills
(after the fix), notifications, permission boundaries (no admin/finance/
package mutation ability) — is real, live-verified, and correctly
prevents every hard-gate violation this ticket names (cross-tenant access,
self-role-change, self-verification, cash/wallet mislabeling, runtime-
action exposure). The blocker is purely about frontend existence, not
backend correctness or security.
