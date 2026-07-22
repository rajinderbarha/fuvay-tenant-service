# Selected Module Scope Lock — Slice 2F-4

## Selected module
`app.engines.tenant_engine.portal_router`

## Why selected
Ranks highest on real security/product risk among all remaining unclosed
tenant-facing modules:
- **User/staff/session administration** — the top-priority category per
  the mission's explicit ranking ("Authentication, tenant-user, invitation,
  role and permission mutations"). This module owns account creation
  (`create_user`, `create_staff`), account suspension/deactivation
  (`suspend_user`, `deactivate_staff`), account lock/unlock
  (`lock_staff`/`unlock_staff`), and forced session revocation
  (`revoke_staff_sessions`) — the most security-sensitive capability class
  in the entire remaining-module list.
- **Zero access-scope protection today** — all 10 mutation endpoints were
  gated by the plain `require_tenant_owner` ROLE dependency only (role in
  `{tenant_owner, super_admin}`), with no `access_scope` check at all —
  identical to the exact gap already found and fixed twice
  (`provider_portal.router` in Slice 2F-2, `execution`/`home_service_assignment`
  in Slice 2F-3B). A read-only-scoped support agent impersonating
  `tenant_owner` could previously lock/unlock/deactivate/suspend accounts
  and force-revoke sessions.
- **A genuine, severe functional bug discovered during investigation**:
  `lock_staff`, `unlock_staff`, `revoke_staff_sessions` (and the 2 read-only
  security-status endpoints) all constructed `AuthService(..., actor_id=...)`
  — a keyword argument `AuthService.__init__` has never accepted. These
  endpoints crash with a 500 on every real call today, regardless of
  authorization. This alone would justify selecting this module even before
  weighing the access-scope gap.
- Wallet visibility (`GET /wallet`, `/wallet/ledger`) places this module in
  the finance-adjacent risk category too (priority 2), though those two
  endpoints are reads, not mutations, and out of this slice's mutation
  scope.

## Runtime mutation count
10 (confirmed via live `inventory_mutation_routes.py --module`).

## Highest-risk endpoints
1. `POST /v1/tenant/staff/{user_id}/lock` — locks a staff account.
2. `POST /v1/tenant/staff/{user_id}/unlock` — unlocks a staff account.
3. `POST /v1/tenant/staff/{user_id}/sessions/revoke-all` — force-revokes
   all of a staff member's sessions.
4. `POST /v1/tenant/staff/{staff_id}/deactivate` — deactivates staff.
5. `POST /v1/tenant/users/{user_id}/suspend` — suspends a tenant user.

## Known alternate routes
`app.engines.tenant_engine.admin_router` exposes the same capabilities
(`create_user`, `suspend_user`, `create_staff`, `deactivate_staff`) via the
same `AdminTenantService`, but gated by `require_super_admin` — a stronger,
platform-only route, confirmed not a bypass (same trust-level pattern as
`provider_portal.router`'s and `tenant_engine.router`'s own admin_router
precedents from prior slices).

## Expected personas
`tenant_owner` (self-service) and `super_admin` (platform override, exempt
from the access-scope check) — no staff delegation exists (the underlying
`require_tenant_owner` role check excludes `staff`/`technician`).

## Expected permissions
None granted today — this module is role-gated, not permission-gated,
matching `provider_portal.router`'s pattern. No new permission is
introduced this slice.

## Expected access-scope behavior
Read-only-scoped `tenant_owner` must be blocked from all 10 mutations, even
with an explicit permission override — enforced via the existing
`require_tenant_owner_mutation` composed dependency (built in Slice 2F-2,
reused here without modification).

## Explicitly excluded modules
Every other module in `remaining-module-priority-matrix.csv` — none were
modified this slice. In particular, `package_commerce.admin_router` and
`finance_hub.admin_router` were flagged as needing their OWN persona
re-verification (their `admin_router` naming may not mean platform-only,
per the mission's explicit warning) but were NOT investigated further or
modified — reserved for a future slice.

## Scope lock
This module is not ambiguous — the persona (`tenant_owner`/`super_admin`),
the guard composition (`require_tenant_owner_mutation`, already built and
proven), and the ownership mechanisms (already correct in
`AdminTenantService`/`AuthService`) were all confirmed via direct source
reading before any code was changed. No blocker was found; implementation
proceeded in this same slice.
