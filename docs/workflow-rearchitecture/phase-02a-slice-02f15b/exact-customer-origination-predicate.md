# Exact Customer-Origination Predicate

## The query (three equivalent instances, one pattern)
All three provenance-dependent call sites (`FieldOpsService._assert_tenant_customer_relationship`, `BookingService.create_booking`'s relationship check, `BookingService.convert_to_job`'s / `FieldOpsService.create_job`'s creator-role check) use the same shape:

```python
select(Booking.id)
  .join(BookingStatusHistory, BookingStatusHistory.booking_id == Booking.id)
  .where(
      Booking.tenant_id == tenant_id,
      Booking.customer_id == customer_id,
      Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
      BookingStatusHistory.from_status.is_(None),        # <- the creation-event filter
      BookingStatusHistory.changed_by_role == "customer",
  ).limit(1)
```

(`convert_to_job`/direct `create_job`'s variant reads `BookingStatusHistory.changed_by_role` directly for the ONE Booking being acted on, filtered the same way: `BookingStatusHistory.booking_id == b.id, BookingStatusHistory.from_status.is_(None)`.)

## Predicate breakdown
| Filter | Purpose |
|---|---|
| `Booking.tenant_id == tenant_id` | Scope to the acting tenant (no cross-tenant leakage) |
| `Booking.customer_id == customer_id` | Scope to the specific customer |
| `Booking.status.in_(QUALIFYING_BOOKING_STATUSES)` | Low-trust statuses (draft/pending/rejected/cancelled/expired/voided) excluded — see `legacy-booking-provenance.md` from 2F-15A |
| `BookingStatusHistory.from_status.is_(None)` | **The exact creation-event marker** — matches exactly the one row written at Booking creation, never any other transition |
| `BookingStatusHistory.changed_by_role == "customer"` | The actor who performed that exact creation event was a customer |
| `.limit(1)` | Existence check only, no ordering needed (at most one row can ever match `from_status IS NULL` per booking) |

## Behavior under each condition
- **Multiple history rows exist for the Booking** (the normal case — creation + confirm + cancel, etc.): irrelevant to the outcome, because only the ONE row with `from_status IS NULL` can pass the filter; all other rows are excluded regardless of their `changed_by_role`.
- **No history exists at all**: the `JOIN` produces zero rows for that Booking — it simply cannot appear in the result set. Falls through to the independent-Job-evidence check; fails closed if that's also absent.
- **The creation row's `changed_by_role` is NULL or any value other than `"customer"`**: excluded by the equality filter (SQL `NULL = 'customer'` and `'tenant_owner' = 'customer'` both evaluate to false/unknown) — falls through, fails closed if no independent evidence.

## Classification

**EXACT_CREATION_EVENT_BY_CUSTOMER.**

This is not `ANY_HISTORY_EVENT_BY_CUSTOMER` — a customer-authored cancellation, reschedule-accept, or any other later transition row has `from_status` populated with a real value (never `NULL`, see `creation-event-provenance.md`/`later-customer-activity-test-matrix.csv`), so it can never satisfy `from_status.is_(None)` and can never be mistaken for the creation event, however many such rows exist.

It is also not `EARLIEST_HISTORY_EVENT_BY_CUSTOMER` (which would require ordering by timestamp and trusting insertion order/clock skew) — the predicate uses a structural marker (`from_status IS NULL`) written atomically in the same transaction as the Booking's own creation, not a timestamp comparison.
