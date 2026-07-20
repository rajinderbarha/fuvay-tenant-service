# Customer Review-List Authority — Slice 2F-25A

## Route
`GET /v1/reviews/customers/{customer_id}` -> `list_by_customer`

## The defect

The route relied on `_assert_owns`:

```
if self.actor_role == "customer" and self.actor_id != customer_id:
    raise NotFound
```

It fires **only** for the customer role. `tenant_owner`, `staff`,
`technician` and any unknown role passed unconditionally — so a tenant
principal could enumerate **any** customer's complete review history **across
every tenant**, by supplying a customer id.

2F-25 recorded this as an accepted residual. That was the wrong call: it is a
cross-tenant customer-data read, not a benign gap.

## After — per persona

| Persona | Access | Enforcement |
|---|---|---|
| `customer` (self) | own reviews across every tenant dealt with | `_assert_owns` (unchanged) |
| `customer` (other) | **denied** | `_assert_owns` -> NotFound |
| tenant-side principal | only rows belonging to **its own tenant** | `Review.tenant_id == actor_tenant_id` |
| `super_admin` | unscoped | explicit |
| no tenant context (non-customer) | **denied** | fails closed |

A tenant can therefore see the reviews a customer left **for that tenant** —
which it can already see through `list_by_tenant` — and nothing more. No new
visibility was invented; the cross-tenant portion was simply removed.

## Requirements check

| Requirement | Status |
|---|---|
| Customer self-view uses the authenticated identity | MET |
| Client `customer_id` cannot broaden self-service | MET — `_assert_owns` compares to `actor_id` |
| Tenant actors require the tenant relationship | MET — tenant predicate |
| Same-tenant arbitrary customer enumeration | **still permitted within the tenant's own rows** — this is the established model (`list_by_tenant` already exposes them). Narrowing to an explicit tenant-customer relationship would be new policy; recorded as a product question. |
| Cross-tenant customer reads fail | MET |
| Hidden/rejected/deleted filtered | **NOT filtered** — `status` is returned as-is, unchanged from before. Recorded in `known-limitations.md`; the rows are the tenant's own. |
| Missing and unauthorized are equivalent | MET |

## Field privacy
`_review_dict` omits `flagged_reason`, `flagged_by`, `resolved_by` and
`idempotency_key` — moderation-private and never-expose fields are not
serialized. See `residual-field-privacy.csv`.
