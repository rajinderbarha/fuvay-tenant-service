# Slice 2F-37 Implementation Contract — Financial, Product-Policy and Remaining Held-Route Closure

**Not executed in Slice 2F-34.** Frozen, ready-to-run brief. Executes
AFTER Slice 2F-36 completes.

## Mission

Close `platform_commerce_deposit` (3 routes). Adjudicate the 17 frozen
held candidates. Freeze (not resolve) the N01 domain-integrity backlog
as a visible, separate sub-scope. Do not invent product policy for
`compliance` candidates or any other held route lacking an existing
policy.

## Starting arithmetic

Load live from Slice 2F-36's final output. Stop with
`AUTHORITATIVE_QUEUE_RECONCILIATION_BLOCKED` if it doesn't reconcile.

## Exact modules and route files

- Set A: [slice-2f37-module-scope.csv](slice-2f37-module-scope.csv) (hash `6d64894af41dbf67`)
- Set B: [slice-2f37-held-scope.csv](slice-2f37-held-scope.csv) (hash `b4bf520b7764f11b`)
- Set C: [slice-2f37-exclusion-scope.csv](slice-2f37-exclusion-scope.csv) (hash `2074bf7001bc1d27`)

## Allowed application files

- `app/engines/platform_commerce/router.py`, `app/engines/
  platform_commerce/service.py`
- Router/service files for the 17 held routes — discover per module
  (pricing, commerce, payments, subscriptions, compliance engines).
- `app/core/permissions.py` — only if no existing guard fits.
- Explicitly OUT: any N01 media file (the domain-integrity backlog is
  frozen as a scope statement in this slice, not remediated).

## Forbidden files

Anything backing a Set C route or assigned to 2F-35/2F-36/2F-38.

## Workstreams

1. Reconfirm A/B/C hashes against the LIVE post-2F-36 canonical/matrix.
2. Close `platform_commerce_deposit`'s 3 routes: swap to `require_
   tenant_mutation_permission`, preserving the existing (already-sound)
   `_assert_owns_tenant_deposit` service-layer check unchanged.
3. Adjudicate each of the 17 held routes individually. For `compliance`
   candidates specifically: adjudicate ONLY if existing repository policy
   (e.g. an existing deletion/portability workflow already implemented
   elsewhere) supports it; otherwise disposition as
   `PRODUCT_DECISION_REQUIRED` and record in the product-decision
   registry — do not guess a policy.
4. Formally freeze the N01 domain-integrity backlog: re-confirm the 3
   items are still open, still non-canonical, still not reducing N01's
   protected count. Do not remediate them.
5. Full test matrix with negative controls for the 3 canonical routes
   and every adjudicated held route.
6. A dedicated verifier script (`verify_2f37.py`) with `--selftest`.

## Canonical/held update rules

Same discipline as 2F-35/36. `compliance` routes with no clear existing
policy must NOT be added canonically merely to "make progress."

## Regression requirements

Full suite, twice, deterministic, zero new failures. M01/N01/geo/2F-35/
2F-36 non-regression canaries re-run.

## Allowed final statuses

Same 6-status list, applied per module.
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` is
expected to be the realistic status for any `compliance`-adjacent
closure that hits an undecided policy question.

## Approval gate / stop condition

Stop at Slice 2F-37's own approval gate. Do not select a further module.
Do not begin Slice 2F-38 in the same run.
