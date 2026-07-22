# Service-Layer Bypass Audit

## Scope and limitation, stated honestly
A comprehensive per-service caller graph (every service method × every router that calls it × every internal/worker/CLI path) across the entire backend was not completed this slice — that is a multi-day audit across ~140 router files and their corresponding service classes. What was done:

## Confirmed safe patterns (spot-checked, representative)
- **`update_permissions`** (`AuthService`): explicitly checks `if user.tenant_id != tenant_id: raise PERMISSION_DENIED` — cannot be used to grant/deny permissions across tenant boundaries even if called from a different, less-guarded router (the check is in the service method itself, not only the router dependency).
- **`invite_staff`**: creates the new user with `tenant_id=tenant_id` (the inviter's own tenant, passed explicitly from the router which reads it from `user.tenant_id` in the token) — a caller cannot pass an arbitrary tenant_id to invite into a different tenant, because the router signature only accepts an `InviteStaffRequest` body (email/name/phone/permissions), never a tenant_id field.
- **`_get_staff_permissions`**: filters `WHERE user_id = :user_id` only — since a `user_id` always belongs to exactly one `tenant_id` (enforced by the `User` model), no caller of this method could retrieve another tenant's permissions by supplying a different tenant_id, because the method doesn't accept one.

## Not audited this slice (deferred, honestly)
- Whether any of the ~140 other engine service classes have a mutation method reachable from more than one router with inconsistent guards.
- Whether any admin route can indirectly trigger a tenant-scoped mutation service method without the tenant-scoping check that the tenant-facing router would have applied.
- Bulk/export endpoints across the codebase for hidden mutation side effects.
- Background workers/CLI tools for whether they call tenant-scoped service methods with a caller-supplied (rather than derived) tenant_id.

## Why this wasn't expanded
This slice's core, proven deliverable (the effective-permission wiring fix) is real and load-bearing; attempting a full service-layer bypass audit on top of it within the same bounded pass risked either not finishing either well, or claiming a comprehensiveness this session's time budget could not support. Per this series' established discipline, this is reported as an honest gap rather than a rushed, low-confidence sign-off.

## Recommendation for a future slice
A systematic per-engine pass: for each of the ~16 tenant mutation router files (and the ~5 additional ones identified in `mutation-enforcement-matrix.csv` as not among the original 16, e.g. `auth/router.py`, `execution/home_service_router.py`), list every mutation endpoint's guard, then grep for the corresponding service method's other callers across the codebase. This is exactly the scale of work `tenant-mutation-route-inventory.csv` began and should be extended by.
