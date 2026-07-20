# Customer Authority for create_job

## Disposition: PROVIDER_SELECTED_EXISTING_CUSTOMER (with cross-checks added this slice)

## Evidence

- `create_job`'s `customer_id` field is optional and, when supplied, must reference an existing
  `auth.User` row with `role == "customer"` (Slice 2F-14C) — this rules out
  `OPTIONAL_MANUAL_CUSTOMER` (no ad-hoc customer creation is possible) and confirms the account
  must already exist on the platform.
- No test, frontend caller, or internal caller anywhere in this codebase exercises a
  provider-selected-arbitrary-customer path directly — the only caller (`_spawn_repair_from_consultation`)
  always derives `customer_id` from an already-verified source record (the parent consultation),
  which is `INTERNAL_CALLER_DERIVED`, not `PROVIDER_SELECTED_EXISTING_CUSTOMER` for that specific
  path.
- For the manual/standalone creation path (no `parent_job_id`/`booking_id`), a tenant_owner/staff
  member CAN supply an arbitrary existing customer's `customer_id` — this is
  `PROVIDER_SELECTED_EXISTING_CUSTOMER`, and there is no additional relationship check (e.g. "this
  customer has booked with this tenant before") anywhere in the codebase for this specific route.

## Answering the mission's explicit question

"If provider-selected existing customers are supported, verify whether any same-platform
customer may be selected or whether an existing relationship is required."

**Any same-platform customer may be selected — no prior relationship with the tenant is
required or checked.** This is consistent with how the rest of this codebase treats customers as
platform-wide accounts, not tenant-scoped ones (re-confirmed from Slice 2F-14C:
`auth.User.tenant_id` is nullable and customers are never tenant-associated anywhere else). This
is **not** a security defect — the tenant staff member creating the Job already holds
`require_tenant_mutation_permission` authority over their own tenant's Job creation; associating
an arbitrary real customer account with a new Job in their own tenant does not grant that staff
member any elevated access to the customer's other data, and the customer receives no
notification or exposure from this association alone (no side effect fires until further Job
lifecycle events occur, e.g. notes/media/status updates, which are separately access-controlled).

This is recorded as `PRODUCT_DECISION_REQUIRED` (whether an existing tenant-customer relationship
should be required) rather than a defect — see product-decisions-required.md.

## Fixed this slice (relational consistency, not authority itself)

When `booking_id`/`parent_job_id` are ALSO supplied alongside an explicit `customer_id`, the
supplied `customer_id` must now match the booking's/parent's own customer — closing the
possibility of a Job simultaneously claiming a booking/parent reference while showing an
unrelated customer.
