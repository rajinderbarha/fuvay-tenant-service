# Behavioural Invariant Report — Slice 2F-26

## Why invariants, not just node IDs

Slice 2F-25 introduced a regression that exact node-ID comparison could not
see: `field_ops` job close silently stopped creating review requests, because
the failure was caught by `except Exception` and logged at warning level. No
test covered the path, so no node ID changed.

Node-ID comparison detects **test outcomes**. It cannot detect a capability
that degrades silently. Every slice from here on needs invariants that assert
behaviour directly.

## Invariants asserted this slice

| Invariant | Assertion | Result |
|---|---|---|
| Job-close review request is still created | the exact internal call shape (`actor_role="system"`, `actor_tenant_id=job.tenant_id`, `trusted_internal=True`) returns `status="sent"` and calls `db.add` exactly once | PASS |
| The internal caller still passes tenant context | `actor_tenant_id=job.tenant_id` and `trusted_internal=True` present in `field_ops.service` | PASS |
| The swallowed-exception block is still present | `except Exception` still wraps the job-close call, so the residual risk stays visible rather than being assumed gone | PASS |
| Prior closures intact | Package Commerce (`require_tenant_owner_mutation` + `is_paid=False`), customer_reviews, compliance | PASS |
| Legacy review create still 410 | source assertion | PASS |
| Legacy scoped lookups intact | `_get_review_scoped` in `flag_review`; `_effective_tenant` in `list_by_tenant` | PASS |

## No authorization behaviour changed

This slice modified **no application file**. The invariants confirm that
directly rather than inferring it from a clean test diff — which is the point:
a clean diff is exactly what the 2F-25 regression also produced.

## Warnings inspection

No new swallowed-authorization warnings appeared. The only recurring warnings
in the suite are the pre-existing FastAPI duplicate-operation-id warnings from
`service_setup/templates_router.py` and a Starlette TestClient deprecation
notice — both present before this slice and unrelated to authorization.
