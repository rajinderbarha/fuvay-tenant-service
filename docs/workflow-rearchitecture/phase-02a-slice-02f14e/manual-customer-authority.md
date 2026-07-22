# Manual Customer Authority

## Disposition: PRODUCT_DECISION_REQUIRED (not fixed with an invented relationship rule)

## Investigation

Searched this entire codebase for any existing tenant/customer relationship model:

- **Tenant customer/contact table**: none exists.
- **Lead/customer relationship**: none exists.
- **Provider customer directory**: none exists.
- **Tenant-created customer/contact record**: none exists — all `customer`-role accounts are
  platform-wide `auth.User` rows (confirmed in Slice 2F-14C: `User.tenant_id` is nullable and
  never populated for customers).
- **Customer invitation**: no such flow exists anywhere in this codebase.
- **Explicit customer-to-tenant association table**: none exists.
- **Booking customer relationship**: exists (`Booking.customer_id` + `Booking.tenant_id`) — a
  real, queryable prior-relationship signal, but only applies when `booking_id` is independently
  supplied (already cross-checked, 2F-14D).
- **Previous Job relationship**: exists (`Job.customer_id` + `Job.tenant_id`) — same caveat as
  above, only applies when `parent_job_id` is supplied.
- **Service-area registration**: exists for tenants/technicians, not for customers.

## Why this is NOT fixed as ARBITRARY_CUSTOMER_TARGETING_DEFECT

The mission's own guidance states "absence of a relationship check is not evidence that arbitrary
targeting is allowed" — but the converse reasoning applies with equal force here: **if a prior
Booking or Job relationship were required for every manually-created Job's customer_id, it would
be impossible to ever create the FIRST Job for a legitimately new customer**, since no other
customer-onboarding or first-contact mechanism exists anywhere in this codebase for a tenant to
establish a relationship with a customer before referencing them in a Job. Requiring a
relationship as a hard rule would not close a defect — it would break the specific, evidenced
use case (a tenant staff member manually recording a walk-in/phone job for a customer they just
spoke to for the first time) that `create_job`'s manual mode appears designed to support, with no
alternative path provided anywhere in the codebase to establish that "first" relationship.

## Disposition

**PROVIDER_SELECTED_EXISTING_CUSTOMER, with any real platform customer account eligible** — this
was the disposition already reached in Slice 2F-14D and is **reconfirmed, not changed**, after
this slice's deeper investigation (Workstream 5) found no additional evidence to the contrary. No
`ARBITRARY_CUSTOMER_TARGETING_DEFECT` was found: the tenant staff member creating the Job already
holds `require_tenant_mutation_permission` authority over their own tenant's Job creation, and
associating a real customer account with a new Job in their own tenant grants that staff member
no elevated access to the customer's data elsewhere in the platform (no other route trusts
`Job.customer_id` alone as an authorization credential for anything beyond that specific Job).

## Consequence for closure status

This slice reports `SECURITY_CLOSED_CUSTOMER_AUTHORITY_PRODUCT_POLICY_BLOCKED` as one dimension
of its overall status (see approval-gate.md) — the security question (can an unauthorized actor
bypass tenant/Job/customer ownership?) is closed; the product-policy question (should a stricter
customer-relationship requirement exist?) remains genuinely open and is not resolved by
inventing a rule that would break an evidenced legitimate use case.
