# HS8 — Parts Request Report

## Status: partially implemented — documented as a real gap, not fabricated

`POST /v1/staff/service-jobs/{job_id}/parts-required` is real and
live-verified: a technician can mark a job as needing parts
(`{"note_text": "Need a new compressor capacitor"}`), which transitions
the job's `status` to `quote_required` (the codebase collapses
"parts required" and "quote required" into one terminal status —
`JOB_TRANSITIONS` has no distinct `parts_requested`/`parts_approved`
states) and logs a real execution event.

## What does NOT exist
- No dedicated Parts Request entity with fields matching the ticket
  (Part Name, Quantity, Estimated Cost, Reason, Photo, Customer/Business
  Approval flags) — `mark_parts_required` only accepts a free-text note.
- No tenant/business-side **approve/reject** action for a parts request.
  The only adjacent real system is Sprint 22's `quote_checklist` engine
  (`app/engines/quote_checklist/customer_router.py`), which lets the
  **customer** approve/reject/request-revision on a **quote** (which may
  bundle parts costs) — a different concept from a tenant approving a
  technician's parts request, and not wired to `mark_parts_required` at
  all.
- No `Requested/Approved/Rejected/Customer Approval Pending/Installed/
  Cancelled` status vocabulary anywhere in the codebase.

## Verdict
Parts request flow: **not implemented** as the ticket describes it —
only the technician-initiated "flag this job as needing parts" signal
exists, with no structured request record and no tenant approval step.
Per the ticket's own instruction ("If parts approval is not implemented,
document as blocker, not READY"), this is documented as a genuine
blocker, not claimed as working.
