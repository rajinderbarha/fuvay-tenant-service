# Tenant Engine Alternate Route Audit

Scope: registered routes other than `tenant_engine.router`'s own 19
newly-guarded endpoints that could perform an equivalent mutation on the same
tenant-lifecycle/engine/flag/billing/data domain (Workstream 7). Not a
platform-wide alternate-route audit (Slice 2F's finding on the
`execution.home_service_router` vs `home_service_assignment` overlap remains
separately deferred, untouched this slice).

## Candidates found and cleared

### 1. `app/engines/tenant_engine/admin_router.py`
Defines its own `POST /{tenant_id}/suspend` (line 247) alongside other
tenant-lifecycle-adjacent admin actions (verify, activate, archive,
reactivate, request-changes, change-plan, add-usage-credits). Every single
endpoint in this file — all ~45 of them — is gated by `require_super_admin`
directly (confirmed via `grep -n "require_super_admin" admin_router.py`,
45 matches, one per route). Since `require_tenant_mutation_permission`
already exempts `super_admin` from the access-scope check, this router poses
no additional exposure beyond what already exists: a super_admin can always
reach both this admin surface and the tenant_engine.router surface. **Not a
bypass** — same trust level, by design (`PLATFORM_ADMIN_MUTATION`
equivalent).

### 2. `app/engines/settings_engine/admin_router.py`
Defines `PUT /feature-flags/{flag_id}`, `POST /feature-flags/{flag_id}/enable`,
`POST /feature-flags/{flag_id}/disable`, gated by
`require_permission(P.SETTINGS_FEATURE_FLAGS_UPDATE)`. Read the handler and
service method (`SettingsService.set_feature_flag_status`): this operates on
`settings_engine`'s own platform-level `FeatureFlag` table (keyed by
`flag_id`, a UUID), a materially different domain object from
`tenant_engine.router`'s per-tenant flag *override* (keyed by `tenant_id` +
`flag_key`, a string, resolved through a platform→plan→tenant hierarchy per
`resolve_feature_flag`'s docstring). **Not a bypass** — different table,
different permission, different concept (global flag definition vs. one
tenant's override of it).

## Conclusion
No alternate route was found that lets a caller reach the same tenant-scoped
mutation this slice just guarded, through a weaker gate. No closure action
was required.

## Addendum (Slice 2F-1A)
Frontend-exposure evidence confirms candidate #1 above is not merely
equal-trust-level but the **actual, sole in-use caller path** for
`tenant_engine.router`'s own `/suspend` and sibling endpoints is the
super-admin app calling `tenant_engine.router` directly (`/v1/tenants/{id}/suspend`
etc.), not `admin_router.py`'s parallel `/v1/admin/tenants/{id}/suspend`.
Both routes exist and both work (same super_admin trust level), which is a
duplication worth resolving in a future slice (see
`product-decisions-required.md` item 6 context) — not resolved here, per
this slice's explicit "do not remove without a safe compatibility plan"
constraint.
