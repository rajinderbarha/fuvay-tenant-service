# CUSTOMER-L5-11 — Contract Matrix

Verified by direct reading of `app/engines/home_service_booking/service.py`,
`customer_router.py`, `constants.py`, `app/engines/final_records/creation_service.py`,
`idempotency.py`, `models.py`, `number_service.py`, `constants.py`,
`customer_router.py`, `app/exceptions.py` — cross-checked by an
independent background research pass.

## Endpoints Used

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/customer/home-services/booking-drafts/{draftId}/summary` | Real, customer-facing review-summary retrieval (already documented by CUSTOMER-L5-10 for this sprint's benefit). Merges into `draft.booking_summary`; returns `ready_for_confirmation`. |
| `POST` | `/v1/customer/home-services/booking-drafts/{draftId}/confirm` | Real, idempotent canonical booking creation. Internally runs the real preflight (`mark_ready_for_confirmation`) then the real transaction (`HomeServiceFinalCreationService.finalize`). |
| `GET` | `/v1/customer/my-activity/bookings/{bookingId}` | Real canonical booking retrieval, customer-ownership enforced, includes the linked `ServiceJob`. |

## `POST /{draftId}/summary` — Full Contract

- **Request**: none beyond `draftId`.
- **Response**: `{"booking_summary": {...merged...}, "draft_status": "..."}`.
  `booking_summary` (cumulative, merged across every prior sprint's writes
  to it) includes: `offering_name`, `offering_slug`, `issue_summary`,
  `address` (the draft's `address_snapshot`), `city`, `zipcode`,
  `preferred_date`, `preferred_time_window`, `price_estimate` (=
  `draft.price_snapshot`), `selected_provider` (internal-score-stripped —
  server-side, confirmed by direct reading of `build_booking_summary`),
  `serviceability` (`{serviceable: bool, status: str}`),
  `ready_for_confirmation` (bool), plus everything `confirm-price-choice`
  (L5-10) already wrote (`selected_tenant_id`, `selected_provider_name`,
  `selected_zipcode`, `selected_price_tier`, `customer_offer`,
  `allowed_offer_min/max`, `platform_fee_amount`, `payment_mode`).
- **`ready_for_confirmation`** is `True` only when `serviceability_status
  == "serviceable"` AND `selected_tenant_id` is set AND
  `selected_price_tier` is one of `"low"|"mid"|"high"` — the exact real
  precondition this sprint's review screen uses to decide whether to show
  the "Confirm booking" action at all.
- **Repeatable**: yes — merges on top of the existing `booking_summary`
  each time, safe to call multiple times (e.g., on every review-screen
  mount, for a fresh summary).

## `POST /{draftId}/confirm` — Full Contract

- **Request**: no body; reads the `Idempotency-Key` HTTP header (optional
  — passed through and stored for audit/traceability, but **not** the
  actual functional dedup mechanism — see idempotency-contract.md).
- **Response** (200, both first-time and idempotent-retry cases, same
  envelope shape):
  ```json
  {
    "idempotent": false,
    "booking_number": "BK-20260713-000042",
    "booking_id": "…",
    "job_number": "JOB-20260713-000042",
    "job_id": "…",
    "status": "pending_assignment",
    "booking_status": "confirmed",
    "confirmation_id": "…",
    "selected_provider_tenant_id": "…",
    "selected_price_option": "mid",
    "selected_price_amount": 690.0,
    "payment_mode": "customer_pays_provider_directly"
  }
  ```
  On an idempotent retry (draft already confirmed), the response is
  smaller: `{"idempotent": true, "booking_number", "booking_id",
  "confirmation_id"}` only — no `job_number`/`job_id`/`status` fields.
  This client's schema treats all of these as optional except the three
  always-present fields, and branches its own UI logic on `idempotent`
  where relevant (mainly for analytics/logging, not for user-facing
  differences — the resulting confirmation screen looks identical either
  way, since both cases end with a real, fetchable booking).
- **Internal sequencing** (not directly observable by the client, but
  documented for completeness): calls `mark_ready_for_confirmation`
  first (skipped if already confirmed) — real preflight, real
  `ServiceOSException`s with proper 422 status and specific codes — then
  `HomeServiceFinalCreationService.finalize()` — real transaction, whose
  own three guard `ValueError`s are **not** cleanly mapped (see Error
  Contract below).

## `GET /v1/customer/my-activity/bookings/{bookingId}` — Full Contract

- **Request**: none beyond `bookingId` (a real database UUID, distinct
  from `booking_number`).
- **Response**: `ServiceBooking.to_dict()` (see negotiated data below)
  plus a `job` key (`ServiceJob.to_dict()` or `null`).
- **Quirk**: not-found and access-denied both return **HTTP 200** with a
  body of `{"error": "FINAL_BOOKING_NOT_FOUND"}` or
  `{"error": "FINAL_ACCESS_DENIED"}` — not a 404/403 status. This client's
  schema/parsing must check for this `error` shape explicitly (a
  `z.union` of the success shape and this error shape), not rely on HTTP
  status for these two specific failure modes.

## `ServiceBooking` Fields — Classification

| Field | Classification | Rendered? |
|---|---|---|
| `id` | Internal identifier | Not displayed as text; used only as the fetch key |
| `booking_number` | `CUSTOMER_VISIBLE` | Yes — the real booking reference (format `BK-YYYYMMDD-NNNNNN`) |
| `draft_id` | Internal | Not displayed |
| `customer_id` / `tenant_id` | Internal | Not displayed |
| `category_id` / `offering_id` | Internal | Not displayed directly (service name comes from `booking_summary.offering_name`, fetched separately via `/summary` before confirmation — not re-fetched after) |
| `customer_name` / `customer_phone` | `CUSTOMER_VISIBLE`, `SENSITIVE` | Not re-displayed on the confirmation screen (the customer already knows their own name/phone; no product need to echo it back) |
| `city` / `zipcode` | `CUSTOMER_VISIBLE` | Yes — part of the address summary |
| `address_snapshot` | `CUSTOMER_VISIBLE` | Yes — the real, already-approved (L5-07) address fields |
| `preferred_date` / `preferred_time_window` | `CUSTOMER_VISIBLE` | Yes — the SLA/schedule summary |
| `price_snapshot` | Mixed | Only `selected_price_option`/`selected_price_amount`/`payment_mode` rendered (see below); the nested `price_options` low/mid/high trio and `platform_fee_*` fields are not re-rendered on this screen (already shown and chosen in L5-09/L5-10) |
| `provider_snapshot` | Mixed, **requires client-side stripping** | Only `provider_name`/`public_badges`/`rating`/`customer_visible_reason` rendered — `internal_score`/`matching_score_snapshot` **must be stripped client-side** (see baseline-verification.md finding #7 and security-review.md) |
| `issue_summary` | `CUSTOMER_VISIBLE` | Yes |
| `issue_details` | Internal-shaped JSON, not customer-safe to render raw | Not rendered (mirrors every prior sprint's "no raw diagnostic payload" discipline) |
| `status` | `CUSTOMER_VISIBLE` | Yes — drives the next-step guidance copy (`"pending_assignment"` is the real, only-observed initial value) |
| `assignment_status` | `CUSTOMER_VISIBLE` | Not separately rendered this sprint — `status` alone is sufficient for the real initial state; `assignment_status` becomes relevant once a later sprint builds the assignment-status timeline |
| `failure_reason` | `CUSTOMER_VISIBLE` when present | Not applicable at initial creation (always `null` for a freshly created booking) |

`price_snapshot.selected_price_option`/`selected_price_amount` (written by
`finalize()`, `creation_service.py:114-119`) are the exact real
tier/amount the customer confirmed in L5-10 — this is the canonical,
post-booking source of truth for "what price was agreed," carried forward
from the draft's ephemeral `booking_summary` into the permanent booking
record.

## Error Contract

| Backend error_code | HTTP | Source | This sprint's handling |
|---|---|---|---|
| `SERVICE_NOT_AVAILABLE_IN_AREA` | 422 | `mark_ready_for_confirmation` | Real, clean error — mapped to a "service window/serviceability" section-specific message, routes back to AddressSelection |
| `ERR_NO_PROVIDER_AVAILABLE` (`HOME_BOOKING_NO_PROVIDER_AVAILABLE`) | 422 | `mark_ready_for_confirmation` | Same generic unavailable-provider handling established since L5-08 |
| `INVALID_SELECTED_PRICE_OPTION` | 422 | `mark_ready_for_confirmation` | Routes back to the Bargain screen to re-choose a tier |
| `SELECTED_PROVIDER_NOT_BOOKABLE` | 422 | `mark_ready_for_confirmation` | Routes back to ProviderPreview to re-match |
| `ERR_REQUIRED_FIELD_MISSING` | 422 | `mark_ready_for_confirmation` | Generic "your booking isn't ready yet" message (this client's own preflight-precondition check, mirroring L5-09/10's `evaluatePricingPreflight` pattern, should prevent reaching this in practice) |
| `FINAL_DRAFT_NOT_FOUND` / `FINAL_DRAFT_NOT_READY` / `FINAL_ACCESS_DENIED` | **Unmapped — surfaces as generic 500 `INTERNAL_ERROR`** | `finalize()`'s own `ValueError` guards, uncaught by any specific handler | Treated as a generic "something went wrong, please check your booking status" — this client cannot distinguish these three real reasons at all (a real, disclosed backend robustness gap, not fixable from the frontend — see known-gaps.md) |
| `FINAL_BOOKING_NOT_FOUND` / `FINAL_ACCESS_DENIED` | 200 with `{"error": ...}` body | `GET /bookings/{id}` | Parsed via the schema's error-shape branch, not HTTP status |

No new error codes are introduced by this sprint's own client code — all
mapping is to real, backend-confirmed codes (or the documented absence of
one, in `finalize()`'s case).
