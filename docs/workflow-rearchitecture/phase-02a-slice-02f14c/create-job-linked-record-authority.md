# create_job Linked-Record Authority

## Verified per linked record

- **Record exists**: `service_type_id`, `parent_job_id`, `booking_id`, `customer_id` — all now
  raise a `422` (`FOREIGN_*`) if the referenced record does not exist (fixed this slice; all four
  previously either had no existence check or only a conditional one).
- **Record is active where required**: `service_type_id`'s catalog entry must have
  `is_active == True` (fixed this slice, `INACTIVE_SERVICE_TYPE`). No "active" concept exists on
  `Booking`/`Job`/`User` in a way this route needs to enforce beyond existence + tenant/type
  match.
- **Record belongs to the principal tenant where tenant-owned**: `service_type_id`
  (`ServiceCatalogItem.tenant_id`), `parent_job_id` (`Job.tenant_id`), `booking_id`
  (`Booking.tenant_id`) — all checked against the already-server-pinned `tenant_id` (fixed this
  slice).
- **Customer belongs to the authenticated/verified business context**: customers are
  platform-owned, not tenant-scoped (confirmed via `auth.User.tenant_id` being nullable and
  customers never carrying a tenant relationship anywhere else in this codebase) — there is no
  "customer belongs to tenant" concept to enforce. What IS enforced (fixed this slice): the
  referenced `customer_id` must resolve to an existing `User` with `role == "customer"` — i.e.
  a tenant cannot link a Job to a nonexistent user or to another tenant_owner/staff account by
  mistake or malice.
- **Service/catalog item is available to the principal tenant**: enforced via
  `ServiceCatalogService.get_by_service_type_id(tenant_id, service_type_id)`, which filters by
  `tenant_id` at the query level — a service type belonging to a different tenant returns `None`
  and is rejected (fixed this slice).
- **Booking/source record belongs to the principal tenant**: fixed this slice
  (`Booking.tenant_id` check).
- **Assigned staff/technician belongs to the principal tenant**: not applicable — `create_job`
  does not accept an assignment field at all (see create-job-request-field-inventory.csv,
  `UNSUPPORTED_FIELD`). Assignment happens exclusively via the separate, already-hardened
  `assign_job` route.
- **Address belongs to the correct customer where applicable**: not applicable — `create_job`
  accepts a free-form `address` dict (city/pincode/lat/long), not a normalized `address_id`
  foreign key, so there is no address record to validate ownership of.
- **Parent/source Job belongs to the principal tenant**: fixed this slice (`parent_job_id` check
  above).
- **Template belongs to the principal tenant or is an approved platform template**: not
  applicable — `create_job` does not accept a `checklist_template_id`; the checklist is derived
  from the already-tenant-validated `service_type_id`'s catalog entry (`cat.checklist_template`),
  which is itself only reachable once `service_type_id` has passed the new tenant-ownership check.
- **Request `tenant_id` cannot influence derived ownership**: confirmed — every new validation
  above uses the already-pinned `tenant_id` variable (set at the top of the method before any of
  these checks run), never the raw request value.
- **Request `customer_id` cannot associate an unrelated customer**: the request `customer_id` can
  reference any existing customer account (this is legitimate — tenant staff creating a job on
  behalf of a real customer is the intended workflow) but can no longer reference a nonexistent
  or non-customer account (fixed this slice).

No adapter between `field_ops.Job` and `ServiceJob`/`Booking` was built — all checks are
read-only existence/ownership lookups against the already-existing `Booking`/`ServiceCatalogItem`/
`User`/`Job` models, using their own existing query patterns.
