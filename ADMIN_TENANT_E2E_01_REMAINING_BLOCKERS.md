# ADMIN_TENANT_E2E_01 — Remaining Blockers

No P0 blockers to foundation certification. The following are real, non-blocking gaps for future
page-by-page Admin/Tenant E2E sprints to pick up:

1. **No access_scope/RBAC enforcement on provider mutation endpoints** (e.g.
   `PUT /v1/provider/business-profile`). A `customer_support_limited` tenant user can currently mutate
   critical tenant fields. Needs a dedicated security/RBAC sprint. Not a blocker for THIS foundation
   sprint's scope (tooling + login + seed + smoke), but should be prioritized before any real read-only
   role is exposed to real users.
2. **No UI-level read-only mode** in tenant-portal — all `tenant_owner` users see an identical editable
   UI regardless of `access_scope`. Needs frontend work once the backend RBAC gap above is closed.
3. **Onboarding tour modal blocks first-load screenshots** in both admin and tenant apps — future E2E
   specs should add a `dismissTour(page)` helper (click "Skip tour" or set the relevant localStorage
   flag) before asserting on page content, to avoid every screenshot showing the tour overlay instead
   of real page data.
4. **Admin sidebar active-state does not track Home Services sub-routes.**
5. **`next lint` is non-functional** in both apps under Next.js 16.2.9 (pre-existing tooling gap, not
   introduced this sprint) — a future sprint should either downgrade/adjust the lint invocation or
   migrate to the Next 16-recommended ESLint flat-config CLI usage.
6. **Two legacy "wallet"-named pages** (`tenant-portal/app/(tenant)/wallet`,
   `super-admin/app/admin/provider-wallets`) still exist with wallet-style naming, adjacent to (but not
   exact matches of) the forbidden label list — candidates for a rename/audit in a future cleanup
   sprint.
7. Full backend pytest suite was not re-run in full this sprint (only the directly relevant
   `tests/test_auth_login_fix.py`, 16/16 passing) — a future sprint touching backend code should run the
   fuller suite.

None of the above block foundation certification: browser tooling works, both logins work in real
browsers against the real backend, seed data is genuinely bookable, and all in-scope routes smoke
clean.
