# Technician Execution Boundary — Slice 2F-13 (Workstream 9)

## UNSUPPORTED_CAPABILITY in this router
`checklist_router` has **no technician execution route** — no
"start checklist", "answer item", "toggle complete", "add note",
"add evidence", "mark complete", or "submit for review" endpoint. It is
template administration only.

- Technician **cannot** reach any route here: `FIELD_OPS_CHECKLIST_MANAGE`
  is not granted to the technician role (and the reads/mutations all
  require it), so technician receives 403 on every route. Proven:
  `test_no_permission_role_denied_on_every_mutation[technician]`.
- Technician checklist EXECUTION (against `JobChecklistItem`, with
  `requires_photo` evidence and per-job assignment) lives in the
  out-of-scope `field_ops.service.py` / `field_ops.staff_router`. That
  surface is where "technician assigned to the job", "item active",
  "cannot self-approve", etc. would apply — **not audited or modified
  this slice** ("do not begin field_ops.staff_router").

Per the mission's instruction ("do not create technician capability where
no technician route exists"), no technician execution capability was
created here. Reported honestly as absent.
