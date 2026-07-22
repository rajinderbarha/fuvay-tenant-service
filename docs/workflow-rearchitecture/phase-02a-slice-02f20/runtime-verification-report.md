# Runtime Verification Report

## Route-level (re-run this slice)
All 6 selected (POST) routes confirmed live via
`inventory_mutation_routes.walk()`:

```
POST /v1/provider/compliance/consents/{consent_type}/withdraw           -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/compliance/customer-requests/{request_id}/tenant-response -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/compliance/requests                                    -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/compliance/requests/{request_id}/cancel                -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/compliance/requests/{request_id}/generate-export       -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/compliance/staff-requests/{request_id}/tenant-response -> TENANT_MUTATION_ROLE_SCOPE_AWARE
```
(all now resolve to `require_tenant_owner_mutation`, a member of the
established `VERIFIED` guard_status set, in place of the previous
`PERMISSION_ONLY_NOT_SCOPE_AWARE` classification.)

`download_export` (a GET route) is not tracked by the mutation-route
walker at all — as with every prior GET in this initiative, its
dependency was instead confirmed via direct source-level introspection
(`test_uses_require_tenant_owner_mutation[download_export]`, this slice's
test suite, which walks the route's own `dependant` tree) rather than the
POST/PUT/PATCH/DELETE-only runtime walker.

## Exit-condition checks (per this slice's Workstream 24)
- Any selected route remaining unclassified — NONE, all 6 fully classified.
- A tenant mutation lacking mutation scope — NONE, all 6 +
  `download_export` now use `require_tenant_owner_mutation`.
- Tenant authority able to be `None` — FIXED for `withdraw_consent`
  (the one place this was true); every other route never had this
  problem.
- Client metadata controlling tenant scope — NEVER true, confirmed
  structurally (no route accepts a tenant_id/metadata_json field).
- Subject identity client-trusted without relationship validation — NEVER
  true, confirmed structurally.
- Cross-tenant or cross-subject IDOR remaining — NONE found among the 6
  selected routes (existing `metadata_json` scoping mechanism, re-verified
  intact).
- Export worker unlocated without explicit `NOT_IMPLEMENTED` evidence —
  RESOLVED: conclusively documented as absent
  (`compliance-export-worker-discovery.md`), not silently unlocated.
- Worker not revalidating tenant and subject — N/A, no worker exists.
- Export download lacking ownership — NONE, `download_export`'s existing
  tenant/subject join check is intact and now additionally
  access-scope-aware.
- A weaker same-record route remaining — NONE
  (`compliance-alternate-route-audit.md`).
- Documentation disagreeing with runtime — cross-checked; all CSVs match
  the actual code.

## Test-suite exit code
`pytest tests/test_phase2f20_compliance_provider_authorization.py` exits
0 (27/27).
