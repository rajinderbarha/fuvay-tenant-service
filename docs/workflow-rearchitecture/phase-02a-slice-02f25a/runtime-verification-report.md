# Runtime Verification Report — Slice 2F-25A

## Verifier
`python scripts/workflow_rearchitecture/verify_legacy_review.py` -> **exit 0**,
25 checks, all PASS.

Unlike Slice 2F-25's report, this is the output of an actual script that fails
on the conditions it names — see `runtime-verifier-hardening.md`.

## Four capabilities — final state

| Capability | Before 2F-25A | After |
|---|---|---|
| `GET /aggregates/{entity_type}/{entity_id}` | completely unscoped | tenant-scoped; super_admin explicit; fails closed without tenant |
| `GET /requests/jobs/{job_id}` | bare job_id lookup | customer-scoped for customers, tenant-scoped otherwise |
| `GET /customers/{customer_id}` | `_assert_owns` (customer role only) | + tenant predicate for every non-customer principal |
| `POST /requests` (create_request) | client job_id + customer_id, unverified | parent `field_ops.Job` resolved in-tenant; customer derived; mismatch rejected |

## Exit conditions (must exit non-zero if any hold)

| Condition | Result |
|---|---|
| Any mounted route unclassified | **NO** — all 15 classified |
| Aggregate treated as public without a proven contract | **NO** — adjudicated tenant-scoped, not public |
| Job request status not relationship scoped | **NO** |
| Customer listing permits arbitrary tenant/customer enumeration | **NO** |
| create_request lacks exact Job/customer/tenant ownership | **NO** |
| A read trusts client tenant identity | **NO** |
| A private route uses an unscoped lookup | **NO** |
| Documentation narrows "privacy closure" to dodge a mounted route | **NO** — verifier checks the docs |
| Coverage described as application-wide complete | **NO** — verifier checks for the forbidden label |

## Regression the verifier now guards

The `field_ops` internal-caller check exists because Slice 2F-25 silently
broke that path. A verifier that only inspected the review engine would have
stayed green while job closes stopped creating review requests.

## Test-suite exit codes
- `test_phase2f25a_legacy_review_residual_closure.py` — 36 passed, 1 skipped, exit 0
- `test_phase2f25_legacy_review_engine_authorization.py` — 49 passed, exit 0
- canonical + prior-slice suites — passing
