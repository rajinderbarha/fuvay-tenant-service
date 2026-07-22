# Cancellation Reason Integrity — Slice 2F-12A (Workstream 8)

## Behavior (from `cancel_appointment` source, unmodified)
- **Required**: yes — `if not reason or not reason.strip(): raise
  ValueError(ERR_REASON_REQUIRED)`. This check runs **first**, before
  even fetching the appointment (`db.execute` is never called for an
  empty/whitespace reason — proven by
  `test_empty_reason_rejected_before_any_lookup`).
- **Maximum length**: none enforced at the service layer (`reason` is a
  free-text field; `appt.failure_reason` is a `Text()` column). Not
  changed — no defect (matches the sibling `cancel_job`, which also
  imposes no length cap; adding one would be new validation absent from
  the established pattern).
- **Empty / whitespace reason**: rejected with `ERR_REASON_REQUIRED`
  (proven directly).
- **Customer-visible?**: `reason` is stored on `appt.failure_reason` and
  as the cancellation event's `notes`. The customer tracking route
  (`customer_tracking`) returns `appt.to_dict()` — which includes
  `failure_reason` — to the appointment's own customer. So the
  cancellation reason IS visible to the customer whose appointment it is
  (appropriate — they are told why their appointment was cancelled). It
  is not exposed to any other customer (customer_id filter) or publicly.
- **Internal notes in reason?**: the reason is a single free-text field
  with no visibility flag; it is not a provider-internal note (those go
  through `add_note` with `is_customer_visible`). Staff should treat the
  cancellation reason as customer-facing — documented, not enforced by a
  new check (no evidence of a defect; matches `cancel_job`).
- **Overwrite / repeated cancellation**: a repeated cancel on an
  already-cancelled appointment is rejected by `_assert_transition`
  (`cancelled` has an empty transition set) before any mutation — so the
  reason cannot be overwritten via a second cancel
  (`test_repeated_cancel_rejected`).
- **Audit logged?**: yes — the reason is passed as the `notes` of the
  `CA_EV_CANCELLED` event and stored on `failure_reason`.
- **Sensitive data in logs/notifications?**: no notification
  infrastructure exists (nothing is sent anywhere). The audit event's
  `notes` field carries the staff-authored reason — expected,
  proportionate audit content, not raw student PII duplication.

## No change made
Reason handling was already correct and consistent with the approved
sibling `cancel_job`. No new validation was added (per the mission's
instruction not to add validation absent from established patterns unless
a direct defect is proven — none was).
