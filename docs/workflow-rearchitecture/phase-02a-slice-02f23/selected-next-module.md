# Selected Next Module — Slice 2F-24

## Module
`app.engines.customer_reviews.provider_router`

## Mounted prefix
`/v1/provider/reviews/*`

## Exact mutation count
**2**

| Method | Path | Endpoint |
|---|---|---|
| POST | `/v1/provider/reviews/{review_id}/reply` | `submit_reply` |
| POST | `/v1/provider/reviews/{review_id}/flag` | `flag_review` |

## Related reads (same router, not selected)
`GET /v1/provider/reviews` (list), `/summary`, `/staff-summary`,
`/{review_id}` — all `get_current_user` only. In scope for the
implementation slice's read-privacy audit, not for mutation protection.

## Why this outranks every other remaining module

**It is the only module in the queue with a CONFIRMED cross-tenant
mutation**, verified by reading the service, not inferred from the route
signature:

```python
async def _get_review(self, db, review_id):
    r = await db.execute(select(CustomerReview).where(CustomerReview.id == review_id))
```

`_get_review` filters by primary key **only**. `flag_review` then does:

```python
review = await self._get_review(db, review_id)   # no ownership check
...
if review.status != STATUS_FLAGGED:
    review.status = STATUS_FLAGGED               # mutates ANY review
```

There is no tenant or ownership comparison anywhere in `flag_review`.
Combined with a route dependency of bare `get_current_user`, **any
authenticated principal can set any review in any tenant to `flagged`** by
guessing or harvesting a review id. That is a cross-tenant integrity attack
on publicly visible reputation content — a competitor can flag a rival's
positive reviews, or a tenant can suppress its own negative ones.

Three further factors compound it:

1. **Cross-persona impersonation.** `submit_reply` has no role check, so a
   `customer` can post the official provider reply. The service hardcodes
   `ACTOR_PROVIDER` in the event log, so the audit trail will attribute the
   customer's text to the business.
2. **A weaker same-record alternate route.** `customer_router.flag_review`
   passes `tenant_id` **from the client body**
   (`body["tenant_id"]`) — `CLIENT_TENANT_TRUSTED` on the same
   `ReviewFlag` record. Closing only the provider route would leave this open.
3. **Public blast radius.** Reviews are customer-facing published content;
   `submit_reply` can also trigger a customer notification.

### Comparison against the runners-up

| Module | Why it ranks lower |
|---|---|
| `analytics.provider_router` (HIGH) | Also zero-auth, but a single route; tenant_id from JWT and `SCOPE_PROVIDER` hardcoded, so no confirmed cross-tenant mutation — the concern is export/download privacy. |
| `profile.router` (HIGH) | Technician can rewrite tenant legal identity (GST, business name). Serious, but requires an already-trusted staff-side role, the schema is a strict allow-list with no role/tenant/status fields, and no cross-tenant path exists. |
| `media.new_router` (MEDIUM, 6 routes) | Largest by count, but object ownership **is** enforced by the media access policy (`assert_can_delete`); the gap is persona scope only, and effects are reversible and audit-logged. Route count is not risk. |
| `marketing_automation` (MEDIUM) | Zero-auth, but the hypothesised risks **do not exist** — see below. |
| `admin_catalog` × 3 (MEDIUM/LOW) | Parent-child ownership questions on admin-moderated catalog data. |

## Corrections to the mission's own risk hypotheses

Per the instruction not to preserve descriptions the source disproves:

- **`marketing_automation`** — WS6 anticipated bulk customer targeting,
  audience isolation, sender identity, consent/suppression, dispatch before
  authorization, and irreversible external sends. **None exists.** All three
  routes are tenant-scoped raw SQL that insert a draft campaign row, flip a
  status to `pending_admin_review`, or update a notes field. There is no
  send, no audience, no consent model, and no external effect.
- **`media.new_router`** — WS6 anticipated cross-tenant MediaAsset use and
  public URL exposure as open risks. Ownership is already enforced through
  the access-policy layer closed by the 2F-18 series; the residual issue is
  that `require_technician` lets a technician mutate **tenant-level** brand
  assets alongside their own profile photo.
- **`profile.router`** — WS6 anticipated role or tenant mutation through
  profile fields. **Not possible**: `UpdateBusinessProfileRequest` is a
  strict allow-list containing no role, tenant, status or verification field.

## Readiness

- Mounted and active (runtime-verified).
- Clear model boundary: `CustomerReview`, `ReviewReply`, `ReviewFlag`,
  `ReviewEvent`.
- **No new role or permission required** — `require_tenant_owner_mutation`
  is a drop-in, exactly as in 2F-20 and 2F-22.
- No migration, no pipeline merge.
- `submit_reply` already contains the correct ownership pattern
  (`review.tenant_id != tenant_id -> PERMISSION_DENIED`), so `flag_review`
  has a proven in-module template to copy.
- Small: 2 mutations + 4 reads + 1 alternate route.

## Product question (non-blocking)

Whether `staff` may reply to or flag reviews is undecided. It is a
refinement, not a blocker: the safe default is `tenant_owner` +
`super_admin` (brand voice and moderation posture), which can be widened
later without redesign. Recorded in `product-decisions-required.md`.

## Explicit boundaries for Slice 2F-24
See `selected-next-module-boundaries.md`. Not implemented in this slice.
