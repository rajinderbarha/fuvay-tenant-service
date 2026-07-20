# Slice 2F-35 Implementation Contract — Critical Destructive and Security-Sensitive Authorization

**Not executed in Slice 2F-34.** This is the frozen, ready-to-run brief.

## Mission

Implement complete authorization, tenant/object ownership, and privacy
closure for `webhook_endpoint_management` and `rag_query`. Adjudicate all
9 frozen held candidates (`security`, `documents`, `rag` modules) from
direct source evidence. Any adjudicated `TENANT_PROVIDER_MUTATION_ADD`
route must be added canonically and protected in the same slice.

## Starting arithmetic

- Protected: 241, Denominator: 264, Unprotected: 23, Pending held: 54
- Canonical hash: `d4900ce03daa5437`
- Matrix hash: `abfa5d030b1cfeee`
- Held registry hash: `3729aa0e0fd5dafe`

If these do not match live repository state exactly at execution time,
stop with `AUTHORITATIVE_QUEUE_RECONCILIATION_BLOCKED`.

## Exact modules and route files

- Set A: [slice-2f35-module-scope.csv](slice-2f35-module-scope.csv) (hash `d1ad1fa8027272e1`)
- Set B: [slice-2f35-held-scope.csv](slice-2f35-held-scope.csv) (hash `4fb3739e9ace9269`)
- Set C: [slice-2f35-exclusion-scope.csv](slice-2f35-exclusion-scope.csv) (hash `43a129bd966687b6`)

## Allowed application files (confirm exact paths via `inspect.getsourcefile`, do not assume)

- `app/engines/webhook/router.py`, `app/engines/webhook/service.py`
- `app/engines/rag/router.py`, `app/engines/rag/service.py`
- Whatever router/service file(s) implement the 9 Set B routes (`app/
  engines/security/*`, document-management engine, `app/engines/rag/*`)
  — discover and record before modifying.
- `app/core/permissions.py` — ONLY if no existing guard (`require_
  tenant_mutation_permission`, `require_mutation_access_scope`) fits.

## Forbidden files

Anything backing a Set C route. `app/engines/geo/*`, `app/engines/
media/*` (already-closed modules — do not reopen). Any file assigned to
2F-36/2F-37/2F-38 in
[cross-slice-file-conflict-audit.csv](cross-slice-file-conflict-audit.csv).

## Workstreams (mirror the discipline established in Slices 2F-31A/33)

1. Reconfirm A/B/C hashes and mount status.
2. Per-route authority contract (persona, role, permission, access-scope
   requirement) for both Set A routes.
3. Adjudicate every Set B route: `TENANT_PROVIDER_MUTATION_ADD`,
   `*_EXCLUDE`, or `PRODUCT_DECISION_REQUIRED` — from direct source
   evidence, never from the held-registry's module label alone.
4. `webhook_endpoint_management`: derive tenant server-side (mirror
   `MediaService`/`GeoService`'s `_require_trusted_tenant` pattern),
   compare to the client-supplied `tenant_id` Query param, reject
   mismatch.
5. `rag_query`: `RAGService` must accept `actor_tenant_id`; `_get_kb`
   must scope by `KnowledgeBase.tenant_id == actor_tenant_id` (confirm
   `KnowledgeBase` has a `tenant_id` column — if not,
   `IMPLEMENTATION_SCOPE_BLOCKED`).
6. Non-oracular foreign/missing responses for both routes.
7. Alternate-route/caller audit (`git grep` for direct service
   construction and direct method calls).
8. Full test matrix mirroring `tests/test_phase2f33_geo_zone_closure.py`'s
   category structure (authorization, tenant/object, service, privacy,
   Set B adjudication, coverage arithmetic) with a negative control for
   every positive.
9. A dedicated verifier script (`verify_2f35.py`) with `--selftest`.

## Canonical/held update rules

Update Set A routes' `guard_status` only after complete evidence. Add
only Set B routes adjudicated `TENANT_PROVIDER_MUTATION_ADD`, each
exactly once. Do not modify any row outside Set A/adjudicated Set B.

## Coverage arithmetic rules

`final_protected = 241 + c + h`, `final_denominator = 264 + a`, where `c`
= Set A routes closed (≤2), `a` = Set B routes added, `h` = added Set B
routes fully protected. Report exact route-level arithmetic — do not
force a round number.

## Regression requirements

Full `tests/test_phase2f*.py` suite, run twice, deterministic, zero new
failures. M01/N01/geo non-regression canaries re-run.

## Documentation requirements

Mirror the 42-file structure established in Slice 2F-33's
`docs/workflow-rearchitecture/phase-02a-slice-02f33/` directory, adapted
for the 2-module/9-held scope.

## Allowed final statuses

`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED`,
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`,
`SECURITY_CLOSED_PRIVACY_BLOCKED`,
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`,
`IMPLEMENTATION_SCOPE_BLOCKED`, `INCOMPLETE`. Every status scoped only to
`webhook_endpoint_management` + `rag_query` (+ any Set B additions) —
never application-wide.

## Approval gate / stop condition

Stop at Slice 2F-35's own approval gate. Do not select a further module.
Do not touch Set C. Do not begin Slice 2F-36 in the same run.
