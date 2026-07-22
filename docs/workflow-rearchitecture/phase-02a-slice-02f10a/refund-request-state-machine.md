# Refund Request State Machine — Slice 2F-10A (Workstream 7)

## Trace: `create_refund_request_from_complaint`
- **Complaint lookup**: `get_customer_complaint` (ownership-checked,
  Slice 2F-10 fix, unmodified this slice).
- **Customer ownership**: enforced via the above.
- **Complaint status**: read (`complaint.status`) but does not gate
  `RefundRequest` creation itself — only gates whether the complaint's
  own status transitions alongside it (see
  `refund-silent-transition-review.md`).
- **`RefundRequest` model**: created with `status = REFUND_REQUESTED`
  always; `customer_id`/`tenant_id`/`invoice_id`/`booking_id`/`job_id`/
  `appointment_id`/`lead_id` all copied from the complaint (not
  customer-supplied) — no cross-linkage IDOR surface exists here.
- **Requested amount / reason source**: both are customer-supplied input
  fields on `RefundRequest`, stored as a request only — never trusted as
  an approved amount (approval is a separate, provider-only path).
- **Complaint transition call**: `complaint.status = STATUS_REFUND_REQUESTED`
  only `if STATUS_REFUND_REQUESTED in ALLOWED_TRANSITIONS.get(complaint.status,
  set())` — a conditional, silent skip otherwise (see
  `refund-silent-transition-review.md` for why this is intentional).
- **Audit event**: `EVT_REFUND_REQUESTED`, logging the *real* applied
  status (`None` when the transition was skipped) — `MODULE-L5-02 bug #31`,
  re-verified unmodified and correct.
- **Notification**: none directly in this method (not found in this
  code path).
- **Commit/flush order**: `db.add(refund)` → `db.flush()` →
  (conditional) `complaint.status = ...` → `db.flush()` →
  `_log_event` → `db.commit()`.
- **Admin approval boundary**: entirely separate —
  `provider_review_refund` (provider-only, `provider_router`, Slice
  2F-9-closed) and any admin path (`admin_router`, untouched, out of
  scope) are the only routes that can advance a `RefundRequest` past
  `requested`.

## Exact legal source states for the complaint-side transition
Per `ALLOWED_TRANSITIONS` (base map, not the extended AI-settlement
variant — confirmed this is the map actually used here):
`STATUS_OPEN`, `STATUS_AWAITING_PROVIDER`, `STATUS_UNDER_ADMIN_REVIEW` —
the only 3 keys whose transition set includes `STATUS_REFUND_REQUESTED`.
Every other status (including `resolution_proposed`, `rework_approved`,
`resolved`, `settled`, `closed`, `cancelled`, `rejected`, and
`refund_requested`/`approved`/`recorded` themselves) results in the
transition being silently skipped — but the `RefundRequest` row is still
created (see `refund-silent-transition-review.md`).
