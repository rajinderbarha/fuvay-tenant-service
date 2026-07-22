# Role Navigation Implementation

## Implemented this phase
**Technician shell only** (`frontend/tenant-portal/components/layout/StaffLayout.tsx`), which already existed and already gated correctly on `ctx.isTechnician`. One item added:

| id | href | label | position |
|---|---|---|---|
| `my-work` | `/staff/my-work` | My Work | 2nd (after Dashboard) |

This matches the approved technician target nav (`Today, My Jobs, Inspection and Quote, Work Completion, Profile`) in spirit — the existing shell uses different labels (`Dashboard`, `Assigned Work` for My Jobs, etc.) that were not renamed this phase (out of scope: renaming existing nav labels was not part of the chosen vertical slice, and doing so without also reconciling the corresponding page content/breadcrumbs would be a partial, risky change).

## Permission enforcement
- `StaffLayout` already blocks non-technician roles before rendering any nav (`if (!ctx.user || !ctx.isTechnician) { ... access denied ... }`) — unchanged, still the sole gate at the layout level.
- The new `/v1/staff/my-work` endpoint requires `get_current_user` (standard auth) and resolves the staff member via the same tenant/staff-scoping helper pattern used by every other endpoint in this router family — it does not introduce a new permission model, and hidden navigation is not the only control: the backend independently tenant-scopes and staff-scopes every query (see `route-and-permission-test-report.md`).

## Not implemented this phase
- super_admin, admin_operations/finance/security/readonly shell (9-item nav per `final-role-navigation-matrix.csv`)
- tenant_owner shell (9-item nav)
- staff/manager shell (7-item nav — distinct from technician)
- Badge/count wiring for any shell's nav items (the technician shell's nav items still show no counts; adding a My Work count badge to the nav itself, as opposed to the My Work page's own section counts, was not done this phase)

These are tracked in `deferred-items.md`.
