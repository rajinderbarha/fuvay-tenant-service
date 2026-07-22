# Phase 2A Slice 2F-2 — Provider Portal Mutation Enforcement — Implementation Summary

## Mission
Close access-scope-aware mutation enforcement for
`app.engines.provider_portal.router` (24 mounted mutation endpoints, the
next module per Slice 2F's own priority order), following the exact
pattern established for `tenant_engine.router` in Slices 2F-1/2F-1A, and
close any directly-connected bypasses found along the way.

## What changed

### 1. New composed guard: `require_tenant_owner_mutation`
`app/core/permissions.py`. Unlike `tenant_engine.router` (permission-gated
via `require_permission(P.X)`), every mutation endpoint in
`provider_portal.router` was gated by the plain ROLE dependency
`require_tenant_owner` (role in `{tenant_owner, super_admin}`), with no
access-scope check at all. `require_tenant_owner_mutation` wraps
`require_tenant_owner` and additionally rejects (403) any caller whose
`access_scope` is in `TENANT_READONLY_ACCESS_SCOPES`, exempting
`super_admin` — the role-gated analogue of `require_tenant_mutation_permission`,
reusing the same `TENANT_READONLY_ACCESS_SCOPES` set and the same
denial-response shape, per the brief's "do not create a parallel
authorization framework" instruction.

### 2. Guard swap (22 endpoints)
`app/engines/provider_portal/router.py`: swapped
`Depends(require_tenant_owner)` → `Depends(require_tenant_owner_mutation)`
on all 22 role-gated mutation endpoints (confirmed via source inspection
that every one of the 22 occurrences was attached to a POST/PUT/DELETE
mutation handler, never a GET). The remaining 2 of the 24 live mutation
routes were correctly left untouched:
- `set_area_coverage` — already `require_tenant_mutation_permission`-gated
  from prior work, unrelated to this slice.
- `preview_matching_inputs` — a `FALSE_POSITIVE` (POST verb used only
  because it accepts a body; calls a read-only lookup function, performs no
  write; confirmed by reading the handler source).

### 3. Three real, directly-connected bugs found and fixed
- **Cross-tenant read-back data leak** (5 handler groups, 8 SELECT
  statements): `update_team_member`, `activate_team_member`,
  `deactivate_team_member`, `update_availability`, and 4 offering-mutation
  handlers each correctly scoped their `UPDATE`/`DELETE` by
  `tenant_id=:tid`, but the immediately-following read-back `SELECT` used
  only `WHERE id=:id`, with no tenant filter — a cross-tenant record ID
  would safely no-op the mutation but then leak that other tenant's row's
  data back in the response. **Fixed**: every read-back now filters by
  `tenant_id=:tid` and returns 404 if not found in the caller's own tenant.
- **Missing session revocation on team-member deactivation**:
  `provider_team_members.user_id` is a nullable link to a real `users`
  login row; `deactivate_team_member` never revoked that user's sessions.
  **Fixed**: mirrors the proven `AuthService.deactivate_staff` /
  `tenant_engine.deactivate_staff` pattern exactly — DB `revoked_at` +
  Redis `serviceos:session:revoked:{id}` flag for every active session,
  fail-open on Redis errors (consistent with the existing convention).

### 4. Mutation inventory tooling extended
`scripts/workflow_rearchitecture/inventory_mutation_routes.py`:
`guard_status()` now recognizes `require_tenant_owner_mutation` (a plain,
non-factory function, so its literal name is the dependency name) as
`TENANT_MUTATION_ROLE_SCOPE_AWARE`, added to `ACCEPTED_GUARD_STATUSES`. Also
added a small `CONFIRMED_FALSE_POSITIVE_ROUTES` allowlist (currently one
entry: `preview_matching_inputs`) so `--verify-module` can correctly report
0 unverified routes for a module containing one deliberately-non-mutating
POST endpoint, without weakening the check for genuine gaps elsewhere.

## Workstream findings (condensed — full detail in dedicated docs)
- **Team/membership security**: no staff delegation exists (role-gate
  excludes staff/technician entirely); no RBAC-escalation surface in the
  updatable fields; `create_member_login` is an unimplemented stub. See
  `team-membership-security.md`.
- **Availability ownership**: no per-technician self-service exists — all
  availability configuration is tenant-wide, owner-only. See
  `availability-ownership-decision.md`.
- **Offerings ownership**: tenant-wide, owner-only, `CANONICAL_HERE` (no
  duplicate route in admin_catalog/service_setup). See
  `offerings-ownership-decision.md`.
- **Alternate routes**: `tenant_engine.portal_router`'s `/staff/*` operates
  on a different table (`users`, not `provider_team_members`) — not a
  duplicate, `DISCONNECTED`. See `provider-portal-alternate-routes.md`.
- **Service-layer audit**: no separate service class exists for this
  module — the router IS the service layer; no other code path writes to
  any of its 7 owned tables. See `provider-portal-service-bypass-report.md`.

## Closure status
**SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED**, matching `tenant_engine.router`'s
precedent disposition:
- **SECURITY_CLOSED: yes.** All 22 tenant-reachable mutations are now
  access-scope protected; role and tenant-scoping checks remain enforced;
  the 3 directly-connected bypasses found are closed; no weaker alternate
  route exists.
- **PRODUCT_POLICY_CLOSED: no.** 4 open product decisions remain (see
  `product-decisions-required.md`) — none block security closure, all
  honestly documented rather than silently ignored.

## Files changed
- **Modified:** `app/core/permissions.py` (new
  `require_tenant_owner_mutation`), `app/engines/provider_portal/router.py`
  (22 guard swaps + import cleanup + 3 bypass fixes),
  `scripts/workflow_rearchitecture/inventory_mutation_routes.py`
  (guard_status extension + false-positive allowlist).
- **New:** `tests/test_phase2f2_provider_portal_mutation_enforcement.py`
  (53 tests), this documentation directory (16 files),
  `docs/workflow-rearchitecture/phase-02a-slice-02f/` CSVs updated (see
  approval-gate.md for exact diffs).

## Test results
483 targeted + 269 broader-partition = 752 tests, 0 failures.
