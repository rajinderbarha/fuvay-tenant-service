# Read and Privacy Audit — Slice 2F-24

## Two read IDORs found and fixed (not previously known)

Neither appeared in the 2F-23 finding; both were discovered by reading the
routers during this slice.

| Route | Before | After |
|---|---|---|
| `GET /v1/provider/reviews/{review_id}` | unscoped PK read -- **any authenticated principal could read any review in any tenant** | scoped to JWT tenant |
| `GET /v1/customer/reviews/{review_id}` (`get_my_review`) | unscoped PK read despite the name | scoped to own `customer_id` |

Exposure before the fix included `pending`, `hidden`, `rejected` and `deleted`
reviews together with `moderation_reason` and `rejection_reason` -- internal
moderation data, cross-tenant.

## Full read inventory

| Read | Scope | Status |
|---|---|---|
| provider list `GET /v1/provider/reviews` | `tenant_id` from JWT | already scoped |
| provider `/summary` | `tenant_id` from JWT | already scoped |
| provider `/staff-summary` | `tenant_id` from JWT | already scoped |
| provider detail | **now** `tenant_id` | fixed |
| customer list | `customer_id` from JWT | already scoped |
| customer detail | **now** `customer_id` | fixed |
| public tenant list / summary | tenant path param; approved+public only | by design |
| public review detail / reply | approved+public only | by design |
| admin list / detail / events / flags / replies | `require_super_admin` | by design |

## Verification

- **Public reads expose only publishable fields** -- the public router filters
  to approved/public reviews; unchanged by this slice.
- **Provider reads are tenant scoped**; **customer reads are customer scoped**.
- **Internal moderation notes are not public** -- `moderation_reason` and
  `rejection_reason` are reachable only through the tenant-scoped provider
  read, the customer's own review, or the admin surface.
- **Foreign and missing ids are privacy equivalent** -- both
  `REVIEW_NOT_FOUND` via the central scoped lookup, so no route is an
  existence oracle.
- **Hidden/rejected/deleted content is not leaked cross-tenant** -- it was,
  before this slice, through the two unscoped detail routes.
- **GET routes do not mutate** -- confirmed by reading every handler body;
  none writes or commits.

## Flag actor exposure
`ReviewFlag.to_dict()` includes `flagged_by_user_id` and `flagged_by_type`.
Flags are returned only from the admin surface and to the flag's own creator
on write. No route returns another party's flag actor to a tenant or customer.
Recorded rather than assumed.

## Tests
`TestReadPrivacy` (5).
