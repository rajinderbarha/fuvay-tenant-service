# Provider Verification Boundary — Slice 2F-13 (Workstream 10)

## UNSUPPORTED_CAPABILITY in this router
No provider-verification route exists in `checklist_router` — no
"approve checklist", "reject checklist", "request correction", "verify
evidence", "waive item", "override item", or "finalize" endpoint. There
is no `ChecklistApproval` model.

Checklist verification/approval (if any) against the per-job
`JobChecklistItem` snapshot would live on the out-of-scope
`field_ops.service.py` / `staff_router` job-execution surface — not
audited or modified this slice. Reported honestly as absent; no
verification capability was created here.
