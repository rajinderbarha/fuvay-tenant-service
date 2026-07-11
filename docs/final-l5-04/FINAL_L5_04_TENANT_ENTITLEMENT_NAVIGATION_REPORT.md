# FINAL-L5-04 — Tenant Entitlement Navigation Report

## This is the central blocker of this sprint

## Required behavior vs. real, verified current state
| Requirement | Real current state |
|---|---|
| 1. Platform module status | Tenant Portal's sidebar (`TENANT_NAV_GROUPS`) does not consult platform module status at all — it renders unconditionally, confirmed by direct source read (no `moduleKey`/enabled-check field exists on any `NavItem`) |
| 2. Tenant enabled modules | **Not implemented.** `categoryDashboardApi.getRuntime()` (`GET /v1/tenant/dashboard/runtime`) *does* return `enabled_engines: string[]` and `modules: Array<{...is_enabled...}>` — real, typed fields — but `TenantLayout.tsx` never fetches or consumes this endpoint for navigation filtering (confirmed via grep: zero references to `categoryDashboardApi`/`getRuntime`/`enabled_engines` in `TenantLayout.tsx`) |
| 3. Tenant approved categories | Not implemented — no category-approval-to-menu-visibility connection exists |
| 4. Tenant role permissions | Partially — `isTenantReadOnly()` gates individual mutation buttons app-wide (established FINAL-L5-01D), but does not hide/show entire *menu items* based on role |
| 5. Tenant setup readiness | Not connected to menu visibility (setup readiness is shown via a separate `SetupWizardDrawer` checklist, not via hiding/showing sidebar items) |
| 6. Tenant package/plan restrictions | Not implemented |

## Root cause found and diagnosed this sprint: the underlying data is broken, not just unwired
Live-queried this sprint: `tenant.category_id` is **NULL for every seeded tenant** (`Demo AC Services`, `Isolation Test Services` — both `None`), while `tenant.vertical` is correctly populated (`'home_services'` for both). `app/engines/tenant_engine/portal_router.py::get_dashboard_runtime` resolves `enabled_engines`/`modules` **exclusively via `tenant.category_id`**:
```python
if tenant and tenant.category_id:
    category = await db.scalar(select(ServiceCategory).where(ServiceCategory.id == tenant.category_id))
```
Since `tenant.category_id` is always `None` in practice, this branch never executes, and `enabled_engines`/`modules` are **always empty arrays** — confirmed via a live API call this sprint: `GET /v1/tenant/dashboard/runtime` for the real seeded demo tenant returns `"enabled_engines":[],"modules":[]`.

A prior sprint already found and fixed an analogous issue for the adjacent `category_type` field, adding an explicit fallback: `"category_type": vertical or (category.category_type if category else None)` (confirmed via reading the same function, and corroborated by a real, passing test — `test_backend_runtime_returns_top_level_category_type_from_tenant_vertical` in `tests/test_tenant_home_services_vertical_detection_fix.py`, 111/111 passing this sprint). That same fallback pattern was **never extended** to the `enabled_engines`/`modules` resolution, which is why this specific data has stayed silently empty.

## Why this was not fixed this sprint
Wiring `TenantLayout` to filter `TENANT_NAV_GROUPS` by `enabled_engines`/`modules` would be straightforward *if the data were real* — but doing so against the current, always-empty data would either (a) hide the entire tenant sidebar for every real tenant (a severe regression, since "no modules enabled" would be misread as "no modules available"), or (b) require first fixing the backend's category-resolution fallback (a genuine, valuable, but separate and non-trivial change: it touches the same function this sprint already knows has a real test suite, needs the vertical→category lookup logic implemented correctly — not just copy-pasted — and needs its own dedicated verification pass, including checking whether `enabled_engines`/`modules` are even *populated* anywhere in the schema for the `home_services` category, which was not confirmed this sprint). Attempting this blind, at the end of an already-large sprint, would violate this mission's own rule 1 analog ("do not rewrite... without evidence") and risk a real, live regression to the Tenant Portal's primary navigation for every tenant.

## What this means for certification
Per the mission's own explicit instruction: **"Do not return READY if... Tenant entitlement is ignored."** Tenant entitlement is, factually, currently ignored by the live Tenant Portal navigation — this is not a matter of interpretation. This single finding is sufficient on its own to prevent an unconditional `READY_FINAL_L5_04_DYNAMIC_NAVIGATION_CERTIFIED` recommendation, and is the primary reason this sprint's Final Report recommends `PARTIAL_READY_WITH_FINAL_L5_04_BLOCKERS`.

## Recommended next step (not implemented this sprint)
1. Fix `get_dashboard_runtime`'s category resolution to fall back through `tenant.vertical` the same way `category_type` already does, verifying `enabled_engines`/`modules` actually populate for a real tenant afterward (dedicated backend fix + test).
2. Only then wire `TenantLayout` to filter `TENANT_NAV_GROUPS` by the now-real `enabled_engines`/`modules`, following the exact `isNavItemVisible()` pattern already proven safe in `AdminLayout.tsx` (fail-open — show items while data is loading/null — to avoid a flash-of-no-nav).
3. Certify with the same browser-proof pattern established this sprint for verticals (toggle an entitlement → menu updates live, no reload).

## Result
`NOT_READY_FINAL_L5_04_TENANT_ENTITLEMENT_FAILED` in isolation would be the technically correct status for this Part alone; it is folded into the sprint's overall `PARTIAL_READY_WITH_FINAL_L5_04_BLOCKERS` recommendation rather than used as the final status directly, since substantial, real, verified progress was made elsewhere (see Final Report).
