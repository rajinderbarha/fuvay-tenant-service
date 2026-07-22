# Legacy Service-Layer Bypass Report — Slice 2F-25

## Method-by-method

| Method | Callers | Tenant source | Ownership | After |
|---|---|---|---|---|
| `submit_reply` | reply route | JWT (service) | `_get_review_scoped` | scoped |
| `flag_review` | flag route | JWT | `_get_review_scoped` | scoped |
| `resolve_flag` | resolve route (`require_super_admin`) | platform-wide | intentional | unchanged |
| `get_review` | detail route | JWT | `_get_review_scoped` + `_assert_owns` | scoped |
| `list_by_tenant` | list route | `_effective_tenant` | tenant predicate | pinned |
| `list_by_staff` | staff list | `_effective_tenant` | tenant predicate | pinned |
| `list_by_customer` | customer list | n/a | `_assert_owns` | unchanged (residual) |
| `list_review_requests` | 2 routes | `_effective_tenant` | tenant predicate | pinned |
| `list_recent_reviews` | recent route | `_effective_tenant` | tenant predicate | pinned |
| `create_review_request` | create route | `_effective_tenant` (was BODY) | tenant pinned | pinned |
| `get_review_request` | job lookup | n/a | none | residual |
| `get_aggregate` | aggregate route | n/a | none | residual |
| `create_review` | **no mounted route** (410) | n/a | n/a | unreachable via HTTP |

## Prohibited patterns

| Pattern | Status |
|---|---|
| Global behaviour from `tenant_id=None` | **removed** — `_effective_tenant` fails closed; `_get_review_scoped` refuses a tenantless principal |
| Unscoped primary-key mutation | **removed** |
| Unscoped private detail read | **removed** |
| Client-controlled actor attribution | never possible — no actor-type field |
| Client-controlled tenant authority | **removed** |
| Arbitrary status mutation | never possible — constants only |

## Strongest / weakest caller
Strongest: `resolve_flag` (`require_super_admin`). Weakest **was**
`flag_review` (bare authentication); it is now level with `submit_reply` and
`create_request` under the scope-aware tenant permission.

## Note
`create_review` remains on the service and is used by seeding/tests. No
mounted route reaches it — asserted by
`test_no_alternate_mount_reactivates_creation`.
