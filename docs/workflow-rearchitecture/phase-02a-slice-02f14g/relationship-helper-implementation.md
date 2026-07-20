# Relationship Helper Implementation (Updated)

## Changes to `_assert_tenant_customer_relationship`

- Added `QUALIFYING_BOOKING_STATUSES = (BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING,
  BS.IN_PROGRESS, BS.COMPLETED, BS.CONVERTED_TO_JOB)` and filters the Booking query with
  `Booking.status.in_(QUALIFYING_BOOKING_STATUSES)`.
- Added `or_(Job.booking_id.isnot(None), Job.parent_job_id.isnot(None))` to the Job query.
- Both filters are applied **inside the SQL query itself** (not post-filtered in Python) — a
  non-qualifying row is never even fetched, let alone returned.

## Preserved (unchanged)

- **Read-only**: no `db.add`/`db.flush`/write of any kind — confirmed, only `select()` statements.
- **Tenant-scoped and customer-scoped**: both queries still filter on `tenant_id` and
  `customer_id` first.
- **Uniform rejection**: still a single `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` (422) regardless
  of which of the now-multiple non-qualifying reasons applies (wrong tenant, wrong status, wrong
  lineage, or no record at all) — the caller cannot distinguish any of these cases.
- **Executed before Job persistence**: unchanged position in `create_job`'s validation order.
- **No new table, migration, or role/permission**: confirmed — only an existing constants import
  (`BS` from `app.engines.booking.constants`, already used elsewhere in this file) and a new
  `or_` import from `sqlalchemy` (already a dependency of this file).
- **No relationship record written**: confirmed, still purely read-only.
- **No other tenant's data used**: the `tenant_id` filter is always the principal tenant's own ID.
- **No relationship details returned**: the helper still only returns `None` or raises — it never
  returns the matched Booking/Job row or any of its fields to the caller.
