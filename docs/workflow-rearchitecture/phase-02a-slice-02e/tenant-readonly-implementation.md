# Tenant Read-Only Implementation

## Status: BLOCKED, per the explicit non-negotiable rule and Workstream 8's own stop condition

> "If the current model cannot enforce this after the approved integration, stop and report the exact blocker rather than remediating the account."

## What changed this slice, and why it's not enough
Fixing the effective-permission wiring (this slice's core deliverable) makes the *grant/deny* mechanism reachable — meaning a `staff` user could theoretically have every mutation permission explicitly denied via `StaffPermission` rows, and `PermissionChecker.has()` would correctly return `False` for each one. **But this only protects routes that actually call `require_permission(some_specific_permission)` or `require_tenant_mutation_permission(...)`.** Per `tenant-mutation-route-inventory.csv`, only 1 of 16 tenant-facing router files uses the access_scope-aware mutation guard, and several others appear to use role-only guards (`require_staff_or_above` etc.) that never consult `permission_overrides` or `access_scope` at all — a role-only guard cannot be denied via a permission override, because it never checks any permission in the first place.

## Concretely, what this means
A `staff` user with every known mutation permission explicitly denied would still successfully call any endpoint gated only by `require_staff_or_above` (role check only) — because that dependency never looks at `permission_overrides`. Confirmed by reading `require_staff_or_above`'s implementation pattern (role-string equality check only, no permission consultation) against the router survey's finding that several tenant router files use exactly this class of guard.

## The exact blocker (per the brief's request to "report the exact blocker")
**Read-only enforcement requires every tenant mutation endpoint to be gated by a permission (or the access_scope-aware guard), not by role alone.** Today, 15 of 16 tenant-facing router files either don't use `require_tenant_mutation_permission` or use role-only guards not proven to consult permissions at all. Closing this requires a per-file, per-endpoint review — correctly distinguishing genuine mutations from reads/previews/exports — across those 15 files. This is the same gap identified in Slice 2D, now confirmed with router-file-level precision rather than an estimate.

## Decision
`EXISTING_ARCHITECTURE_CANNOT_ENFORCE_READ_ONLY` — unchanged from Slice 2D's conclusion, now with stronger evidence (a named, countable list of the 15 uncovered files, not just "~14, approximately").

## Not attempted this slice
Extending guard coverage to the 15 files — explicitly out of this slice's bounded scope, per the same reasoning as `service-layer-bypass-audit.md`.
