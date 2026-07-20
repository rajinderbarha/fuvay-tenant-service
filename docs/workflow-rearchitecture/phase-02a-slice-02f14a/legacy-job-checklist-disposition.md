# Legacy Job.checklist / update_checklist Disposition

## Classification: PROTECTED_COMPATIBILITY_ROUTE

`Job.checklist` (JSONB: `list[{"step": str, "completed": bool}]`) and its mutator
`FieldOpsService.update_checklist` are mounted on both routers
(`PUT /v1/staff/me/jobs/{job_id}/checklist` was never actually mounted — confirmed staff_router
has no such route; the legacy route only exists on `field_ops.router` at
`PUT /v1/jobs/{job_id}/checklist`).

## Guard status

Gated by `require_staff_or_technician_only` at the router level (already fixed in Slice 2F-14)
and `_assert_assigned` at the service level (assigned-technician-only, pre-existing, unmodified).
Both are correctly enforced — **not** a live weaker alternate.

## Bypass check

- **JobChecklistItem ownership**: not touched by this method at all (writes only to
  `Job.checklist`, a separate field).
- **CHECKLIST_STARTED enforcement**: not applicable — this method doesn't go through
  `update_job_checklist_item`'s gate because it doesn't touch `JobChecklistItem` rows.
- **Required-item completion**: `complete_job_checklist`'s required-item check reads from
  `JobChecklistItem`, never from `Job.checklist` — confirmed via source inspection, this legacy
  write cannot satisfy or bypass that gate.
- **Final Job protection**: `update_status`'s `WORK_COMPLETE` guard checks
  `job.status == JS.CHECKLIST_COMPLETE`, which is only ever set by
  `complete_job_checklist` — writing to `Job.checklist` does not set this status.
- **Technician assignment / tenant isolation**: enforced (`_assert_assigned`), unchanged.

## Conclusion

This route is mounted, correctly guarded, and functionally inert with respect to the
authoritative completion gate (it writes to a field nothing else reads for gating purposes). It
is not a bypass and does not need to be blocked or deprecated for security reasons. Whether to
formally deprecate/remove the dead field for cleanliness is a **product decision**
(`product-decisions-required.md`), not a security requirement — no frontend/mobile caller was
found (confirmed in Slice 2F-14's frontend-mobile-exposure-audit.md, re-confirmed unchanged this
slice).
