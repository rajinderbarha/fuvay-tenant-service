# Customer Tracking Boundary — Slice 2F-11A (Workstream 8)

## Verified (unchanged from Slice 2F-11, re-confirmed this slice)
- **Canonical customer role required**: `require_customer` (applied
  Slice 2F-11, unmodified).
- **Authenticated principal is authoritative**: `customer_id` is always
  `uuid.UUID(str(user.user_id))`, never request-supplied — the route has
  no `customer_id` field in any query/path parameter.
- **Lead/customer relationship checked**: inline query filters
  `RealEstateLead.id == lead_id AND RealEstateLead.customer_id ==
  uuid.UUID(str(user.user_id))` together — a foreign customer's lead ID
  simply doesn't match, no partial exposure.
- **Tenant/provider derived from the lead**: `lead.tenant_id` is read
  from the fetched lead record itself and passed to `get_notes`, never
  independently trusted from the request.
- **Customer sees only their own tracking record**: proven by the
  combined filter above.
- **Provider-internal notes excluded**: `get_notes(..., customer_only=True)`.
- **Staff/technician endpoints cannot be reached through the customer
  path**: structurally separate router (`customer_router`, distinct
  prefix `/v1/customer/real-estate-leads`), distinct dependency
  (`require_customer`).
- **Foreign lead IDs return the established safe-denial response**: the
  combined query returns no row, and the route raises
  `ERR_RECORD_NOT_FOUND` — the same not-found response a genuinely
  missing lead would produce.
- **No mutation occurs on GET**: `customer_tracking` performs only a
  `select` and 2 read service calls (`get_notes`); no `db.add`/`flush`/
  `commit` anywhere in the function.
- **Does not use tenant mutation access scope**: confirmed — `require_customer`
  has no access-scope concept at all (customers don't carry a tenant
  `access_scope` claim).

## No change needed
This boundary was already correct in Slice 2F-11 (only the role gate
was added there; the ownership filter itself pre-dated that slice and
was always correct). Re-verified directly this slice via
`TestCustomerTrackingPrivacy`, not re-fixed.
