# CUSTOMER-L5-12 — Contract Matrix

Verified by direct reading of `app/engines/home_service_assignment/customer_router.py`,
`service.py`, `models.py`, `constants.py`, `app/engines/final_records/models.py`,
`app/engines/execution/home_service_service.py`, `home_service_router.py` —
cross-checked by an independent background research pass.

## Endpoints Used (primary source, per baseline-verification.md's Central Findings)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/customer/bookings` | Real, paginated (`page`/`page_size`) booking list — already server-side customer-safe. |
| `GET` | `/v1/customer/bookings/{bookingId}` | Real booking detail — real `assignment_status` + backend-authored `assignment_message`, plus `job_status`/schedule when a job exists. |
| `GET` | `/v1/customer/bookings/{bookingId}/tracking` | Real lifecycle timeline — built from `ServiceJobAssignmentEvent`, backend-authored customer-safe labels. |
| `GET` | `/v1/customer/bookings/{bookingId}/rating` | Real review-existence check — used only to decide review-boundary visibility (submission out of scope). |

## Endpoints Investigated and Explicitly NOT Used

| Method | Path | Parity status | Reason not used |
|---|---|---|---|
| `GET` | `/v1/customer/my-activity/bookings*` | `MATCHED` (real, still used by L5-11's own code, untouched) | Superseded for this sprint's purposes by the richer, already-customer-safe `/v1/customer/bookings*` router — no timeline endpoint exists here at all, and `provider_snapshot` is not server-side stripped. |
| `GET` | `/v1/customer/service-jobs/{jobId}/tracking` | `MATCHED` (real, confirmed reachable) | Deliberately deferred — its event vocabulary (dispatched/on-the-way/arrived/in-progress) and customer-visible notes/media belong to CUSTOMER-L5-13's live-tracking scope, not this sprint's assignment/acceptance/scheduling lifecycle. See baseline-verification.md. |
| `POST` | `/v1/customer/bookings/{bookingId}/rating` | `MATCHED` (real) | Review **submission** explicitly out of scope (§36) — this sprint only reads review existence via the `GET` counterpart. |
| any cancel/reschedule endpoint for a **confirmed** `ServiceBooking` | — | `MISSING_BACKEND` | Confirmed absent — the only real cancel endpoint found anywhere (`POST /{draftId}/cancel`, `home_service_booking`) operates on a pre-confirmation **draft**, not a confirmed booking. No customer-callable cancel/reschedule exists for a real `ServiceBooking` today. |

## `GET /v1/customer/bookings` — Full Contract

- **Request**: `page` (default 1), `page_size` (default 20) — real, simple offset pagination (no cursor, no total count returned).
- **Response**: `{"items": [...], "page": N, "page_size": N}` — no `total`/`has_more` field, so this client must infer "more pages exist" from `items.length === page_size` (a real, honest inference, not a fabricated total).
- **Item shape**: `booking_id`, `booking_number`, `status`, `issue_summary`, `city`, `preferred_date`, `selected_provider` (already customer-safe: `provider_name`/`rating`/`public_badges` only), `selected_price_option`, `selected_price_amount`.

## `GET /v1/customer/bookings/{bookingId}` — Full Contract

- **Response fields**: `booking_id`, `booking_number`, `status`, `assignment_status`, `assignment_message` (real, backend-authored customer-safe sentence — this client renders it verbatim, never re-deriving its own from `assignment_status` alone, since the backend's mapping is the single source of truth for that sentence), `preferred_date`, `preferred_time_window`, `city`, `address` (full snapshot), `issue_summary`, `selected_provider` (safe), `selected_price_option`, `selected_price_amount`, `payment_mode`. When a job exists: `job_status`, `scheduled_date`, `scheduled_time_window`.
- **Error shape (real, distinct convention from `final_records`'s router)**: not-found/ownership-mismatch returns HTTP 200 with
  `{"success": false, "error": {"code": "BOOKING_NOT_FOUND", "message": "..."}}`
  — an **object** `error` field (`{code, message}`), not the bare string
  `{"error": "..."}` `final_records` uses. This client's schema treats
  these as two distinct real shapes and must not conflate them.

## `GET /v1/customer/bookings/{bookingId}/tracking` — Full Contract

- **Response**: `{"booking_number", "status", "assignment_status", "assignment_message", "timeline": [...]}`.
- **Timeline item shape**: `{"event": "<customer-safe label>", "event_type"?: "<raw type, only on assignment-event-derived rows>", "created_at"?: "<ISO string, only on assignment-event-derived rows>"}`. The **first** item is always a synthetic, timestamp-less `{"event": "Booking confirmed", "status": "confirmed"}` row (no `event_type`/`created_at`) — a real, deliberate backend choice to always show a starting point even when the customer has no job yet.
- **Real event types mapped to customer-safe labels** (`_safe_event_label`, `customer_router.py:178-189`): `job_received`, `assignment_created`, `assignment_reassigned`, `assignment_cancelled`, `technician_accepted`, `technician_rejected`, `job_scheduled`. **Any other real `event_type` value is silently dropped** by the backend itself (`_safe_event_label` returns `None`, and the router's own loop skips appending when `label` is falsy) — this client never sees an unrecognized event type from this endpoint at all; there is no unknown-event case to handle for this specific field (though this client's schema still fails safe on a structurally malformed timeline item, per its own established discipline).

## `GET /v1/customer/bookings/{bookingId}/rating` — Full Contract

- **Response**: `{"review": null}` or `{"review": {"rating": number, "comment": string|null, "created_at": string|null}}`.
- Not-found/ownership-mismatch returns `{"review": null}` (no error field at all) — deliberately indistinguishable from "no review exists yet," which this sprint's review-boundary logic already only queries after independently confirming booking ownership via the detail fetch, so this ambiguity never surfaces as a false positive.

## Field Classification (per §7/§8's requested field list)

| Spec-requested field | Real backend equivalent | Classification |
|---|---|---|
| `booking_reference` | `booking_number` | `MATCHED`, `CUSTOMER_VISIBLE` |
| `provider_id`/`tenant_id` | Not directly exposed by this router's list/detail (only the already-safe `selected_provider` sub-object) | `INTERNAL_ONLY` — never rendered as raw text |
| `zone_id`/`city_tier` | None | `MISSING_BACKEND` — confirmed absent, unchanged finding since CUSTOMER-L5-09 |
| `sla_id` | None (only `preferred_time_window` free text, unchanged since L5-07) | `MISSING_BACKEND` |
| `quoted_price`/`negotiated_price` | `selected_price_option`/`selected_price_amount` | `MATCHED`, `CUSTOMER_VISIBLE` |
| `payment_status` | None beyond the fixed `payment_mode` string | `MISSING_BACKEND` — this sprint shows only the payment-timing policy, never a fabricated paid/unpaid status |
| `provider_acceptance_status` | Re-scoped to `assignment_status` (technician-level, not a separate tenant-level accept/reject) — see status-projection.md | `MATCHED` (renamed/re-scoped concept) |
| `job_id` | Present only in the detail-with-job case implicitly (job_status is inlined, no separate `job_id` field returned by this specific router) | `MISSING_CLIENT`-adjacent: this client does not need a raw `job_id` for anything it renders, so this is not a gap in practice |
| `cancelled_at`/`completed_at` | None as separate timestamp fields — only the current `status` string | `MISSING_BACKEND` — this sprint does not fabricate these timestamps |

## Action Availability (§29) — No Real `allowed_actions` Contract Exists

Confirmed absent by exhaustive grep (see baseline-verification.md and
action-contract.md). This sprint derives action visibility from real,
already-fetched fields only (`booking.status`, `job_status` presence,
review-existence) — never a fabricated authoritative list. See
`action-contract.md` for the complete, field-by-field derivation logic.
