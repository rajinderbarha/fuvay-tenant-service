# Checklist Service Bypass Report — Slice 2F-13 (Workstream 17)

## Methods reached by `checklist_router` and their callers
`ChecklistTemplateService` methods: `create_template`, `list_templates`,
`get_template`, `update_template`, `delete_template`, `list_items`,
`_list_items_unchecked`, `add_item`, `update_item`, `delete_item`, plus
helpers `_get_template_for_tenant`, `_get_item_for_template`.

**Callers**: only `checklist_router` (the 9 routes) + tests. No worker/
internal caller. Confirmed by grep — `ChecklistTemplateService` is
instantiated only in `checklist_router._svc` and test files.

## Object-ownership at the service layer (router guards do not replace it)
- **Tenant ownership**: enforced in `_get_template_for_tenant` for every
  tenant-scoped actor (fixed this slice — was tenant_owner-only). Reached
  by get/update/delete/add_item/update_item/delete_item and (fixed)
  `list_items`.
- **Item→template parent**: `_get_item_for_template` (item.template_id ==
  template_id), which also calls `_get_template_for_tenant` first.
- **create/list_templates**: principal-tenant-bound via `_tenant_id(u)` /
  the query filter (super_admin body override is the explicit platform
  pattern).

## Bypasses found and closed (all 3, directly connected)
1. Access-scope (6 mutation guards) — fixed in the router.
2. `_get_template_for_tenant` role-conditional tenant check — fixed
   (defense-in-depth at the service layer, independent of the router
   guard).
3. `list_items` unchecked read — fixed (service-layer ownership check).

## No repository-wide claim
Only `ChecklistTemplateService` (this router's service) was audited. The
out-of-scope `FieldOpsService` (job checklist execution) was not
re-audited.
