# Initial Status Semantics

## Single writer, single initial status
Repo-wide search (`grep -rn "Booking(" app/ scripts/`) confirms exactly ONE construction site for the `Booking` model in the entire application codebase: `app/engines/booking/service.py::BookingService.create_booking`, line 595:

```python
booking = Booking(
    ...
    status=BS.PENDING_CONFIRMATION,
    ...
)
```

The corresponding creation-history write (line ~624) is: `_write_history(booking, None, booking.status, ...)` — `to_status` is therefore always `BS.PENDING_CONFIRMATION`, for every creation mode.

## Per creation mode
| Mode | Initial `Booking.status` | History `from_status` | History `to_status` | Actor role | Actor ID | Customer ID |
|---|---|---|---|---|---|---|
| Customer self-booking | `PENDING_CONFIRMATION` | `NULL` | `PENDING_CONFIRMATION` | `customer` | The authenticated customer's own user ID | Same as actor ID (server-derived, router-enforced) |
| Provider-assisted | `PENDING_CONFIRMATION` | `NULL` | `PENDING_CONFIRMATION` | `tenant_owner` | The tenant_owner's user ID | The named customer (validated to be a real active account, and — since Slice 2F-15/2F-15A — required to have prior relationship evidence) |
| Platform/internal | N/A — no separate creation code path exists; a platform user would have to authenticate through the same `create_booking` router and would follow the "provider-assisted" mode above if they held `BOOKING_CREATE` (only `customer`/`tenant_owner` are granted this permission; `super_admin` is not, so no platform-initiated creation path currently exists) | — | — | — | — | — |
| Legacy compatibility creation | None found — no separate/legacy Booking-creation method exists in the current codebase | — | — | — | — | — |
| Seed/test creation | Test fixtures construct `Booking`/`BookingStatusHistory` mock objects directly (never via the real ORM against a live database in this repo's test suite) — not a runtime code path | — | — | — | — | — |

## Requirement: one exact `to_status`, not an arbitrary set
Since there is exactly one writer and it always writes the same `to_status`, this slice adopts the STRICTEST possible rule: **a trusted creation row must have `to_status == BS.PENDING_CONFIRMATION`** (not merely "some initial-looking value"). This is not separately enforced as an additional SQL filter in the 4 provenance queries (see `exact-current-provenance-query.md`) because it is already guaranteed by construction — there is no writer path that could produce a `from_status IS NULL` row with any other `to_status`. If a future creation path is ever added with a different initial status, this document's claim would need to be re-verified, and the provenance queries would need an explicit `to_status == BS.PENDING_CONFIRMATION` filter added defensively at that time — flagged here as a forward-looking note, not a current gap.
