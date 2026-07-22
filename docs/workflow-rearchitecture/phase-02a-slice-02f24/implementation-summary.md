# Implementation Summary — Slice 2F-24

## Module
`app.engines.customer_reviews.provider_router`
Selected mutations: `POST /v1/provider/reviews/{review_id}/reply`,
`POST /v1/provider/reviews/{review_id}/flag`

## The defects (all four confirmed by source, then closed)

### 1. Cross-tenant review flagging — the critical one
`flag_review` resolved the review through `_get_review`, a **primary-key-only**
lookup, and performed **no ownership check whatsoever**, then wrote
`review.status = "flagged"`. The route was bare `get_current_user`. Any
authenticated principal could therefore flag **any review in any tenant**.

### 2. Customer-as-provider impersonation
`submit_reply` was also bare-authenticated. A `customer` could post the
official provider reply, and the service records the event as
`ACTOR_PROVIDER` — so the audit trail attributed a customer's text to the
business.

### 3. Client-controlled tenant on the same-record alternate
`customer_router.flag_review` read `body["tenant_id"]` and passed it as the
flag's tenant, letting a client choose which tenant a moderation record was
attributed to.

### 4. Read IDOR on both detail routes (found this slice, not previously known)
`GET /v1/provider/reviews/{review_id}` and
`GET /v1/customer/reviews/{review_id}` both called an unscoped
`get_review(review_id)`. Any authenticated principal could read any review in
any tenant — including `pending`, `hidden`, `rejected` and `deleted` reviews
together with their `moderation_reason` and `rejection_reason`. The customer
route is even named `get_my_review`.

## The fix: one central fail-closed scoped lookup

Per Workstream 4's instruction to avoid "six inconsistent ownership checks",
a single helper now owns review authorization:

```python
async def _get_review_scoped(self, db, review_id, *, tenant_id=None, customer_id=None):
    if tenant_id is None and customer_id is None:
        raise ValueError(ERR_PERMISSION_DENIED)   # no global mode
    q = select(CustomerReview).where(CustomerReview.id == review_id)
    ...                                            # scope as SQL predicates
    if not rv: raise ValueError(ERR_REVIEW_NOT_FOUND)
```

- **A scope is mandatory.** There is no `tenant_id=None means all tenants`
  mode; an unscoped call fails closed before any query runs.
- **Scopes are SQL predicates**, so a foreign row is never loaded at all.
- **Missing and unauthorized are indistinguishable** (both `REVIEW_NOT_FOUND`),
  so no route is an existence oracle for another tenant's reviews.

`flag_review`, `submit_reply` and the public `get_review` all route through
it. `_get_review` survives **only** for the platform-admin surface (entirely
`require_super_admin`, legitimately cross-tenant) and is documented as never
being an authorization boundary.

## Changes made (5 files)

| File | Change |
|---|---|
| `review_service.py` | added `_get_review_scoped`; `flag_review` + `submit_reply` + `get_review` routed through it; actor-type allow-list; flag tenant taken from the review |
| `provider_router.py` | `require_tenant_owner_mutation` on both mutations; strict `ProviderReplyRequest` / `ReviewFlagRequest` schemas; tenant-scoped detail read |
| `customer_router.py` | `require_customer`; strict `CustomerFlagRequest` (rejects `tenant_id`); customer-scoped flag and detail read |
| `admin_router.py` | reads via the explicitly-unscoped `_get_review` so admin intent is visible at the call site |
| `test_sprint24_customer_reviews.py` | 3 mock doubles re-pointed to the new helper (intent unchanged) |

No role, permission or migration added. Legacy `POST /v1/reviews` remains 410.

## Coverage
**207/226 → 209/226.** 17 unprotected across 6 modules. The customer flag
route is **not** counted — it is outside the tenant-only canonical CSV by the
Design A convention, and was corrected without touching the numerator.

## Tests
46 new deterministic tests. 276 passing across the full slice-suite set.

## Final status
**`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`** —
see `approval-gate.md`.
