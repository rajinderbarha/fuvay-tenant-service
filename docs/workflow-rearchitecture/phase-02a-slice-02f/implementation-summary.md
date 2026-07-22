# Phase 2A Slice 2F — Implementation Summary

## Outcome in one sentence
This slice replaced Slice 2E's router-file-level estimate with an exhaustive, live, endpoint-level mutation inventory (built via a new runtime-introspection script), which **confirmed and sharpened** the mutation-guard gap rather than closing it — closing it (185 tenant-facing mutation endpoints, only 10 fully protected) is genuinely beyond a single bounded slice's safe scope; this slice instead delivered the one real, safely-scoped fix within reach: closing the session-revocation gap for permission reductions. Per this slice's own quality gate 23 ("remaining UNVERIFIED mutation routes are zero, or the slice must report failure rather than completion"), this slice **honestly reports incompletion** of the full mutation-enforcement mission, with precise, real numbers, rather than a false claim of closure.

## Workstream 1 — Runtime mutation inventory (real, exhaustive, live)
Built `scripts/workflow_rearchitecture/inventory_mutation_routes.py`, which walks the live FastAPI app (same `_IncludedRouter` recursion as the Phase 1A `list_routes.py` tool) and, for every `POST`/`PUT`/`PATCH`/`DELETE` route, captures method, path, endpoint function name/module, and the FastAPI dependency-chain function names (`route.dependant` walk) — giving real, per-endpoint guard visibility without needing to hand-read hundreds of files.

**Results (live, not estimated):**
- **1,188 total mutation-method routes** across the entire backend.
- **185 tenant-facing** (`/v1/provider/*`, `/v1/tenant/*`, `/v1/tenants/*` = 134; `/v1/staff/*` = 51).
- Of those 185: **10 fully protected** (`require_tenant_mutation_permission`, all in `admin_catalog/tenant_router.py`, matching Slice 2E's finding exactly), **59 role-only guarded** (`require_tenant_owner`/`require_technician`/`require_super_admin` — no permission or access-scope check), **33 permission-only guarded** (a specific `require_*` permission dependency, but not access-scope-aware), and **83 show no role/permission dependency at all beyond `get_current_user`** (bare authentication only, at the route-dependency level — a materially more serious and precisely-quantified finding than Slice 2E's estimate, though whether any of these 83 have an equivalent check inside the handler body was not individually verified — see `known-limitations.md`).

Full per-endpoint data in `tenant-mutation-endpoint-inventory.csv`.

## Workstreams 4-8 — Guard application, technician exceptions, bypass audits: NOT attempted at scale this slice
Applying `require_tenant_mutation_permission` (or an equivalent) to 175 endpoints safely requires, per-endpoint, distinguishing genuine tenant-owner-only operations from staff-delegable ones from technician-operational ones from customer/platform-adjacent ones sharing a router — a large, high-risk, multi-file change this slice's bounded scope did not attempt, consistent with the discipline established across this entire series (every prior slice declined comparably large speculative rearchitecture). Attempting it hastily risks violating rules 8/9 ("do not break verified technician operational actions"/"do not break tenant-owner operations").

## Workstream 9 — Permission-reduction session revocation (the real fix this slice delivers)
`app/engines/auth/service.py::update_permissions` now:
1. Detects a "reduction" — any permission ending up `is_granted=False` as a result of the call (grant→deny transition OR a brand-new explicit deny).
2. If any reduction occurred, revokes every active `user_sessions` row for the target user (DB `revoked_at`) **and**, critically, writes the Redis `serviceos:session:revoked:{session_id}` flag `get_current_user` actually checks at request time — closing the exact gap Slice 2D found in the pre-existing `deactivate_staff` method (which only did the DB half, never the Redis half, and still does not — see `known-limitations.md`).
3. Records `reduced_permission_keys` and `sessions_revoked` in the existing `staff.permissions_updated` audit event.
4. Leaves pure grants untouched (no unnecessary revocation), per the brief's explicit instruction.

Proven via 4 new tests (`tests/test_phase2f_mutation_enforcement.py::TestPermissionReductionSessionRevocation`), plus the full 365-test combined regression suite (up from 287) confirming no regression in this security-critical, widely-shared code path.

## Workstream 10/11/12 — Read-only test matrix, read-path regression, remediation readiness
Not built at the comprehensive scale requested (would require the guard-application work above to exist first — testing denial against endpoints that aren't yet guarded would either fail or test nothing meaningful). Remediation readiness: **NOT_READY_MUTATION_GAPS** — see `remediation-readiness-decision.md`.

## Non-negotiable rules compliance
No `tenant_readonly`/`tenant_manager` created. `admin_readonly` never used for tenant access. `readonly@` was not modified (confirmed: role distribution identical before/after this slice). Migration 144 was not applied (confirmed: still at revision 143, unattempted this slice since no new resolution occurred). Booking/job pipelines and UI untouched. Combined regression suite: **365/365 passing** (6 new Slice 2F tests + 359 carried forward from prior slices and adjacent auth suites).
