# Phase 2A Slice 2E — Implementation Summary

## Outcome in one sentence
The core effective-permission wiring gap identified in Slices 2C/2D was closed with a single, precisely-targeted, fully-tested fix — but the read-only persona and `readonly@demo-ac-services.local`'s remediation remain correctly BLOCKED, because the fix unblocks the *manager* persona (permission grants) but does not by itself close the separate, larger *mutation-guard coverage* gap (only 1 of 16 tenant routers enforces the read-only mutation guard) that the read-only persona actually depends on.

## Workstream 1/2 — Effective-permission architecture (the central fix)
Re-investigated the full auth chain and found Slice 2D's conclusion was **partially incorrect**: `app/engines/auth/service.py`'s `_build_token_pair` (login) and its token-refresh counterpart already load real `StaffPermission` rows into the JWT's `permission_overrides` claim — that half of the pipeline was already built and working. The actual, narrower gap: `app/dependencies/auth.py::get_current_user` never read `payload.get("permission_overrides")` back out when reconstructing `UserContext`. **Fixed with one added line.** Verified via:
- A full round-trip test (`tests/test_phase2e_effective_permissions.py::TestFullRoundTripPermissionOverrides`) proving a JWT-carried override now actually changes `PermissionChecker.has()`'s outcome, both for grants beyond the base role bundle and denies overriding a role-granted permission.
- The full 287-test combined regression suite still passes (up from 278) — this touches the most central, most-used code path in the entire backend, so this was the highest-risk change this slice made, and it was proven safe.

Precedence (Workstream 1's explicit questions) was already correctly implemented in `PermissionChecker.has()` before this slice — deny wins over role-grant, overrides can expand beyond the base role bundle, unknown permission strings are structurally inert (since `permission` is always a hardcoded `P.*` constant from route code, never derived from override-dict keys). No precedence logic needed to be invented; it needed to be *reached*.

## Workstream 4 — Mutation route inventory (router-file granularity)
Surveyed all 16 tenant-facing router files (`tenant_router.py`/`provider_router.py` across engines) for mutation-guard patterns. **Confirmed finding, unchanged from Slice 2D's estimate but now precisely verified**: exactly 1 file (`admin_catalog/tenant_router.py`) uses `require_tenant_mutation_permission` (10 of its 10 mutation endpoints covered); the other 15 files use a mix of `require_permission`, role-only guards, or patterns not resolved to a clear mutation dependency in this pass. Full detail in `tenant-mutation-route-inventory.csv` and `mutation-enforcement-matrix.csv`.

## Workstreams 5/6/8/10 — Mutation enforcement expansion, read-only persona, account remediation: NOT completed this slice
Extending mutation-guard coverage from 1 to 16 router files requires individual per-endpoint review (distinguishing true mutations from read/preview/export endpoints per file) — a large, cross-cutting change this slice's bounded scope did not attempt, consistent with the discipline established across this entire series (Slice 2, 2B, 2D all similarly declined large speculative rearchitecture). Because comprehensive read-only enforcement cannot be proven, per the non-negotiable rule ("do not map the remaining account to staff until direct API mutation denial is proven"), `readonly@demo-ac-services.local` **remains unremediated** — this is the correct, rule-compliant outcome, not an omission.

## Workstream 7/11 — Manager persona: proven working, no new account created
Confirmed (not built new) that `invite_staff` and `update_permissions` (pre-existing `AuthService` methods) already implement the complete manager-permission-grant pipeline correctly, including tenant-ownership verification. With this slice's fix, permissions granted through them now take effect. No new manager permission template was introduced (per the rule against hidden role aliases) — a manager is simply `role=staff` plus an explicit, tenant-scoped set of `StaffPermission` grants chosen per real business need. The disabled `manager@demo-ac-services.local` demo account was **not reactivated** — the demo environment does not require it, and reactivating a historical account to merely demonstrate a now-working mechanism would risk conflating "proof the mechanism works" (done via tests) with "this specific account is a real manager" (unproven, same as Slice 2D's conclusion).

## Workstream 12 — Migration 144
Still correctly blocked — `readonly@` remains the one invalid-role account. Not applied.

## Workstream 13 — Authorization integrity check extended
`scripts/workflow_rearchitecture/check_role_integrity.py` extended with 4 additional checks: unknown `staff_permissions.permission_key` values, cross-tenant `staff_permissions` rows, orphaned permission rows, invalid `access_scope` values. All confirmed zero violations except the known 1 invalid role. Verified live.

## Non-negotiable rules compliance
No `tenant_manager`/`tenant_readonly` created. `admin_readonly` never used for a tenant account. No convenience grants of `tenant_owner`/`super_admin`/platform-admin. `readonly@` was not mapped to `staff` because direct API mutation denial is not proven (rule 5, honored exactly). No frontend-only security boundary was introduced (no frontend changes made this slice at all). Deny-fails-closed already true in `PermissionChecker.has()`, now actually reachable. Tenant isolation preserved (`update_permissions` already checks `user.tenant_id != tenant_id`). Booking/job pipelines and UI untouched. All prior regression tests pass (287/287 total).
