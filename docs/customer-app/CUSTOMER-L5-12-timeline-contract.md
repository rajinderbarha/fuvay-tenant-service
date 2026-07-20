# CUSTOMER-L5-12 — Timeline Contract

## Endpoint

`GET /v1/customer/bookings/{bookingId}/tracking` — a real, genuine
lifecycle timeline built from `ServiceJobAssignmentEvent` (append-only,
`app/engines/home_service_assignment/models.py`), already mapped to
customer-safe labels server-side by `_safe_event_label()`.

## Event-by-Event Contract

| Backend `event_type` | Customer title (backend-authored, rendered verbatim) | Visibility | Ordering | Test coverage |
|---|---|---|---|---|
| *(synthetic, no `event_type`)* | "Booking confirmed" | Always first, real (not client-fabricated — the backend's own router code literally prepends this row before querying real events) | Always position 0 | `booking-tracking-schema.test.ts` |
| `assignment_created` | "Technician assigned." | Customer-visible | By `created_at ASC` (backend `ORDER BY`) | Covered via schema test |
| `technician_accepted` | "Technician accepted your booking." | Customer-visible | Same | Same |
| `technician_rejected` | "Provider is finding another technician." | Customer-visible | Same | Same |
| `assignment_reassigned` | "Technician updated." | Customer-visible | Same | Same |
| `assignment_cancelled` | "Provider is finding a technician." | Customer-visible | Same | Same |
| `job_scheduled` | "Visit scheduled." | Customer-visible | Same | Same |
| `job_received` | *(not mapped — real event type exists in constants but has no entry in `_safe_event_label`, and per research is not confirmed to be actually emitted by any real code path)* | Never appears (backend drops it) | N/A | N/A |
| `assignment_failed` | *(same as above — defined, not mapped, not confirmed emitted)* | Never appears | N/A | N/A |
| Any other/future real event type | Dropped **server-side** (`_safe_event_label` returns `None`, router skips it) | Never appears | N/A | N/A |

## Ordering

Backend-guaranteed: `ORDER BY ServiceJobAssignmentEvent.created_at` (the
router's own query). This client renders the array exactly as received —
no client-side re-sort, no client-generated sequence number.

## No Unknown-Event Handling Needed on This Client

Because the backend itself silently drops any `event_type` without a
customer-safe label (verified: the router's loop only appends when
`label` is truthy), this client's timeline schema never actually receives
an unrecognized `event_type` from this endpoint in practice. The schema
still fails safe on a structurally malformed timeline *item* (e.g. missing
the required `event` string) by dropping just that row
(`parseBookingTracking`'s per-item resilience, matching the established
"drop invalid rows, don't fail the whole screen" pattern) — a
defense-in-depth measure, not a response to any real observed case.

## Current Milestone vs. Future Milestones

Per §25, this sprint does **not** render synthetic "future expected
steps" — there is no real data source for what a customer's specific next
milestone will be (no ETA, no scheduled dispatch time beyond
`scheduled_time_window` itself). The rendered timeline shows only real,
already-occurred events (each with a real `created_at` timestamp, except
the synthetic first row) — never a fabricated future entry.

## Accessibility

Each timeline row is rendered as plain text (event label + optional
timestamp) with a checkmark icon that is purely decorative — the
information is fully conveyed by the text alone, satisfying §55's "must
be understandable without icons or color" requirement without any
additional accessibility-specific code needed.

## Localization

Event labels themselves are real, backend-authored **English-only**
strings (confirmed: `_safe_event_label`'s dictionary in
`home_service_assignment/customer_router.py` has no locale awareness) —
this is a real, disclosed gap (same category as prior sprints'
`customer_visible_reason`/`assignment_message` findings): Hindi/Punjabi
customers see these specific strings in English regardless of app
locale. Documented in `known-gaps.md`, not silently mistranslated.
