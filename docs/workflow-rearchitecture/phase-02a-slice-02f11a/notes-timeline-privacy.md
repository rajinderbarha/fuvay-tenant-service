# Notes and Timeline Privacy — Slice 2F-11A (Workstream 7)

## Note model
`RealEstateLeadNote` — `note_type`, `note_text`, `is_customer_visible`
(bool, default `False`), `created_by_user_id` (not exposed in `to_dict()`).
Created only by `add_note` (agent mutation, now
`require_owner_or_office_staff_mutation`-gated, unchanged).

## Timeline model
`RealEstateLeadExecutionEvent` — one row per `_set_status` call (every
lifecycle mutation) plus a dedicated `note_added` event type. Payload:
`event_type`, `old_status`, `new_status`, `notes` (free text), `actor_role`
(hardcoded `"agent"` for every event in this module), `created_at`.
`assigned_agent_id`/`actor_user_id` are stored on the model but **not**
included in `to_dict()` — confirmed absent from the serialized response.

## Verified this slice
- **Customers receive only customer-visible events and notes**:
  `customer_tracking` never calls `get_timeline` at all (confirmed via
  direct source inspection, `test_customer_tracking_excludes_timeline_and_internal_notes`)
  — the entire audit trail is structurally unreachable from the customer
  path, not merely filtered. Notes are fetched with
  `customer_only=True`, filtering to `is_customer_visible == True` only.
- **Provider-internal notes do not enter customer tracking responses**:
  same mechanism as above.
- **Unassigned technicians cannot read internal notes**: technician is
  now denied at the persona layer for all 3 provider/agent read routes
  (fixed this slice) — moot regardless of note visibility.
- **Assigned technicians receive only fields explicitly required for
  execution**: N/A — no technician read path exists at all now; nothing
  to minimize.
- **Staff and owners remain tenant-scoped**: `tenant_id` filter in
  `get_timeline`/`get_notes`, unmodified, re-verified.
- **Cross-tenant note IDs do not leak existence**: `get_notes`'s query
  filters by `lead_id` AND `tenant_id` together — a foreign-tenant lead's
  notes are excluded by the tenant filter regardless of the `lead_id`
  supplied.
- **Timeline events do not include unnecessary raw payloads or secrets**:
  `event_metadata`/`request_id` (stored on the model) are **not** included
  in `RealEstateLeadExecutionEvent.to_dict()` — confirmed absent, a
  reasonable minimization (metadata could contain internal
  request-tracing detail not meant for a business-side read).

## No dead/ignored visibility field found
`is_customer_visible` is actively read and enforced by `get_notes`'s
`customer_only` parameter — not dead code.
