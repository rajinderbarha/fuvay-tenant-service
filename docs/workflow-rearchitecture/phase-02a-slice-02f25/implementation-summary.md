# Implementation Summary — Slice 2F-25

## Module
`app.engines.review` — the LEGACY review engine (table `reviews`), distinct
from the canonical `customer_reviews` engine closed in Slice 2F-24.

## Why this slice existed

2F-24 classified this engine `DISTINCT_MODEL`, correctly declined to touch it
(outside that mission's boundary), and flagged that it kept unguarded
behaviour and had live frontend callers. That flag was right — and the
exposure turned out to be **larger than the canonical engine's had been**.

## What was actually wrong

| # | Defect | Severity |
|---|---|---|
| 1 | `submit_reply` and `flag_review` resolved the target with `select(Review).where(Review.id == review_id)` and mutated it with **no ownership check at all** | cross-tenant mutation |
| 2 | `flag_review` was additionally bare `get_current_user` | any authenticated principal |
| 3 | `list_by_tenant` / `list_by_staff` took `tenant_id` from the **query string** and used it verbatim | cross-tenant enumeration |
| 4 | `list_review_requests` / `list_recent_reviews` took `tenant_id` from the **path** | cross-tenant enumeration |
| 5 | `create_review_request` took `tenant_id` from the **request body** | client tenant authority |
| 6 | `_assert_owns` only fires for `actor_role == "customer"` — every other role passed unconditionally, yet `get_review` relied on it | cross-tenant detail read |
| 7 | Read-only tenant users could mutate (`require_permission`, not the scope-aware variant) | access-scope bypass |

Item 6 is the subtle one: a guard that *looks* like ownership enforcement but
is only a customer-self-service check. Its docstring now says so explicitly.

## The fix

**Service gains tenant context.** `ReviewService` had no notion of the
caller's tenant at all — which is precisely why every method trusted a client
value. It now takes `actor_tenant_id`.

**Two central fail-closed helpers:**

- `_get_review_scoped(review_id)` — ownership as a SQL predicate; a foreign
  row is never loaded; foreign and missing are both `NotFound`. Platform admin
  is *explicitly* unscoped rather than unscoped by omission.
- `_effective_tenant(requested)` — the principal's tenant is authoritative. A
  **mismatching** client value is refused; a **matching** one is accepted
  (this is what keeps the live tenant-portal working); a principal with no
  tenant fails closed; `super_admin` may target an explicit tenant.

Applied to all 5 tenant-taking methods and all 3 review lookups.

**Routes:** `flag_review` moved from bare `get_current_user` to the same
permission as its sibling; all three tenant mutations moved from
`require_permission` to the **existing** scope-aware
`require_tenant_mutation_permission`, so read-only tenant users are denied.

No new role, permission, model or migration.

## Coverage — the denominator moved, by exact route evidence

The prefix-based Design A sweep only ever considered
`/v1/provider|staff|tenant/*`. These routes live on the generic `/v1/reviews/*`
prefix, so **three genuine tenant mutations had never been counted at all**.

- Denominator **226 -> 229** (reply, flag, create_request added)
- Numerator **209 -> 212** (all three protected in the same slice)
- Unprotected **17** (unchanged)

`resolve_flag` is `require_super_admin` -> outside tenant X/Y. `POST
/v1/reviews` is 410 -> excluded. Neither was added.

## Frontend
No frontend change was needed. tenant-portal sends its **own**
`getTenantId()` on every legacy call, which the "reject only mismatches"
design accepts. Verified across all six applications.

## Tests
49 new deterministic tests, including a caller-inventory assertion that lists
all six known apps so a future "no callers" claim cannot be made without
checking them.

## Final status
**`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`** —
see `approval-gate.md`.
