# Swallowed-Exception Risk Audit — Slice 2F-26

## Why this exists

Slice 2F-25 introduced a regression that exact node-ID comparison could not
detect. `field_ops` job close creates the review request inside
`try: ... except Exception: logger.warning(...)`. When 2F-25 added tenant
pinning, that call began raising `TENANT_ACCESS_DENIED` on **every job
close** — caught, logged at warning level, invisible to the test suite. Review
requests silently stopped being created.

Node-ID comparison detects *test outcomes*. It cannot detect a capability that
degrades silently inside a caught exception.

## Confirmed swallowed-exception path

| Caller | Swallowed call | Status |
|---|---|---|
| `field_ops.service` job close | `ReviewService.create_review_request` | **REPAIRED in 2F-25A**; behavioural invariant added this slice |

The `except Exception` block itself remains — repairing the caller fixed the
symptom, not the pattern. `test_swallowed_exception_path_is_still_documented`
asserts the block is still present, so the residual risk stays visible rather
than being assumed away.

## Behavioural invariants added

`TestBehaviouralInvariants` asserts, independent of node IDs:
- `field_ops` still passes `actor_tenant_id=job.tenant_id` and
  `trusted_internal=True`;
- the exact internal call shape still succeeds and writes a request row
  (`db.add` called once);
- the swallowing `except Exception` is still present.

## Generalisation

Any future authorization hardening on a service method reached from a
swallowed-exception caller can silently disable a capability.
`newly-discovered-service-caller-graph.csv` records, per newly discovered
mutation, whether such a caller exists. Only the job-close path currently does.

**Recommendation (not implemented — out of scope):** narrow that
`except Exception` to the exceptions actually expected, so an authorization
denial surfaces instead of being logged at warning level.
