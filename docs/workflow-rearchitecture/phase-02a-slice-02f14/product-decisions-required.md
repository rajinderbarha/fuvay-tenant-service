# Product Decisions Required

1. **`JobNote`/`JobMedia` access control** — `add_note`/`list_notes`/`add_media`/`list_media` on
   `field_ops.router` perform no tenant, role, or `is_internal` filtering at all. This needs a
   dedicated future slice (scoped specifically to the notes/media capability) to decide: who may
   read internal notes (staff/technician/tenant_owner only, vs. customer-visible notes filtered
   by `is_internal=False`), and to add tenant/job-ownership scoping to both `add_*` and `list_*`.
   Not fixed this slice — see job-note-privacy.md, evidence-media-boundary.md.
2. **Legacy `Job.checklist` JSONB / `update_checklist` route** — confirmed inert (does not
   affect the completion gate). Product should decide whether to formally deprecate/remove this
   dead route and field, or leave it as historical dead weight. No live frontend caller exists
   currently (frontend-mobile-exposure-audit.md), so removal carries no user-facing risk, but
   that is a product cleanup decision, not a security fix, and out of this slice's scope.
3. **Evidence/media capability for checklist items** — `JobChecklistItem.requires_photo` is
   gated on presence of a `photo_urls` string list with no actual upload/storage/validation
   infrastructure behind it. If real photo evidence is a product requirement, a dedicated
   media-infrastructure slice is needed (explicitly out of scope here per the mission).
