# Evidence / Media Boundary

> **SUPERSEDED (Slice 2F-14A):** `JobMedia`'s access-control gap (surface 2 below) was fixed in
> Slice 2F-14A, not deferred. See
> `docs/workflow-rearchitecture/phase-02a-slice-02f14a/jobmedia-access-control.md`. Content below
> retained for historical record.

## Two distinct "photo evidence" surfaces exist

1. **`JobChecklistItem.photo_urls`/`requires_photo`/`requires_note`** — part of the checklist
   execution snapshot (see job-checklist-materialization.md), enforced by
   `update_job_checklist_item`: if `item.requires_photo` and no `photo_urls` supplied,
   `CHECKLIST_ITEM_PHOTO_REQUIRED` is raised (and symmetrically for `requires_note`). This is a
   **simple URL-list field on the checklist item row** — there is no dedicated media/evidence
   model, no upload endpoint, no storage-key validation, and no size/type/virus-scan
   infrastructure backing it. Classified `UNSUPPORTED_CAPABILITY_BEYOND_URL_LIST`: the field
   exists and is gated correctly for what it is, but building real media infrastructure (upload,
   storage, retrieval, signed URLs) is explicitly out of this slice's scope per the mission
   ("do not build media infrastructure").

2. **`JobMedia`** (`job_media` table) — a separate, dedicated media-attachment model with
   `media_id`, `media_type`, `caption`, `storage_key`. Exposed only via `field_ops.router`'s
   `add_media`/`list_media` (out of scope this slice, see job-note-privacy.md for the identical
   unfiltered-access finding — `list_media` also performs no tenant/role/ownership filtering).

## Conclusion

Both surfaces are pre-existing and unchanged this slice. Checklist-item photo evidence is a
required-field gate only (`update_job_checklist_item`'s existing validation), not a media
infrastructure capability. `JobMedia`'s access-control gap is documented as an out-of-scope
finding, not fixed, per the same reasoning as job-note-privacy.md.
