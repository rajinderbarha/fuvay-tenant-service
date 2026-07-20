# Phase 2A Slice 2F-4 — Approval Gate

**5 previously security-closed modules unchanged except the one proven
direct bypass fix. `readonly@` untouched. Migration 144 not applied. No
visual redesign. Only one new module started. Stopping here for review.**

## Disposition: SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED

## Files changed
- `app/engines/tenant_engine/portal_router.py` — 10 guard swaps
  (`require_tenant_owner` → `require_tenant_owner_mutation`) + import + 5
  `AuthService` construction crash fixes.
- `app/engines/tenant_engine/admin_service.py` —
  `deactivate_staff` session-revocation fix (DB + Redis).
- **New:** `tests/test_phase2f4_tenant_portal_mutation_enforcement.py`
  (35 tests), this documentation directory (15 files).
- **Updated:** global Slice 2F `tenant-mutation-endpoint-inventory.csv`
  (10 rows) and `mutation-enforcement-matrix.csv` (module summary row +
  platform-wide TOTAL row, now 85/183).

## Remaining modules ranked
See `remaining-module-priority-matrix.csv` — `tenant_engine.portal_router`
ranked highest (9.5/10); `package_commerce.admin_router` and
`finance_hub.admin_router` flagged as needing persona re-verification for
a future slice (their `admin_router` naming may not mean platform-only).

## Selected module
`app.engines.tenant_engine.portal_router`.

## Selection rationale
Top-priority risk category (user/staff/session administration); zero
access-scope protection; and — discovered during investigation — 2 real,
severe bugs (a construction crash affecting 5 endpoints, and a missing
session-revocation gap on a directly-connected alternate route). See
`selected-module-scope-lock.md`.

## Mounted mutation count
10 (unchanged — no route added or removed).

## Final classification totals
10 `TENANT_OWNER_SELF_SERVICE`.

## Routes newly protected
10.

## Routes excluded, with reasons
None excluded (all 10 are applicable tenant mutations). The 2 GET
endpoints sharing the old role dependency were correctly left unguarded by
the access-scope check (reads don't need it).

## Remaining unverified routes
**0** — `--verify-module` exit 0.

## Personas supported
`tenant_owner` (self-service) and `super_admin` (platform override, exempt
from access-scope check). No staff delegation exists.

## Permission gaps
None in the RBAC-grant sense — role-based guard reused, no new permission
introduced.

## Ownership gaps found
2 real bugs (not classic "ownership gaps" but directly-connected security/
functional gaps): (1) `AuthService` construction crash affecting 5
endpoints; (2) missing session revocation on `AdminTenantService.deactivate_staff`
relative to the frontend-canonical `auth.router` alternate.

## Ownership gaps closed
Both of the above.

## Alternate bypasses found
1 real, exploitable (the `deactivate_staff` session-revocation gap versus
`auth.router`'s canonical implementation). 1 confirmed-safe
(`tenant_engine.admin_router`'s `require_super_admin`-gated parallel, not
a bypass).

## Alternate bypasses closed
1 (the real one).

## Service-layer bypasses found / closed
Same as above — the `AdminTenantService.deactivate_staff` gap is both an
alternate-route and service-layer finding; 1 found, 1 closed.

## Frontend exposure changes
None made. Audit revealed 7 of 10 endpoints have no confirmed frontend
caller and 3 do (lock/unlock/revoke-sessions) — no unsafe exposure
requiring a frontend change was found.

## Read-only direct-test results
10/10 endpoints directly HTTP-tested: 403 `PERMISSION_DENIED`, including
with an explicit `permission_overrides` grant.

## Authorized-persona results
10/10 directly HTTP-tested: authorized `tenant_owner` clears the auth
layer; the 3 previously-crashing endpoints (lock/unlock/revoke-sessions)
confirmed no longer return 500.

## Unauthorized-persona results
staff/technician/customer directly HTTP-tested on a representative
endpoint (all share the identical guard code path): 403.

## Cross-tenant results
Not independently re-exercised live this slice beyond source-inspection
regression tests confirming the pre-existing, unmodified tenant-filtering
mechanisms (`_load_tenant_user`/`_load_tenant_staff`/`_can_admin_manage_user`)
remain intact.

## Security-closure status
**SECURITY_CLOSED.**

## Product-policy-closure status
**BLOCKED** — 7 of 10 endpoints have no confirmed frontend caller and an
unresolved relationship to a parallel invitation-based mechanism (see
`product-decisions-required.md`).

## Tests run / passed / failed
This slice's family: 280/280/0. Wider targeted combined run: 594/594/0.
Broader partition: 226/226/0 (5 pre-existing skips). Combined: 1100/1100/0
real failures across all runs this slice touched.

## Broader regression coverage
226 tests across 8 files covering auth, session security, role editing,
cross-tenant IDOR, staff deactivation, and tenant onboarding — not claimed
as full-repository coverage.

## Runtime route count
Unchanged — no route added, removed, or modified this slice.

## Route collisions
0.

## Remaining blockers
The 3 product decisions in `product-decisions-required.md` — none block
security closure.

## Whether every quality gate passed
**Yes, all 31 gates.** Notably: gate 19 (connected weaker alternate routes
closed or block approval) — the real one found (session-revocation gap)
was closed, not merely documented. Gate 23 (already security-closed
modules remain unchanged unless a documented direct bypass requires the
smallest fix) — none of the 5 modules were touched; the bypass fixed this
slice was entirely within the newly-selected module and its own directly
connected `AdminTenantService`, not a change to any of the 5 closed
modules. Gate 31 (final status distinguishes security from product-policy
closure) — done explicitly above.

---
**Stopping here. Not starting a second new module. Not remediating
`readonly@`. Not applying migration 144. Awaiting approval before any
further slice.**
