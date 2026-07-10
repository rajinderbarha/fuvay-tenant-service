# FINAL-L5-02 — Authorization Matrix & Test Report

(Consolidates Parts 6 authorization matrix + authorization test report.)

## Live-verified matrix (representative endpoint: `GET /v1/admin/tenants`)

| Role | Result | Expected |
|---|---|---|
| Anonymous | 401 | 401 ✓ |
| Customer | 403 | 403 ✓ |
| Technician | 403 | 403 ✓ |
| Tenant Owner | 403 | 403 ✓ |
| Tenant Read Only | 403 (in-process regression) | 403 ✓ |
| Tenant Manager | 403 (in-process regression) | 403 ✓ |
| Super Admin | 200 | 200 ✓ |

All verified live this sprint except tenant_readonly/tenant_manager which are covered by the 21-test in-process RBAC regression suite (`tests/test_final_l5_01b_admin_tenant_rbac.py`, 21/21 passing).

## Authorization-before-validation (critical rule)
**Verified architecturally and empirically**: `require_super_admin` is a FastAPI dependency resolved during `solve_dependencies`, before the endpoint body/service/DB runs. In the RBAC regression suite, rejected roles (403) never trigger the mocked-DB pagination `TypeError` that authorized requests do — proving unauthorized requests are rejected **before reaching business/data logic**. This satisfies "Authorization must execute before business validation" and "Unauthorized mutation must return 403 before business validation" for the certified endpoints.

## Scope of coverage
The full authorization matrix asks for every mutation across ~14 domains (tenant profile, service areas, availability, pricing, coverage, publishing, assignment, job status, completion, settings, notifications, rules, finance) × 10 roles. This sprint **live-certified the admin-tenant read surface** (the one with a known prior vulnerability, now fixed and regression-covered) and confirmed the auth-before-validation pattern. **Per-mutation 403-before-422 testing across all 14 domains was not exhaustively performed** — the pattern is proven on the fixed endpoints; extending it to every mutation is the honest remaining work.

## Result
**Certified for the admin-tenant surface (the known-vulnerable one), with the auth-before-validation invariant proven.** Broader per-domain mutation authorization is representative, not exhaustive — stated plainly.
