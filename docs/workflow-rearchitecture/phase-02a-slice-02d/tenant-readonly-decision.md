# Tenant Read-Only Decision

## Decision: EXISTING_ARCHITECTURE_CANNOT_ENFORCE_READ_ONLY (comprehensively, today)

## Evidence

The codebase has exactly one real mechanism shaped for this need: `access_scope="customer_support_limited"` checked by `require_tenant_mutation_permission()` (`app/core/permissions.py`), which:
- Runs the normal role/permission check first, then
- Additionally denies (403) any tenant-side user whose `access_scope` marks them read-only, **before** any request-body/business-rule validation runs
- Exempts only `super_admin`

This is a well-designed mechanism — checked at the right layer, fails closed, doesn't leak business-validation errors to a blocked caller. The problem is coverage: **`grep -rl "require_tenant_mutation_permission" app/engines/` returns exactly 2 files**, out of ~16 tenant-facing `tenant_router.py`/`provider_router.py` files across all engines (confirmed by a second `find` count). Every tenant mutation route in the other ~14 files uses plain `require_permission` (or an even coarser role check), which does **not** consult `access_scope` at all.

## What this means concretely
A user with `role=staff` (or any role) and `access_scope=customer_support_limited` would be correctly blocked from mutating on the 2 covered engines, but could still successfully call `POST`/`PUT`/`PATCH` on any of the other ~14 tenant engines' mutation endpoints, as long as their role's `ROLE_PERMISSIONS` bundle includes the relevant permission — because those routes never check `access_scope` at all. This is not a hypothetical edge case; it is the default behavior for the large majority of tenant mutation surfaces in this codebase today.

## Per-requirement check against the brief's read-only definition

| Requirement | Can existing architecture guarantee this today? |
|---|---|
| View only authorized tenant data | Yes — `TenantScopeService` enforces this regardless of mutation concerns |
| Never create/update/approve/delete records | **No** — only guaranteed on the 2 covered engines |
| Never assign jobs | Not specifically checked; would depend on which engine assign-job lives in |
| Never modify pricing/services/finance | Not guaranteed unless those specific engines are among the 2 covered ones (not verified whether they are) |
| Never manage users/change settings | Not guaranteed platform-wide |
| Never perform hidden mutations through direct API access | **This is exactly the failure mode** — a "read-only" persona today could bypass the intended restriction via any of the ~14 uncovered engines, through direct API calls, with zero frontend involvement (frontend hiding a mutate button is irrelevant if the backend route itself doesn't check `access_scope`) |

## Why not the other dispositions
- **`REPRESENT_AS_STAFF_READ_ONLY_PERMISSIONS`**: would require a permission bundle containing zero mutation permissions — but `ROLE_PERMISSIONS` is a single flat list per role name (`staff`), not user-overridable in practice (see `tenant-access-model.md`'s override-wiring finding) — so there is no way to give one specific staff user a strictly-smaller permission set than another staff user today.
- **`REPRESENT_AS_EXISTING_PERMISSION_TEMPLATE`**: no template mechanism exists (confirmed in `manager-persona-decision.md`).
- **`NEW_CANONICAL_ROLE_REQUIRED`**: explicitly forbidden by this slice's non-negotiable rules without an approved architecture decision — and more importantly, a new *role* wouldn't fix the coverage gap anyway, since the gap is in mutation-route enforcement consistency, not in role granularity.
- **`NEW_PERMISSION_MODEL_REQUIRED`**: closer to correct in spirit, but the "model" (access_scope + require_tenant_mutation_permission) already exists — what's missing is applying it consistently, which is an enforcement-coverage task, not a new model design task.
- **`PRODUCT_DECISION_REQUIRED`**: the requirement itself (genuine read-only access) is not ambiguous — what's missing is engineering completion, similar to the manager persona's gap.

## Required to close this gap (future slice, not this one)
Extend `require_tenant_mutation_permission` (or an equivalent guard) to all ~14 remaining tenant mutation routers. This is a real, bounded, but nontrivial engineering task — each router must be individually reviewed to confirm which endpoints are genuinely mutations (not all `POST`s are, e.g. search/preview endpoints) and swapped from `require_permission` to `require_tenant_mutation_permission` without breaking legitimate owner/staff mutation flows. Out of this slice's scope given its size (14+ files, cross-cutting, needs careful per-file review).

## Application to readonly@demo-ac-services.local specifically
This account cannot be safely remediated to any canonical role today without either granting it real mutation capability (violating "read only") or leaving it in an invalid state. See `affected-account-final-disposition.md`.
