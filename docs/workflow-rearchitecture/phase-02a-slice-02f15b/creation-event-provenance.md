# Creation-Event Provenance

## Atomicity
`create_booking` (`app/engines/booking/service.py`, ~line 619-629):

```python
self.db.add(booking)
await self.db.flush()

# Step 5 — Immutable history
await self._write_history(
    booking, None, booking.status,
    "Booking created — awaiting confirmation", ...)
```

Both `db.add(booking)` and the history write happen within the same request/transaction, before any `db.commit()` in the surrounding request lifecycle (the session's commit boundary is managed by the FastAPI dependency, outside this method) — there is no window where the Booking exists without its creation-history row, and no separate code path creates a Booking without immediately writing this row.

## Actor identity
`_write_history`'s `changed_by=self.actor_id, changed_by_role=self.actor_role` (line 95) — `self.actor_id`/`self.actor_role` are set once, at `BookingService.__init__`, from the authenticated request's `UserContext` (passed down from the router's `Depends(get_current_user)` / `require_tenant_mutation_permission(...)`). There is no code path where these are set to anything other than the actual authenticated caller — server-derived, not client-suppliable.

## Two creation modes
- **Customer self-service**: the customer calls `POST /v1/bookings` themselves. `self.actor_role == "customer"`, `self.actor_id == <the customer's own user id>`. The creation-history row's `changed_by_role == "customer"` and `changed_by == <that same customer's id>` — the customer created their own booking.
- **Provider-assisted**: a `tenant_owner` calls the same endpoint on the customer's behalf (dual-persona route, see `exact-booking-route-reconciliation.csv`). `self.actor_role == "tenant_owner"`, `self.actor_id == <the tenant_owner's user id>`. The creation-history row's `changed_by_role == "tenant_owner"` — correctly recorded as provider-created, NOT customer-created, however the Booking's own `customer_id` field is still set to the actual customer.

## Confirmation is never confused with creation
`confirm_booking` always reads `from_status = b.status` (the Booking's real current status, e.g. `PENDING_CONFIRMATION`) before writing — never `None`. A confirmation row can never satisfy `from_status IS NULL` and can never be read as a creation event, regardless of who performs the confirmation.

## Cancellation is never confused with creation
Identical reasoning: `cancel_booking` reads `from_status = b.status` before writing. A customer cancelling their own booking (or a provider cancelling on the customer's behalf) writes a row with `from_status` populated — never mistaken for creation.

## The narrowest trustworthy predicate
`from_status IS NULL AND changed_by_role == "customer"` is deliberately the narrowest predicate available in the existing schema — it does not use `to_status` (which is always non-NULL and therefore not a useful creation discriminator on its own), does not use timestamp ordering (fragile to clock skew or insertion-order assumptions), and explicitly does **not** treat `Booking.status == CONFIRMED` as origin evidence (status describes the Booking's CURRENT lifecycle position, which is affected by later provider/customer actions and proves nothing about who created it).
