# Ratified Customer Authority Policy (Implemented)

## Secure interim policy (as ratified, verbatim)

A tenant may manually create a `field_ops.Job` for a customer only when one of these same-tenant
relationships already exists:

1. The request references a valid same-tenant `CONFIRMED` Booking owned by that customer.
2. The request references a valid same-tenant parent `field_ops.Job` owned by that customer.
3. The customer has at least one existing same-tenant Booking.
4. The customer has at least one existing same-tenant `field_ops.Job`.

A completely unrelated global customer account must not be selectable for a new standalone
manual Job.

## Implementation

`FieldOpsService._assert_tenant_customer_relationship(tenant_id, customer_id)` — a read-only
helper querying only `Booking` and `Job` (no new table, no migration):

```python
async def _assert_tenant_customer_relationship(self, tenant_id, customer_id) -> None:
    br = await self.db.execute(select(Booking.id).where(
        Booking.tenant_id == tenant_id, Booking.customer_id == customer_id).limit(1))
    if br.scalar_one_or_none():
        return
    jr = await self.db.execute(select(Job.id).where(
        Job.tenant_id == tenant_id, Job.customer_id == customer_id).limit(1))
    if jr.scalar_one_or_none():
        return
    raise ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED", ..., status_code=422)
```

Called from `create_job` **only** when `customer_id` is supplied AND neither `booking_id` nor
`parent_job_id` is supplied (rules 1/2 above are already intrinsically proven by the
already-existing booking/parent tenant+customer cross-checks — no redundant query is issued for
those modes, confirmed by
`TestBookingParentModesUnaffectedByRelationshipGuard`).

## Long-term target

`TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING` — explicitly out of scope, not begun. See
long-term-customer-directory-target.md.

## What was NOT built (explicitly out of scope, confirmed)

No customer-contact table, invitation flow, OTP/consent workflow, customer-directory UI, or
migration was created. The relationship predicate uses only the two tables that already existed.
