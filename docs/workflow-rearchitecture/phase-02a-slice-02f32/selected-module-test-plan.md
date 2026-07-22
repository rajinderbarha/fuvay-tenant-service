# Selected Module Test Plan (for the future implementation slice)

Not executed this slice. Planned categories, mirroring the
`tests/test_phase2f31a_n01_residual_closure.py` structure:

1. **Authorization** — `require_permission(P.TENANT_UPDATE)` unchanged on
   `delete_zone`; admitted-role set proof before/after.
2. **Tenant/object** — `GeoService` derives `actor_tenant_id` server-side;
   `delete_zone` compares it to `ServiceZone.tenant_id` before the query;
   negative control proves the raw unscoped query string is gone.
3. **Service** — constructor requires `actor_tenant_id`/`actor_role`;
   fail-closed for `None` tenant context (mirroring
   `_require_trusted_tenant`).
4. **Privacy** — foreign-tenant and missing-zone responses
   indistinguishable (same exception type/args).
5. **Caller audit** — `git grep` proves no direct-call bypass.
6. **Coverage arithmetic** — 239/262, 23 unprotected.
7. **Held-route non-regression** — `create_zone`/`update_location` remain
   pending and non-canonical after the change (see
   [held-route-adjudication-contract.md](held-route-adjudication-contract.md)).
8. **Regression** — full `tests/test_phase2f*.py` suite, twice, 0 new
   failures.

Every positive assertion must have an adjacent negative control, per this
program's established test-quality bar.
