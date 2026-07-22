# Template Version / Snapshot Behavior — Slice 2F-13 (Workstream 8)

## Disposition: NO_TEMPLATE_MODEL versioning; job side is a COPIED SNAPSHOT
- **No `ChecklistTemplateVersion` model exists** — this router uses live
  `ServiceChecklistTemplate` rows (no version pinning). Templates are
  editable in place (`update_template`, `update_item`).
- **Jobs reference a COPIED SNAPSHOT, not the live template**: at
  job-checklist-seed time (in the out-of-scope `FieldOpsService`/
  `BookingService`), `JobChecklistItem` rows are materialized with their
  OWN `is_required`/`requires_photo`/title columns copied from the
  template. Confirmed by `test_checklist_system.py::test_convert_to_job_
  seeds_checklist_from_catalog_template` and the distinct `job_checklist_items`
  table.

## Documented behavior
- **When the snapshot is created**: at job checklist start / booking→job
  conversion (out of scope; this router does not create it).
- **Template changes affecting active jobs**: NO — job snapshots are
  independent copies; editing/deleting a template row does not alter
  existing `JobChecklistItem` rows (`delete_template` docstring:
  "historical job_checklist_items are never touched").
- **Published templates immutable?**: no publish/immutability concept —
  templates remain editable (`is_active` toggle + soft delete only).
- **Archived templates readable for historical jobs?**: template soft
  delete does not affect historical job snapshots (which carry their own
  copied data), so historical job checklists remain fully interpretable.
- **Required flags / order / answer types copied?**: `is_required`,
  `requires_photo`, `requires_note`, `sort_order`, `title` all exist on
  both models; the snapshot copies them (job-seed logic, out of scope).
  This router has no free-form "answer type/options" model — items are
  boolean/photo/note requirement flags only.
- **Tenant replace template after execution starts?**: N/A in this
  router (no job-checklist replacement route here).
- **Regeneration deletes technician progress?**: N/A here (regeneration,
  if any, is on the out-of-scope job surface).
- **Version IDs enforced?**: no version model — not applicable.

## Conclusion
Template-side = LIVE_TEMPLATE_REFERENCE (editable, no versions). Job-side
= IMMUTABLE_SNAPSHOT (copied at seed time, template edits do not
propagate). Historical integrity is preserved by construction. No
versioning system was designed (none exists, and the mission forbids
building one).
