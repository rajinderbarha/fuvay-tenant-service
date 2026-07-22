# Trusted Customer Creation Predicate

## Requirements checklist
| Condition | Satisfied? | How |
|---|---|---|
| `history.booking_id == booking.id` | Yes | JOIN condition (or direct `.booking_id ==` in the single-booking checks) |
| `history.from_status IS NULL` | Yes | Explicit filter, all 4 sites |
| `history.changed_by_role == canonical customer role` | Yes | Explicit filter `== "customer"`, all 4 sites |
| `history.changed_by_user_id == booking.customer_id` | **Yes, added this slice** | `BookingStatusHistory.changed_by == Booking.customer_id` (or `b.customer_id`/`booking.customer_id` in the single-booking variants) |
| `changed_by_user_id references a real canonical customer account` | Partially — see below | Not independently re-verified at query time (would require an extra JOIN to `User`); instead relied upon transitively: `changed_by` is only ever set to `self.actor_id` from an authenticated `UserContext`, and `create_booking`'s own router only accepts `role == "customer"` self-bookings through `get_current_user`, which requires a real, resolvable JWT-authenticated user. There is no code path where `changed_by` is set to an arbitrary/unauthenticated value. |
| `The customer account is active and non-deleted where those fields exist` | Not re-checked at query time for THIS historical fact (see `known-limitations.md`) — checked at the time of the CURRENT action (e.g. `create_job`'s own `customer_id` validation block independently verifies the CURRENT customer_id's account is active/non-deleted via a `User` lookup) | See `actor-customer-binding.md` |
| `to_status equals an actual valid initial Booking status` | Not separately filtered in the query, but proven structurally safe — see `initial-status-semantics.md` | `create_booking` is the only writer of a `from_status IS NULL` row, and it always writes `to_status = booking.status` at creation time (`PENDING_CONFIRMATION` or `PENDING`, the only two initial statuses observed) |
| `The history row represents creation rather than a later transition` | Yes | `from_status IS NULL` is proven unique to the creation event (see `exact-current-provenance-query.md`, `booking-status-history-schema.md` from 2F-15B) |

## Final predicate classification

**CUSTOMER_CREATION_EVENT_WITH_ACCOUNT_VALIDATION**

This is stronger than `EXACT_INITIAL_CUSTOMER_EVENT` (2F-15B's classification) because it now additionally binds the acting user's identity to the Booking's own customer, not merely proving "a customer created some booking with this from_status IS NULL marker." It falls short of a hypothetical `UNIQUE_CUSTOMER_CREATION_EVENT` label only in the sense that database-level uniqueness of the `from_status IS NULL` row per Booking is a code-path argument, not a schema constraint (documented, not fixed, in `known-limitations.md` — no writer path in this codebase can produce a second such row, so this is not a live risk).

The account-validation component is satisfied transitively (via `get_current_user`'s authentication requirement) rather than by an explicit re-query of the `User` table inside the provenance check itself — this is a deliberate design choice to avoid adding a new join to every relationship-evidence query for a condition that is already guaranteed at write time. Where the CURRENT action also independently validates a customer_id's account state (e.g. `create_job`'s own `customer_id` block), that validation covers the account being acted upon right now, not the historical creation actor — this distinction is documented, not glossed over.

## Role equality alone is never sufficient
Per the mission's explicit requirement ("do not accept role equality without actor-to-customer equality"): every one of the 4 query sites now requires BOTH `changed_by_role == "customer"` AND `changed_by == Booking.customer_id` (or the single-booking equivalent) — role equality alone can no longer satisfy any of these checks.
