# HS2 — Permission Report

## Ticket's 5 example permissions
`admin.home_services.catalog.read/create/update/delete/audit.read` — none
of these fine-grained constants were found in `app/core/permissions.py`
during this sprint's inspection, and the catalog console page does not
gate any action behind a permission check (all buttons/tabs render
unconditionally for any authenticated admin).

## Consistent with the established session-wide gap
This mirrors the exact same gap documented in the prior A3 sprint (Admin
Tenant Management) this session: the real, frontend-facing admin surface
uses coarse `require_super_admin` gating on the backend, with no
fine-grained permission constants reaching the frontend to condition UI
on. Not fixed this sprint — consistent with that prior finding, low risk
today since the test admin account has the `super_admin`/`P.ALL`
wildcard role, but architecturally incomplete.

## What would be needed
1. Add `admin.home_services.catalog.*` (or reuse existing
   `P.CATALOG_HOME_SERVICES_*`-style constants if they already exist —
   not confirmed this sprint) to `permissions.py`.
2. Gate the backend `home_services_catalog_console_router.py` mutation
   endpoints with `require_permission(...)` instead of (or in addition
   to) whatever it currently uses (not verified this sprint).
3. Surface the current user's permission set to the frontend and
   conditionally hide "Add Service"/edit toggles/Activity tab.

## Verdict
Permission-aware UI: **not implemented**. Documented as a remaining
blocker, matching the same class of gap already known from the A3
sprint.
