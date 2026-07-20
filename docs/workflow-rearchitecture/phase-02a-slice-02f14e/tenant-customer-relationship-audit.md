# Tenant/Customer Relationship Audit

## Searched

`app/engines/auth/`, `app/engines/booking/`, `app/engines/field_ops/`, and a repo-wide search for
any model/table representing a tenant-scoped customer relationship, directory, CRM, or invitation
system.

## Found

- `auth.User` (role=`customer`): platform-wide account, `tenant_id` nullable and never populated
  for customers. No tenant association field exists on this model.
- `Booking` (`tenant_id` + `customer_id`): a real, queryable relationship signal — a customer who
  has booked with a tenant has an evidenced prior relationship with that tenant. Used by this
  slice's booking cross-check (2F-14D), not as a blanket requirement for all customer_id use.
- `Job` (`tenant_id` + `customer_id`): same evidenced-relationship signal via prior Jobs. Used by
  this slice's parent cross-check (2F-14D).

## Not found

No dedicated relationship table, CRM, contact-book, invitation system, or service-area-based
customer registration exists anywhere in this codebase. `ServiceArea`/service-area registration
(found in `serviceability`/`home_service_assignment` engines) governs tenant/technician coverage,
not customer relationships.

## Conclusion

The ONLY evidenced tenant/customer relationship signals in this entire codebase are "has a prior
Booking with this tenant" and "has a prior Job with this tenant" — both already leveraged by this
slice's booking/parent cross-checks. No broader relationship model exists to enforce for the pure
manual-creation case. See manual-customer-authority.md for why inventing one would be
counterproductive rather than a defect closure.
