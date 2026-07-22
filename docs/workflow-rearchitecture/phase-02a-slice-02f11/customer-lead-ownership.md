# Customer Lead Ownership — Slice 2F-11 (Workstream 7)

## Provider-side (agent) lead ownership
Enforced by two independent, complementary mechanisms:
1. **Tenant ownership**: `_get_lead(db, lead_id, tenant_id)` filters
   `RealEstateLead.tenant_id == tenant_id`, where `tenant_id` is always
   `uuid.UUID(str(user.tenant_id))` from the authenticated principal —
   never request-supplied (no route schema in this module has a
   `tenant_id` field). A foreign-tenant lead ID raises
   `ERR_RECORD_NOT_FOUND` (the tenant filter simply excludes it from the
   query), not a distinguishable "exists but denied" response — no
   existence leakage.
2. **Assignment ownership**: `_assert_agent_owns_lead(lead, agent_id)`
   requires an exact match between the lead's `agent_id` and the calling
   staff member's own `user_id` (the codebase's established
   `staff_member_id == user.user_id` convention, per
   `app/core/staff_scope.py`) — a staff member from the SAME tenant, but
   not assigned to this specific lead, is still denied
   (`ERR_STAFF_NOT_ASSIGNED`).
3. **[Fixed this slice] Persona ownership**: `require_owner_or_office_staff_mutation`
   now gates every mutation, ensuring only `tenant_owner`/`staff`/
   `super_admin` roles reach the assignment check at all — previously
   any authenticated role (including customer, guest, or an unrelated
   technician) could reach it, relying entirely on the practically
   unguessable-UUID nature of `agent_id` matching for protection.

## Customer-side (tracking) ownership
`customer_router`'s `/tracking` route filters
`RealEstateLead.customer_id == user.user_id` directly in its own inline
query (not delegated to a shared ownership helper) — a foreign customer's
lead ID returns "not found" (no row matches the combined `id` +
`customer_id` filter), not a distinguishable denial. **Fixed this
slice**: added `require_customer` role gate on top of this pre-existing,
correct filter — previously any authenticated role could reach the query
(though only a `customer`-role account would ever have a matching
`customer_id` in practice, since customers are the only role whose
`user_id` populates `RealEstateLead.customer_id`).

## Customer cannot mutate the provider-created lead record
Confirmed structurally — `customer_router` has exactly one route
(`/tracking`, GET only) and it is read-only. No customer-facing mutation
of any kind exists for `RealEstateLead` in this module.

## Customer contact data exposure
`RealEstateLead.customer_snapshot`/`requirement_snapshot` (JSONB fields
likely containing customer-provided contact/requirement data) are
returned via `lead.to_dict()` to any caller who passes the tenant/
assignment/persona checks above — i.e., to the tenant's own assigned
staff and tenant owner, which is the intended, correct exposure (a
business's own staff seeing their own assigned lead's customer details).
No unrelated tenant, technician, or customer can reach this data (see
`privacy-pii-review.md`).
