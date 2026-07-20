# Service-Layer Bypass Report — Slice 2F-24

Router guards do not excuse an unsafe reusable service method. Every service
method reachable from the routes in scope was audited with its full caller
set.

## `ReviewService.flag_review`

| | |
|---|---|
| Callers | `provider_router.flag_review`, `customer_router.flag_review` |
| Strongest caller | provider route (`require_tenant_owner_mutation`) |
| Weakest caller | customer route (`require_customer`) -- both now scoped |
| Tenant source | JWT (provider) / derived from the review (customer) |
| Actor source | principal id; actor type allow-list validated |
| State validation | ownership proven before any write |
| Transaction | flush + commit only after the ownership lookup |

**Cannot** be called with `tenant_id=None` as a global mode -- the scoped
lookup raises `PERMISSION_DENIED` when no scope is supplied, proven with
`db.execute.assert_not_called()`.

## `ReviewService.submit_reply`
Single caller (provider route). Ownership via the central lookup; duplicate
guard before any write; actor id from the principal.

## `ReviewService.get_review`
Callers: provider detail read (tenant-scoped) and customer detail read
(customer-scoped). A scope is now mandatory.

## `ReviewService._get_review` (unscoped)
Sole remaining caller: the `admin_router` detail read, under
`require_super_admin` and legitimately cross-tenant. Documented as never being
an authorization boundary. The admin call site names it explicitly rather than
passing a fake scope, so the cross-tenant intent is visible in review.

## Prohibited patterns -- all verified absent

| Pattern | Status |
|---|---|
| Unscoped primary-key mutation | **removed** -- was the core defect |
| `tenant_id=None` as global mode | impossible -- fails closed |
| Client-controlled actor attribution | rejected by schema + service allow-list |
| Client-controlled tenant ownership | removed from the customer flag route |
| Customer-as-provider reply | blocked by the persona guard |
| Arbitrary status mutation | impossible -- statuses are service constants; provider/customer paths reach only `flagged` |

## Tests
`TestServiceLayerSafety` (5), including two ordering assertions proving the
ownership lookup precedes `db.add` in both mutating methods.
