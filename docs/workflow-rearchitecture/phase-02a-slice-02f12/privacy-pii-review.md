# Privacy/PII Review — Slice 2F-12 (Workstream 12)

## Fields present
`CoachingAppointment.student_name`/`student_phone`/`student_email`/
`target_exam`/`target_band`/`preferred_mode`/`selected_date`/
`selected_time_start/end`/`city`; `CoachingAppointmentNote.note_text`/
`is_customer_visible`.

## Verified this slice
- **Customers see only their own appointment data**:
  `customer_tracking`'s combined `id` + `customer_id` filter (unchanged,
  pre-existing) + `require_customer` (fixed this slice).
- **Provider-internal notes do not enter customer responses**:
  `customer_tracking` never calls `get_timeline` at all (confirmed by
  source inspection) and calls `get_notes(..., customer_only=True)` —
  structurally, not just conventionally, excluded.
- **Technicians cannot read student PII at all**: technician is denied
  at the persona layer for every route in this module, mutations and
  reads alike (fixed this slice, from the outset — no follow-up needed
  unlike real estate's 2F-11/2F-11A split).
- **Cross-tenant IDs do not leak existence or content**: tenant filter
  in `_get_appt`/`get_timeline`/`get_notes`.
- **Public/query endpoints expose no student PII**: no unauthenticated
  or public route exists anywhere in this module.
- **Audit events avoid unnecessary raw sensitive payloads**:
  `CoachingAppointmentExecutionEvent.to_dict()` contains no raw student
  contact fields — only `event_type`/`old_status`/`new_status`/`notes`
  (staff-authored free text)/`actor_role`. `event_metadata`/`request_id`
  (stored on the model) are not included in `to_dict()`.

## No proven PII leak found
Identical structural analysis to real estate's `privacy-pii-review.md`
(Slice 2F-11A) — this router's serializers were designed the same way,
by the same author, and share the same, already-correct minimization
properties.
