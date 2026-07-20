# Supported Creation-Mode Policy (Post-Implementation)

## BOOKING-REFERENCED CREATION — `BOOKING_RELATIONSHIP_ESTABLISHED`

Allowed when `booking_id` is supplied, the Booking belongs to the principal tenant, is
`CONFIRMED`, its customer/service match the request, and no Job already exists for it (all
pre-existing from Slices 2F-14D/14E, unmodified). **The Booking itself proves the tenant/customer
relationship** — confirmed via `test_booking_referenced_creation_does_not_query_relationship`,
which proves no extra relationship query is issued for this mode.

## PARENT-JOB-DERIVED CREATION — `PARENT_JOB_RELATIONSHIP_ESTABLISHED`

Allowed when `parent_job_id` is supplied, the parent belongs to the principal tenant, its
customer matches the request, and (for CONSULTATION→REPAIR) type/status/duplicate rules pass
(all pre-existing from Slices 2F-14D/14E, unmodified). **The parent Job itself proves the
relationship** — confirmed via `test_parent_derived_creation_does_not_query_relationship`.

## STANDALONE MANUAL CREATION — `PRIOR_TENANT_RELATIONSHIP_REQUIRED` / `UNRELATED_CUSTOMER_REJECTED`

Allowed only when: neither `booking_id` nor `parent_job_id` is supplied, the requested
`customer_id` is a real, active, non-deleted `customer`-role account, `service_type_id` belongs
to the principal tenant and is active, **and** `_assert_tenant_customer_relationship` finds at
least one existing same-tenant Booking or Job for that customer.

- Customer with a prior same-tenant Booking or Job → `PRIOR_TENANT_RELATIONSHIP_REQUIRED`
  (satisfied) → creation succeeds.
- Customer with no same-tenant Booking/Job at all (whether completely unrelated to any tenant, or
  known only to a different tenant) → `UNRELATED_CUSTOMER_REJECTED`
  (`CUSTOMER_TENANT_RELATIONSHIP_REQUIRED`, 422) — both cases produce the **identical** error,
  never disclosing which applies.

## No customer_id supplied at all

Not affected by this slice — a Job may still be created with `customer_id=None` (no relationship
check runs, since there is no customer to validate a relationship for).
