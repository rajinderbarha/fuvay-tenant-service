# Residual Service-Layer Bypass Report — Slice 2F-25A

## Per capability

### `get_aggregate`
- Callers: aggregate route only.
- Tenant source: `self.actor_tenant_id`.
- SQL scoping: `entity_type`, `entity_id`, `tenant_id` (super_admin exempt).
- Fails closed with no tenant context, before any query.

### `get_review_request`
- Callers: job-request route only.
- Scoping: `customer_id` for the customer persona, else `tenant_id`.
- Fails closed for a tenantless non-customer.

### `list_by_customer`
- Callers: customer-list route only.
- Scoping: `_assert_owns` for customers; `tenant_id` predicate otherwise.
- Fails closed for a tenantless non-customer.

### `create_review_request`
- Callers: **two** — the HTTP route, and `field_ops.service` on job close.
- **Weakest caller was the HTTP route** (client job_id + customer_id); it now
  proves parentage.
- **The internal caller is the trusted one** and holds the Job row directly.
- `trusted_internal` defaults `False`, so a future caller that forgets it gets
  the strict path rather than the lax one — fail-safe by default.

## Prohibited patterns

| Pattern | Status |
|---|---|
| Tenant absent -> global behaviour | **removed** — every method fails closed |
| Tenant conflict | refused (`TENANT_ACCESS_DENIED`) |
| Foreign customer | refused (`_assert_owns` / `CUSTOMER_MISMATCH`) |
| Foreign Job/entity | refused (tenant predicate on the Job and aggregate lookups) |
| Persona context absent | fails closed |
| Private route used as a global lookup | **removed** — all four are scoped |

## The regression this exposed

`field_ops.service` called `create_review_request` with **no persona context
at all**. Under 2F-25's pinning that meant `TENANT_ACCESS_DENIED` on every job
close, swallowed by `except Exception`. It is the clearest possible
demonstration of why the mission asks for *every* caller to be enumerated:
the weakest caller analysis in 2F-25 listed the HTTP route and missed the
internal one entirely.
