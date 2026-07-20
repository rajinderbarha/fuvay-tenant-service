# Required-Item / Completion Gate — Slice 2F-13 (Workstream 11)

## Not in this router (documented boundary)
`checklist_router` defines **template** required-item flags
(`ServiceChecklistItem.is_required`, `requires_photo`, `requires_note`) —
i.e. what a future job checklist will demand. It does **not** mark any
checklist or job complete; it has no completion route.

## Where the gate actually lives (out of scope, unmodified)
The authoritative job-completion gate operates on `JobChecklistItem`
(the copied snapshot) inside `field_ops.service.py` — proven by the
existing, passing `test_checklist_system.py::test_seeded_checklist_blocks_
work_complete_until_done` and `test_checklist_required_without_template_
is_rejected`. That gate:
- blocks `field_ops.Job` work-completion until required snapshot items
  are done, and
- is entirely separate from the template rows this router edits.

## Template edits cannot bypass the gate
Because job checklists are copied snapshots (see
`template-version-snapshot-behavior.md`), editing or deleting a template
via this router does NOT alter any active job's required-item set or its
completion gate. `delete_template` explicitly never touches historical
`job_checklist_items`. So there is no path by which a template mutation
here weakens or bypasses the (out-of-scope) job-completion gate.

## Conclusion
Completion-gate behavior for jobs is authoritative but lives outside this
router. Within this router, completion gating is `UNSUPPORTED_CAPABILITY`.
No new completion gate was imposed (per the mission's instruction).
