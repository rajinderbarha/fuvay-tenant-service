# Checklist Item / Parent Integrity — Slice 2F-13 (Workstream 7)

## Verified (with directly-connected fixes where needed)
- **Item belongs to template**: `_get_item_for_template(template_id,
  item_id)` loads the item and rejects it if
  `item.template_id != template_id` or it is soft-deleted →
  `CHECKLIST_ITEM_NOT_FOUND`. Foreign-item substitution across templates
  is rejected. Proven: `TestItemParentIntegrity::test_foreign_item_under_template_rejected`.
- **Template belongs to tenant before item access**:
  `_get_item_for_template` calls `_get_template_for_tenant` FIRST, so a
  cross-tenant item mutation is rejected at the template layer (fixed to
  be role-agnostic this slice).
- **Submitted item_id cannot be substituted from another checklist**:
  yes — the parent check above.
- **Submitted template_id cannot be substituted from another tenant**:
  yes — `_get_template_for_tenant` (fixed).
- **Read item leak closed**: `list_items` now enforces
  `_get_template_for_tenant` (was an unchecked cross-tenant read).

## Not applicable in this router (no such capability)
- **Item belongs to job / checklist belongs to job**: N/A — this router
  has no job checklist; templates are not job-scoped.
- **Reordering with foreign item IDs / bulk item updates**: N/A — no bulk
  or reorder endpoint exists (items are updated one at a time via
  `PUT /{template_id}/items/{item_id}`). Sort order is a per-item
  `sort_order` field, updated individually — no multi-item reorder route.
- **Template item belongs to template/version**: no version model exists
  (see `template-version-snapshot-behavior.md`).

## Historical snapshot integrity (verified, unmodified)
Removing a template item (`delete_item`, soft delete) and deleting a
template (`delete_template`, soft delete) do **not** touch historical
`job_checklist_items` — `delete_template`'s own docstring states this,
and the models are distinct (a job snapshot copies flags at seed time).
So updating/deleting a template never silently mutates a historical job
checklist snapshot.
