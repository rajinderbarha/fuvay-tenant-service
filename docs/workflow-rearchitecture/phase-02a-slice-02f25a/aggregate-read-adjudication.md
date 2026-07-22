# Aggregate Read Adjudication — Slice 2F-25A

## Route
`GET /v1/reviews/aggregates/{entity_type}/{entity_id}` -> `get_aggregate`

## Verdict

**`TENANT_SCOPED_AGGREGATE_READ`**

Explicitly **not** `PUBLIC_AGGREGATE_READ`.

## Why not public

The mission requires that a public claim be proven field-by-field. It cannot
be, because the model does not support it:

| Public-claim requirement | Status |
|---|---|
| Entity type is allow-listed | **FAILS** — `entity_type` is a free `String(20)` written by `_recompute_aggregate`; there is no allow-list anywhere in the engine |
| Entity is intentionally public | **FAILS** — no `is_public` flag exists on `ReviewAggregate` |
| Only aggregate values returned | passes — counts and averages only |
| No tenant/customer identifiers leak | passes — `tenant_id` is a predicate, never serialized |
| Hidden/rejected reviews do not contribute | **UNPROVEN** — `_recompute_aggregate` was not re-derived this slice |
| Arbitrary entity types cannot become an oracle | **FAILED before this slice** — any `(type, id)` pair was readable |
| Missing/unauthorized entities are safe | now yes — both return the zero-count shape |

Three requirements fail outright. Declaring it public would have meant
**inventing** a public-review policy, which this slice is forbidden from
doing.

## The exposure before this slice

`ReviewAggregate` rows are keyed `(entity_type, entity_id)` and carry a real
`tenant_id`. With no scoping, any authenticated principal could read the
aggregate rating of any tenant (`entity_type="tenant"`) or any staff member
(`entity_type="staff"`) by supplying the id — competitor reputation data,
readable at will.

## After

```
q = select(ReviewAggregate).where(entity_type == ..., entity_id == ...)
if actor_role != "super_admin":
    if actor_tenant_id is None: raise NotFound
    q = q.where(ReviewAggregate.tenant_id == actor_tenant_id)
```

- tenant principals: own tenant only
- `super_admin`: explicitly unscoped
- no tenant context: fails closed before any query
- absent/foreign: identical zero-count response — the pre-existing contract
  for "no reviews yet", which conveniently makes foreign entities
  indistinguishable from empty ones

## Frontend
tenant-portal calls `getAggregate()` as `/aggregates/tenant/{ownTenantId}` —
its own tenant, so it continues to work unchanged.

## Open product question
Whether provider aggregate ratings *should* be publicly readable (a normal
marketplace feature) is recorded in `product-decisions-required.md`. Building
that requires an explicit public-entity allow-list, not the absence of a
check.
