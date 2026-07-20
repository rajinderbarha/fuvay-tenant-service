# CUSTOMER-L5-12 — Detail Contract

## Endpoint

`GET /v1/customer/bookings/{bookingId}` — see contract-matrix.md for the
full field list and the real, distinct `{"success": false, "error": {code,
message}}` error shape (as opposed to CUSTOMER-L5-11's other endpoint's
bare-string `{"error": "..."}` shape).

## Sections Rendered (per §18)

| Section | Source field(s) | Real or fallback |
|---|---|---|
| Booking reference | `booking_number` | Real |
| Current status | `status` (via the centralized registry) + `assignment_message` (real, backend-authored sentence, rendered verbatim) | Real |
| Service | `issue_summary` | Real (omitted entirely if absent) |
| Address | `address` (full snapshot) with a `city`-only fallback | Real |
| Service window | `scheduled_time_window` (when a job exists) falling back to `preferred_time_window`, falling back to a real "no schedule set" copy | Real |
| Provider | `selected_provider.provider_name`/`.rating` | Real (already customer-safe, no client-side stripping needed — unlike CUSTOMER-L5-11's other endpoint) |
| Price | `selected_price_amount` | Real |
| Payment policy | Static copy (real, fixed `payment_mode` value is always `"customer_pays_provider_directly"` — this sprint does not re-render the raw string, it renders the same established policy sentence CUSTOMER-L5-09/10/11 already use) | Real |
| Timeline | Separate `GET .../tracking` call — see timeline-contract.md | Real |
| Actions | Informational rows only — see action-contract.md | Honest, non-interactive |

## No Coordinates, No Raw Logging

`address`'s real fields never include latitude/longitude (confirmed — the
`address_snapshot` shape has never included coordinates since
CUSTOMER-L5-09's original `_resolve_address_snapshot` finding). No
`logger.*` call anywhere in `features/bookings/` passes the address
object or any of its fields — verified by grep.

## Stale-State Handling

This screen fetches fresh on every mount (`staleTime: 0` on both the
detail and tracking queries) — there is no cached "last known status"
displayed as if current; every visit re-derives the real, current state
from the backend.

## Error Handling

- Not-found/ownership-mismatch (`{"success": false, "error": {...}}`) is
  parsed and surfaced as a `not_found`-category `ApiError`, rendering
  `bookings.detail.notFoundTitle`/`notFoundDescription` with **no** retry
  action (retrying a genuine not-found/ownership-mismatch cannot succeed).
- Any other failure (network/validation/server) renders
  `bookings.detail.loadErrorTitle`/`loadErrorDescription` **with** a retry
  action.

## Test Coverage

`booking-detail-schema.test.ts` (4 tests) covers the real found-with-job,
found-without-job, the real error shape, and malformed-payload cases.
