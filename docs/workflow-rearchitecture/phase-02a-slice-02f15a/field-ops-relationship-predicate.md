# field_ops Relationship Predicate — Revision History

| Slice | Predicate |
|---|---|
| 2F-14F | Any Booking (any status) or Job for the customer+tenant establishes relationship. |
| 2F-14G | Tightened to `QUALIFYING_BOOKING_STATUSES` (CONFIRMED or later) for Bookings; Jobs restricted to those with a non-null `booking_id`/`parent_job_id` (excluding generic manually-created jobs). Self-confirmation bootstrap risk explicitly disclosed as out of scope. |
| **2F-15A** | **Additionally requires the qualifying Booking's own creation-history row show `changed_by_role == "customer"`.** Closes the disclosed 2F-14G bootstrap risk: a provider-created qualifying Booking can no longer, by itself, establish relationship authority. |

## Current predicate (2F-15A)
A tenant may manually create a `field_ops.Job` for a customer when, for that same tenant:
- A Booking exists with `status IN QUALIFYING_BOOKING_STATUSES` **and** its creation-history row (`from_status IS NULL`) has `changed_by_role == "customer"`, **or**
- A `field_ops.Job` exists with a non-null `booking_id` or `parent_job_id` for that customer (source-derived — proves the relationship was already established through an audited pipeline).

No new column, migration, role, or permission was introduced to implement this — it reads the pre-existing `BookingStatusHistory.changed_by_role` value.
