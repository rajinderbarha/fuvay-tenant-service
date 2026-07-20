# Known Limitations

1. `JobNote`/`JobMedia` have no access-control filtering at all on `field_ops.router`'s
   `add_note`/`list_notes`/`add_media`/`list_media` (see job-note-privacy.md,
   evidence-media-boundary.md). Not fixed this slice — distinct capability from the
   same-record-same-capability scope this slice was bounded to.
2. `_provision_job_checklist_items` idempotency was re-confirmed by code inspection, not by a new
   dedicated concurrency/race-condition test (e.g. two simultaneous `start_job_checklist` calls
   under real DB row-locking). No evidence of a race was found, but no new test was added to
   prove it under concurrent load.
3. The global-mutation-coverage recount (213 total / 143 protected) has a 3-row discrepancy
   against this slice's own headline arithmetic (210 / 146) — see global-coverage-update.md; a
   pre-existing, unreconciled CSV artifact, not introduced this slice.
4. The 19 out-of-scope `field_ops.router` routes (quotes/billing/media/notes/assessment) remain
   `UNVERIFIED` in the runtime introspection tool; their route paths in
   `field-ops-staff-final-route-inventory.csv` were reconstructed from source inspection rather
   than a fresh tool run limited to just those 19, since a full-module run was already performed
   this slice covering all 28 routes.
5. A stray, accidentally-committed temp file
   (`app/engines/field_ops/service.py.tmp.3332.f9e469299afb`, part of the original baseline
   commit `36efe8d`) was found and deleted as harmless cleanup — unrelated to this slice's
   security work but noted here for transparency.
