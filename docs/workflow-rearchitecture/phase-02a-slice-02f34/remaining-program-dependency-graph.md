# Remaining Program Dependency Graph (WS12)

## Module → files → slice

```
2F-35 (Critical destructive / security-sensitive)
  webhook_endpoint_management -> app/engines/webhook/{router,service}.py
  rag_query                   -> app/engines/rag/{router,service}.py
  held: security (2), documents (3), rag (4)

2F-36 (Enterprise / tenant-admin / operational)
  enterprise_grid_saved_views       -> app/engines/enterprise_grid/{router,services}.py
  enterprise_grid_preferences_exports -> app/engines/enterprise_grid/{router,services}.py  [shares file with saved_views, SAME slice]
  admin_catalog_provider_setup      -> app/engines/admin_catalog/{brand_provider_router,recommendation_router,
                                        service_option_provider_router,brand_service,
                                        recommendation_engine_service}.py
  profile_technician_self_service   -> app/engines/profile/{router,service}.py
  profile_universal_self_service    -> app/engines/profile/{router,service}.py  [shares file, SAME slice]
  marketing_automation_provider     -> app/engines/marketing_automation/provider_router.py
  analytics_provider_reports        -> app/engines/analytics/provider_router.py
  held: appointments(7), ds(6), inventory(5), catalog(2), dispatch(2), settings(2),
        serviceability(1), chat(1), bookings(1), notifications(1)

2F-37 (Financial / product-policy / N01 integrity / remaining held)
  platform_commerce_deposit -> app/engines/platform_commerce/{router,service}.py
  held: pricing(9), commerce(4), payments(1), subscriptions(1), compliance(2)
  N01 domain-integrity backlog (non-canonical, separate sub-scope)

2F-38 (Final reconciliation and certification)
  No module implementation. Re-verifies 2F-35/36/37 output, canonical/
  matrix final recount, held-registry final state, Migration 144
  readiness, readonly@ disposition, role constraint application.
```

## Shared infrastructure (all slices)

- `app/core/permissions.py` — every module identified this slice can
  close using an EXISTING guard (`require_tenant_mutation_permission`,
  `require_mutation_access_scope`). No new guard function is anticipated.
  If a future slice does need one, it must add it strictly additively
  (never modify an existing guard's behavior another slice depends on).
- `docs/.../tenant-mutation-endpoint-inventory.csv` and
  `mutation-enforcement-matrix.csv` — touched by every implementation
  slice. **Must execute sequentially (2F-35 → 2F-36 → 2F-37 → 2F-38), not
  in parallel** — each slice's frozen starting hash is the prior slice's
  exact final hash.

## No conflicts requiring same-slice merging beyond what's already assigned

Every module maps to exactly one engine's router/service files, and no
two DIFFERENT slices touch the same engine's files. The two cases where
two modules share a file (`enterprise_grid` router/services;
`profile` router/service) both have both modules already assigned to the
SAME slice (2F-36), so no cross-slice conflict exists. See
[cross-slice-file-conflict-audit.csv](cross-slice-file-conflict-audit.csv)
for the exhaustive per-file audit.
