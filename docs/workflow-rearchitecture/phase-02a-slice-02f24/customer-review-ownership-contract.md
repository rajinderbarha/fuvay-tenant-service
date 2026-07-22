# Review Ownership Contract — Slice 2F-24

## Ownership evidence classification

**`DIRECT_TENANT_COLUMN`** and **`DIRECT_CUSTOMER_COLUMN`.**

`CustomerReview` carries both authorities as real, non-null, indexed columns:

```python
customer_id = Column(UUID, nullable=False)
tenant_id   = Column(UUID, nullable=False)
Index("ix_cr_tenant_id", "tenant_id")
Index("ix_cr_customer_id", "customer_id")
```

This is the strongest evidence class in the vocabulary. No derivation through
`ServiceJob`, `ServiceBooking` or a booking relationship is required, and none
was invented — the mission's `SERVICEJOB_DERIVED` / `SERVICEBOOKING_DERIVED`
paths are unnecessary here and were not used. Nothing is stored in JSONB
metadata (contrast the compliance module closed in 2F-20, where no tenant
column existed at all).

## There is no separate provider/business identifier

The model has **no `provider_id` or `business_id` column**. In this engine the
**tenant IS the provider** — `tenant_id` is the provider identity, and
`/v1/provider/*` and tenant scoping are the same boundary.

Consequence, stated plainly because the mission repeatedly asks about it:
**"same-tenant foreign-provider" mutation is not representable in this data
model.** There is no second provider inside a tenant to cross. Every test
matrix row for that scenario is marked `NOT_APPLICABLE` with this reason
rather than being fabricated as a pass. `staff_member_id` exists but
identifies the staff member *rated*, not an owning provider, and is nullable.

## The single central lookup

Workstream 4 required one fail-closed scoped lookup rather than six
inconsistent checks. Before this slice there were three different behaviours:

| Caller | Pre-2F-24 behaviour |
|---|---|
| `submit_reply` | fetch by PK, then `if str(review.tenant_id) != str(tenant_id): raise` |
| `flag_review` | fetch by PK, **no check at all** |
| `get_review` (both routers) | fetch by PK, no check, returned to caller |

All three now route through `ReviewService._get_review_scoped`:

```python
if tenant_id is None and customer_id is None:
    raise ValueError(ERR_PERMISSION_DENIED)      # no global mode
q = select(CustomerReview).where(CustomerReview.id == review_id)
if tenant_id is not None:  q = q.where(CustomerReview.tenant_id == ...)
if customer_id is not None: q = q.where(CustomerReview.customer_id == ...)
if not rv: raise ValueError(ERR_REVIEW_NOT_FOUND)
```

### The four guarantees

1. **A scope is mandatory.** An unscoped call raises `PERMISSION_DENIED`
   *before any query executes* — asserted by
   `test_no_scope_fails_closed_before_any_query`, which also asserts
   `db.execute` was never called. There is deliberately no
   `tenant_id=None means every tenant` mode.
2. **Ownership is a SQL predicate, not a post-fetch comparison.** A foreign
   row is never loaded into memory, so it cannot leak through a log line, an
   exception payload or a later refactor that forgets the comparison.
3. **Missing and unauthorized are indistinguishable.** Both raise
   `REVIEW_NOT_FOUND`, so no route is an existence oracle for another
   tenant's or customer's reviews.
4. **Primary-key-only lookup is no longer an authorization path.**
   `_get_review` survives only for `admin_router` — which is entirely
   `require_super_admin` and legitimately cross-tenant — and its docstring
   states it is never an authorization boundary. The admin call site uses it
   explicitly so the intent is visible rather than disguised behind a fake
   scope.

## Fail-closed matrix

| Condition | Behaviour |
|---|---|
| Scope missing | `PERMISSION_DENIED`, before any query |
| Review absent | `REVIEW_NOT_FOUND` |
| Review owned by another tenant | `REVIEW_NOT_FOUND` (predicate excludes it) |
| Review owned by another customer | `REVIEW_NOT_FOUND` |
| Malformed id | `ValueError` from `uuid.UUID()` before the query |
| Conflicting scopes (tenant + customer that disagree) | both predicates applied; no row matches → `REVIEW_NOT_FOUND` |

## Tests
`TestCentralScopedLookup` (6), plus ownership assertions throughout
`TestProviderFlagAuthority`, `TestProviderReplyAuthority`,
`TestCustomerFlagAuthority` and `TestReadPrivacy`.
