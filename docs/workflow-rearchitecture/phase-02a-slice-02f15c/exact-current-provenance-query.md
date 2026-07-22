# Exact Current Provenance Query (Post-2F-15C)

## Four query sites, one pattern (actor now bound to Booking.customer_id)

### 1. `FieldOpsService._assert_tenant_customer_relationship` (app/engines/field_ops/service.py, ~line 152-166)
```python
select(Booking.id)
  .join(BookingStatusHistory, BookingStatusHistory.booking_id == Booking.id)
  .where(
      Booking.tenant_id == tenant_id,
      Booking.customer_id == customer_id,
      Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
      BookingStatusHistory.from_status.is_(None),
      BookingStatusHistory.changed_by_role == "customer",
      BookingStatusHistory.changed_by == Booking.customer_id,   # <- new this slice
  ).limit(1)
```

### 2. `BookingService.create_booking`'s relationship-requirement check (app/engines/booking/service.py, ~line 501-511)
```python
select(Booking.id)
  .join(BookingStatusHistory, BookingStatusHistory.booking_id == Booking.id)
  .where(
      Booking.tenant_id == tenant_id,
      Booking.customer_id == customer_id,
      Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
      BookingStatusHistory.from_status.is_(None),
      BookingStatusHistory.changed_by_role == "customer",
      BookingStatusHistory.changed_by == Booking.customer_id,   # <- new this slice
  ).limit(1)
```

### 3. `BookingService.convert_to_job`'s creator-check + independent-evidence query (app/engines/booking/service.py, ~line 918-943)
```python
# creator check -- returns a match-or-None (not a raw role string anymore)
select(BookingStatusHistory.id).where(
    BookingStatusHistory.booking_id == b.id,
    BookingStatusHistory.from_status.is_(None),
    BookingStatusHistory.changed_by_role == "customer",
    BookingStatusHistory.changed_by == b.customer_id,           # <- new this slice
).limit(1)

# independent-evidence query (excludes the current booking)
select(Booking.id)
  .join(BookingStatusHistory, BookingStatusHistory.booking_id == Booking.id)
  .where(
      Booking.tenant_id == b.tenant_id, Booking.customer_id == b.customer_id,
      Booking.id != b.id,
      Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
      BookingStatusHistory.from_status.is_(None),
      BookingStatusHistory.changed_by_role == "customer",
      BookingStatusHistory.changed_by == Booking.customer_id,   # <- new this slice
  ).limit(1)
```

### 4. `FieldOpsService.create_job`'s direct `booking_id` reference check (app/engines/field_ops/service.py, ~line 448-467)
```python
# creator check
select(_BSH.id).where(
    _BSH.booking_id == booking.id, _BSH.from_status.is_(None),
    _BSH.changed_by_role == "customer", _BSH.changed_by == booking.customer_id,  # <- new
).limit(1)

# independent-evidence query
select(_Booking.id)
  .join(_BSH, _BSH.booking_id == _Booking.id)
  .where(
      _Booking.tenant_id == tenant_id, _Booking.customer_id == booking.customer_id,
      _Booking.id != booking.id,
      _Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
      _BSH.from_status.is_(None), _BSH.changed_by_role == "customer",
      _BSH.changed_by == _Booking.customer_id,                  # <- new this slice
  ).limit(1)
```

## Predicate field inventory (per query)
| Field | Present | Purpose |
|---|---|---|
| `booking_id` (via JOIN or direct `.booking_id ==`) | Yes, all 4 | Ties the history row to the specific Booking |
| `tenant_id` | Yes, all 4 | Tenant scoping |
| `Booking.customer_id` (target) | Yes, all 4 | Scopes to the customer being evaluated |
| `from_status` | Yes, all 4 (`IS NULL`) | The exact creation-event marker |
| `to_status` | Not filtered explicitly (see `initial-status-semantics.md` for why this is safe) | — |
| `changed_by_role` | Yes, all 4 (`== "customer"`) | Actor held the customer role at creation time |
| `changed_by_user_id` (`changed_by`) | **Yes, all 4, new this slice** (`== Booking.customer_id` / `b.customer_id` / `booking.customer_id`) | Binds the ACTOR to the Booking's own customer — the fix this slice makes |
| Event/action field | N/A — no such column exists (see `booking-status-history-schema.md`, 2F-15B) | — |
| Ordering | None needed (`from_status IS NULL` is unique per Booking) | — |
| `.limit(1)` | Yes, all 4 | Existence check only |
| Duplicate-row behavior | If two `from_status IS NULL` rows somehow existed for one Booking, either would satisfy the query if it matched; not reachable via any writer path in this codebase (see `conflicting-creation-history-matrix.csv`) | — |
| Missing-row behavior | JOIN/filter produces no match; falls through to independent-Job-evidence check; fails closed if absent too | — |

## What changed
Before this slice, `changed_by_role == "customer"` was the ONLY actor-identity filter. This proved the ACTING USER held the customer role, but never proved that acting user WAS the specific Booking's own customer. The new `changed_by == Booking.customer_id` filter closes this: an actor can now only satisfy the predicate if they are BOTH role=customer AND the literal customer this Booking belongs to.
