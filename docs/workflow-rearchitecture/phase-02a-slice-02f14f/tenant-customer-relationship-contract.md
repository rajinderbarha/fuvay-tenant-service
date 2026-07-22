# Tenant-Customer Relationship Contract

## Disposition: ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP

A customer has an established relationship with a tenant when **at least one** row exists in
either:

- `Booking` where `tenant_id == principal tenant AND customer_id == requested customer`, **any
  status**.
- `field_ops.Job` where `tenant_id == principal tenant AND customer_id == requested customer`,
  **any status**.

## Why ANY status counts (not a filtered subset)

Direct model inspection confirms **neither `Booking` nor `field_ops.Job` carries a soft-delete,
test-scaffold, or "invalid" marker** (no `deleted_at`/`is_deleted` column exists on either model —
confirmed via `grep` across both model files; the only `deleted_at` columns in this general area
belong to unrelated models, `ServiceChecklistTemplate`/`ServiceChecklistItem`). Every real row in
either table therefore represents genuine historical contact between that customer and that
tenant — even a cancelled, rejected, or expired Booking still proves the customer engaged with
this specific tenant at some point. Filtering to "active or completed only" would require
inventing a distinction the schema does not support, and would arbitrarily exclude a customer who
legitimately interacted with the tenant but didn't complete a transaction (e.g., cancelled a
booking after finding a better time slot) — narrower than the evidence justifies.

## Rejected alternative dispositions

- `ACTIVE_OR_COMPLETED_RELATIONSHIP_ONLY` — would require filtering by status, which has no
  schema-level or product-documented basis for exclusion here.
- `NON_DELETED_RELATIONSHIP_ONLY` — vacuously identical to `ANY_HISTORICAL_...` since no
  soft-delete field exists to filter on.
- `CONFIRMED_BOOKING_OR_EXISTING_JOB_ONLY` — would incorrectly exclude a customer with only a
  cancelled/rejected Booking, even though that still proves genuine tenant contact; the ratified
  policy's own item 3 ("at least one existing same-tenant Booking") does not qualify this with a
  status restriction.

## Implementation

`SELECT ... LIMIT 1` existence checks only — no full row is ever returned to the caller (queries
select `.id` only), no other tenant's data or the customer's other relationships are ever
disclosed.
