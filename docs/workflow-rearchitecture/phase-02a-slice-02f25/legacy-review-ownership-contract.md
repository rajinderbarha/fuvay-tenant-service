# Legacy Review Ownership Contract — Slice 2F-25

## Ownership evidence: `DIRECT_TENANT_COLUMN`

`Review.tenant_id` is a real indexed column, so no derivation through
`Booking`, `ServiceBooking`, `field_ops.Job` or `ServiceJob` is required —
and none was introduced. No identifier is adapted between pipelines.

## Two central fail-closed helpers

### `_get_review_scoped(review_id)` — object authority
```
q = select(Review).where(Review.id == review_id)
if actor_role != "super_admin":
    if actor_tenant_id is None: raise NotFound      # fail closed
    q = q.where(Review.tenant_id == actor_tenant_id)
if not row: raise NotFound
```
- Ownership is a **SQL predicate**, so a foreign row is never loaded.
- A principal with no tenant context is refused **before** any query.
- Foreign and missing ids are indistinguishable (`NotFound` both).
- `super_admin` is unscoped **explicitly**, not by omission — the difference
  matters, because the previous behaviour was unscoped for *everyone*.

### `_effective_tenant(requested)` — query authority
- `super_admin`: may target an explicit tenant; refuses if none supplied.
- everyone else: pinned to `actor_tenant_id`.
- a **mismatching** client value is **refused**, not silently ignored —
  silently ignoring it would let a caller believe it had queried a tenant it
  had not.
- a **matching** client value is accepted, which is what keeps the live
  tenant-portal working without a frontend change.
- no tenant context -> `TENANT_ACCESS_DENIED`.

## What `_assert_owns` is, and is not

```
if self.actor_role == "customer" and self.actor_id != customer_id: raise NotFound
```

It fires **only** for the customer role. `tenant_owner`, `staff`,
`technician`, `super_admin` and any unknown role pass unconditionally. It was
never a tenancy boundary, yet `get_review` and `list_by_customer` relied on it
as though it were — which is how the cross-tenant detail read existed.

It is retained (it is a correct customer-self-service guard) and its docstring
now states plainly that it must never be used as tenant isolation. A test
asserts that warning is present.

## Fail-closed matrix

| Condition | Behaviour |
|---|---|
| No tenant context on principal | `NotFound` (lookup) / `TENANT_ACCESS_DENIED` (query) — before any SQL |
| Review absent | `NotFound` |
| Review in another tenant | `NotFound` — predicate excludes it |
| Client tenant != principal tenant | `TENANT_ACCESS_DENIED` |
| Client tenant omitted | principal's tenant used |
| `super_admin` without explicit tenant on a list | `TENANT_REQUIRED` |
| Customer reading another customer's review | `NotFound` (`_assert_owns`) |

## Tests
`TestScopedLookup` (5), `TestEffectiveTenant` (8).
