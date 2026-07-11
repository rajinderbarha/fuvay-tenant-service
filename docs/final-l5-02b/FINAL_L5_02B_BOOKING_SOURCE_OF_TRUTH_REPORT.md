# FINAL-L5-02B — Booking Source-of-Truth Decision

## Decision: **MODEL_D** (with a naming correction)

`home_service_booking_drafts` → `service_bookings` directly; `bookings` is a legacy/other-vertical domain table, not part of the Home Services lifecycle at all (not "legacy Home Services", but genuinely a different engine's table).

This matches Model D's shape exactly except the mission's illustrative name `booking_drafts` should be read as `home_service_booking_drafts` (the real table; `booking_drafts` does not exist in the schema).

## Evidence (not row-count-only, per the mission's explicit rule)
1. **Source-code trace**: `app/engines/final_records/creation_service.py` — `HomeServiceFinalCreationService.finalize()` constructs `ServiceBooking(draft_id=draft.id, ...)` then `ServiceJob(booking_id=booking.id, ...)` where `booking` is the just-created `ServiceBooking` instance. `Booking` (the `bookings`-table model) is never imported or referenced anywhere in this service.
2. **Endpoint trace**: every customer-facing booking read endpoint (`home_service_assignment/customer_router.py`) imports and queries `from app.engines.final_records.models import ServiceBooking, ServiceJob` exclusively — 5 separate query sites, zero references to a generic `Booking` model.
3. **Live data shape**: post-reset row counts — `bookings=0`, `service_bookings=5`, matching the 5 canonically seeded jobs exactly (1:1).
4. **Live API behavior**: `GET /v1/customer/bookings` as Customer One returns exactly the 5 seeded records with `booking_number` values `L501-BK-0001..0005`, verified both via direct API call and real Chromium browser rendering this sprint.

## Canonical answers (mission's required decision fields)
| Field | Answer |
|---|---|
| Canonical customer-facing record | `service_bookings` |
| Canonical write path | `POST .../booking-drafts/{id}/confirm` → `HomeServiceFinalCreationService.finalize()` |
| Canonical list/detail source | `GET /v1/customer/bookings`, `GET /v1/customer/bookings/{id}` (both query `ServiceBooking`) |
| Canonical tracking source | `GET /v1/customer/bookings/{id}/tracking` (joins `ServiceBooking` + `ServiceJob`) |
| Cancellation owner | `service_bookings.status` (set to `cancelled`); no dedicated post-confirmation customer cancel endpoint currently exists — see Backend Alignment Report |
| Review owner | `service_bookings` (via `POST/GET .../rating`, not the separate generic `customer_reviews` engine — the router's own docstring explains this deliberate choice) |
| `service_jobs` relationship | `service_jobs.booking_id → service_bookings.id`, created in the same transaction, 1:1 |
| Legacy table status | `bookings` — real table, real purpose for other verticals (per the multi-vertical catalog architecture), **not legacy-for-Home-Services, simply not-this-domain** |
| Projection/synchronization rule | None needed — there is no dual-write or projection; `service_bookings` is written once, directly, never copied to or from `bookings` |
| Transaction boundary | Single `db.commit()` after `finalize()` creates both `service_bookings` and `service_jobs` |
| Idempotency rule | `ConfirmationLockService` — one `CustomerBookingConfirmation` lock row per draft; retries return the existing booking rather than creating a new one |

## Result
**RESOLVED** — no `NOT_READY_FINAL_L5_02B_BOOKING_SOURCE_UNRESOLVED`. This reconfirms, with fresh independent evidence gathered this sprint (not by re-citing FINAL-L5-01D's conclusion from memory alone), the same decision made in FINAL-L5-01D.
