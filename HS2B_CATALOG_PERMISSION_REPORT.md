# HS2B — Catalog Permission Report

## Real permission constants used (not the ticket's assumed namespace)
`app/core/permissions.py` has no `admin.home_services.catalog.*`
constants. It does have real, existing, generic catalog permissions
already used elsewhere in the admin app: `catalog:services:read`,
`catalog:services:write`, `catalog:types:read/write`,
`catalog:brands:read/write`. This sprint wired the HS2 catalog console
to these real constants via the existing `usePermissions()` hook
(already used by `/admin/pricing/bargain-rules` and
`/admin/pricing/provider-overrides`), rather than the ticket's assumed
(non-existent) namespace.

## Implemented this sprint
| Rule | Implementation |
|---|---|
| No read permission → 403 block state | `!perm.loading && !canRead` renders a full-page "You don't have access to the Home Services Catalog" state instead of the catalog |
| Read-only → hide Add/Edit/Delete/Toggle | "Add Service Group" and "Add Service" buttons gated by `canCreate` (`catalog:services:write`); service detail's action link shows "View" instead of "Manage" when `!canUpdate` |
| No create → hide Add Service Group/Add Service | Both buttons wrapped in `{canCreate && (...)}` |
| No audit → hide Activity tab | Tab list filters out `activity` when `!canAudit`; the tab's content is also guarded (`canAudit && <ActivityTab/>`) as defense-in-depth |
| Backend 403 shows request_id | Not independently re-verified this sprint — relies on the existing, already-certified `apiFetch`/`ServiceOSError` global error contract (confirmed present and unchanged in `lib/api.ts`), which surfaces `request_id` on every non-2xx response including 403s |

## Gap: no dedicated delete/update permission split
The ticket lists separate `create`/`update`/`delete` permissions. This
console only has one real write permission (`catalog:services:write`)
covering all three — there's no way to distinguish "can edit but not
delete" today. `canUpdate` and `canDelete` are both currently mapped to
the same constant. Documented as a gap; a real split would need new
permission constants added to `permissions.py` (out of this sprint's
time budget).

## Live verification not performed
This sprint's permission wiring was verified via static inspection
(`test_hs2b_permission_aware_ui`, `test_hs2b_no_read_permission_blocks_page`,
`test_hs2b_add_service_group_gated_by_create_permission`,
`test_hs2b_activity_tab_gated_by_audit_permission` — all passing) but
**not** via an actual login as a restricted-permission test user (no
such test account was created/available this sprint) — so the real
runtime behavior (does the backend actually return 403 for a user
lacking `catalog:services:write`?) was not live-verified.

## Verdict
Permission-aware UI: **implemented and statically verified**, using
real, existing permission constants. Backend enforcement and a live
restricted-user smoke test were **not performed** this sprint.
