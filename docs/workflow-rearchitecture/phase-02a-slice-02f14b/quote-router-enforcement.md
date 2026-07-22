# Quote Router Enforcement

## Tenant quote mutations

`create_quote`, `create_job_quote`, `send_job_quote` — genuine tenant/provider mutations. All
three now require `require_staff_or_above_mutation` at the router (canonical tenant persona,
excludes customer, denies read-only tenant access-scope) plus `_get_job_for_quote_management` at
the service layer (principal tenant authority via `job.tenant_id != self.actor_tenant_id` check
for `tenant_owner`, assignment check for `staff`/`technician`, and — newly added this slice — an
explicit `actor_role == "customer"` denial). Both layers are now present; router establishes
persona/scope, service establishes object ownership.

## Customer quote mutations

`respond_to_quote`, `approve_job_quote`, `reject_job_quote` — genuine customer self-service
decisions. All three now require `require_customer` at the router (canonical customer role) plus
`quote.customer_id == customer_id` / `_get_quote_for_customer` at the service layer (customer
ownership of the specific quote). `customer_id` is always derived from
`uuid.UUID(u.user_id)` — never accepted from the request body, path, or query for any of the
three routes. No tenant mutation scope is required for these — correctly customer-self-service,
not tenant-scoped.

## Correction to Slice 2F-14A's framing

Slice 2F-14A's documentation described the (then-unfixed) absence of a router-level persona
dependency on these six routes as the routes being a "distinct capability" with "existing
service-level ownership already adequate on inspection" — implying router-level enforcement was
optional defense-in-depth. This was incorrect for three of the six:
`create_quote` had **no** service-level ownership at all (not "adequate on inspection" — simply
absent), and `_get_job_for_quote_management` never denied `customer`, meaning `create_job_quote`/
`send_job_quote` had a live customer-quote-administration bypass. Router-level enforcement was not
optional here — it was a missing, required layer. See documentation-corrections.md.
