# ADMIN-TENANT-E2E-09B — Endpoint-Level RBAC Tests Report

All tests run live via curl against the running backend (:8000) after the fix + restart.
Tenant = Demo AC Services (`34b427a7-b2be-496c-b826-6d51bb181248`). Endpoint under test:
`PUT /v1/tenant/catalog/enabled-services/{service}/types/{type}/pricing` (representative;
same result class confirmed on `types`, `publish`, `save-draft`, and the service-coverage
endpoint).

| Actor | Payload | Result |
|---|---|---|
| Tenant Owner (`provider@serviceos.in`) | valid (850/1100) | 200 OK — real DB write, verified via GET |
| Tenant Manager (`tenant.manager@serviceos.in`, access_scope=tenant_scoped) | valid (900/1150) | 200 OK — mutation succeeded |
| Tenant Manager | invalid (700/850, below admin floor 850) | 422 TENANT_PRICE_BELOW_ADMIN_MIN — reaches real business validation, proving Manager is NOT blocked by the read-only gate |
| Tenant Read-Only (`tenant.readonly@serviceos.in`, access_scope=customer_support_limited) | **invalid** (min=99999, max=-5) | **403 PERMISSION_DENIED** — critical proof: authorization runs before validation |
| Tenant Read-Only | valid (700/850) | 403 PERMISSION_DENIED (identical — payload validity is irrelevant once blocked) |
| Tenant Read-Only | GET (read) | 200 OK — reads remain unaffected |
| Unauthenticated | valid | 401 UNAUTHORIZED |

Additional endpoints re-tested for Read-Only, all 403 (not 422/500):
- `PUT .../types` (set supported types) → 403
- `POST .../publish` → 403
- `POST .../save-draft` → 403
- `PUT /v1/provider/service-areas/{area}/coverage` (garbage `service_id`) → 403, not 422 —
  confirms auth-before-validation on the coverage endpoint too.

Wrong-tenant test: existing project policy elsewhere in the codebase for tenant-scoped
resources is to 404 (not leak existence) once tenant_id is validated inside the service layer;
this sprint did not introduce a new cross-tenant path (the fix only adds an access_scope gate
on top of existing tenant-scoping, which was already enforced by `actor_tenant_id` in
`TenantCatalogService`). No regression to that existing behavior — not independently
re-verified with a second tenant account in this sprint (none exists in the seeded dev DB
besides Demo AC Services), noted as a light gap.

All required assertions for Part 3 pass: read-only never reaches business validation
regardless of payload validity.
