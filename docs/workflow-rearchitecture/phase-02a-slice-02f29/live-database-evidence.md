# Live Database Evidence - Slice 2F-29

PostgreSQL, Redis and the API server were REACHABLE throughout this slice
(ports 5432 / 6379 / 8000).

**Honest scope statement:** the M01 authorization proofs in this slice are
asserted with deterministic in-process doubles (mocked `db.execute`/`db.add`)
plus live route/dependency introspection against the real mounted application.
They are **not** live end-to-end HTTP transactions against seeded tenant rows,
and no concurrency or production-database claim is made.

No existing real user or tenant record was created, mutated or deleted by this
slice. `readonly@demo-ac-services.local` was not touched.

What IS live evidence:
- Route mounting, dependency chains and `access_scope_gated` status were read
  from the real running application object.
- Model/table separation (`api_keys` vs `tenant_api_keys`) was read from the
  real SQLAlchemy metadata.
- `PermissionChecker.has` grant/deny/isolation behaviour was exercised against
  the real permission registry.
