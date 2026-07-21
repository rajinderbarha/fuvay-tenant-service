# Role Entry and Navigation Verification — Round 2 (Workstream 6)

All verification this round was done at the API/authorization-boundary
level via direct curl calls with real JWTs (no Playwright/browser session —
see `playwright-baseline.md`). Real, non-fabricated results:

## Verified this round

- **super_admin** (`admin@serviceos.local`): real login, `GET
  /v1/admin/audit-logs` -> 200, `GET /v1/tenants` -> 200. See
  `super-admin-access-investigation.md`.
- **customer cannot access tenant/admin portals**: `GET
  /v1/admin/audit-logs` with the customer token -> real `403`. `GET
  /v1/provider/service-jobs/assignable` with the customer token -> real
  `500` (a real, backend-owned defect: this SHOULD be a `403`
  authorization rejection, not a `500` server error — the endpoint appears
  to attempt tenant-derivation logic that fails/throws for a customer whose
  `tenant_id` is `null`, rather than rejecting the role up front. Not
  frontend-owned, not fixed this round, logged in `known-limitations.md`
  and worth a backend ticket in a future round).
- **tenant_owner cannot access platform administration**: `GET
  /v1/admin/audit-logs` with the tenant_owner token -> real `403`.
- **technician cannot access platform administration**: `GET
  /v1/admin/audit-logs` with the technician token -> real `403` (correct).
- **technician + provider-scoped endpoint** (ambiguous finding, not a
  confirmed defect): `GET /v1/provider/service-jobs/assignable` with the
  SAME-TENANT technician's token -> real `200` (allowed). This may be
  legitimate (a technician viewing their own tenant's assignable-jobs list
  is not necessarily "tenant administration" — no mutation was attempted
  through this token, only a read). Recorded honestly as an open question,
  not asserted as either a pass or a defect, since testing only the mutating
  `assign` action itself (not attempted with this token this round) would
  be needed to make a confident authorization-boundary claim.

## Not verified this round (deferred)

- Session refresh, logout, expired-session behavior — none of these are
  observable via a single stateless JWT curl call; would require a real
  browser session (Playwright) to exercise refresh-token/cookie behavior.
  Deferred with `playwright-baseline.md`.
- Direct-URL forbidden-route behavior at the FRONTEND level (e.g. a
  customer navigating to `/admin/dashboard` in a browser and seeing a
  redirect/403 page) — only the backend API boundary was tested this round,
  not the frontend route-guard behavior. This is an important, real
  distinction: "hidden navigation is NOT the authorization boundary" (per
  the brief) — this round proved the backend boundary genuinely rejects
  unauthorized roles (with the one `500` exception above), which is the
  correct authority; whether each frontend app's route guards ALSO
  correctly redirect (defense in depth, UX correctness) was not verified.
- `admin_operations`/`admin_finance`/`admin_security`/`admin_readonly` —
  no seeded credential exists for these in `scripts/seed_demo_users.py`;
  still unverified, honestly disclosed (not the same blocker class as
  super_admin's Round-1 gap, since here the seed script itself confirms no
  such account was ever created for local dev).
- `admin_readonly` mutation-control absence — cannot be checked without a
  credential for that role.
- Tenant separation (a second tenant's `tenant_owner`/`technician` account)
  was NOT tested — only one demo tenant (`5209ef33-...`) has known seeded
  accounts; cross-tenant isolation was not exercised this round.
