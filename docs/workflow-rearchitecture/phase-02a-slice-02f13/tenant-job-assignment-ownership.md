# Tenant / Job / Assignment Ownership — Slice 2F-13 (Workstream 6)

## Tenant ownership (the core of this slice)
- **Principal tenant authoritative**: mutations derive tenant from
  `u.tenant_id` via `_tenant_id(u)` (create) or from the fetched template
  (update/delete/items). No request `tenant_id` overrides the principal
  **except** the explicit, pre-existing super_admin body-`tenant_id`
  override on `create_template` (platform pattern, principal-bound for
  every non-super_admin actor).
- **Template belongs to principal tenant** — `_get_template_for_tenant`,
  **fixed this slice** to enforce for every tenant-scoped actor (was
  `tenant_owner`-only, letting an override-granted `staff` reach foreign
  templates). Foreign template ID → `CHECKLIST_TEMPLATE_NOT_FOUND` (no
  existence leak). Proven: `TestTemplateTenantOwnershipIDOR` (staff
  foreign rejected, owner foreign rejected, super_admin exempt, matching
  allowed) + `TestListItemsReadIDOR`.
- **Item belongs to supplied template** — `_get_item_for_template`
  rejects an item whose `template_id` ≠ the path `template_id`
  (`CHECKLIST_ITEM_NOT_FOUND`), and calls `_get_template_for_tenant`
  first so tenant ownership is enforced before item lookup. Proven:
  `TestItemParentIntegrity`.

## Job / assignment ownership
**Not applicable** — this router has no job or assignment concept
(templates are catalog definitions, not per-job records). Job/assignment
ownership for the per-job checklist snapshot lives in the out-of-scope
`field_ops.service.py`/`staff_router`. A "query filtered by tenant alone"
technician-assignment concern does not arise here because there is no
technician route and no job in this router.

## Foreign-ID rejection summary (all fail-closed NOT_FOUND, tested)
- Foreign template ID (mutation or read) → rejected.
- Foreign item ID under a template → rejected.
- Request tenant override (non-super_admin) → ignored (principal used).
