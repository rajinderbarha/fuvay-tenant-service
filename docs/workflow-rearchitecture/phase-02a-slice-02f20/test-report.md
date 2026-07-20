# Test Report — Slice 2F-20

## New suite: `tests/test_phase2f20_compliance_provider_authorization.py`
27 tests, 27 passed, 0 failed.

Classes:
- `TestRequireTenantOwnerMutation` — the dependency's role admission
  (`tenant_owner`, `super_admin`) and access-scope denial behavior.
- `TestProviderRouterDependencyWiring` — all 6 mutation routes +
  `download_export` resolve `require_tenant_owner_mutation` in their
  `dependant` tree (source-level introspection, not runtime walk, for
  the GET route).
- `TestWithdrawConsentTenantFix` — `revoke_consent` receives and forwards
  a real `tenant_id`, no longer hardcoded `None`, for the provider
  (tenant-scoped) call path.
- `TestCreateRequestAtomicMetadata` — `metadata_json` is passed directly
  into the `ComplianceRequest` constructor (no separate post-insert
  UPDATE); includes the regression test that surfaced the pre-existing
  `VALID_SUBJECT_TYPES`/`VALID_REQUEST_TYPES` gap (fixed this slice).
- `TestExistingTenantScopingUnchanged` — confirms the pre-existing
  `metadata_json["tenant_id"].astext` WHERE-clause scoping on reads is
  untouched and still fails closed on missing/malformed values.

## Compliance regression: `pytest tests/ -k "compliance or dpdp"`
573 passed, 0 failed, 0 errors.

## Canonical coverage / recount suites (combined)
`test_phase2f14a_field_ops_alternate_route_and_coverage.py` +
`test_phase2f17a_global_mutation_inventory.py` +
`test_phase2f20_compliance_provider_authorization.py`:
64 passed, 0 failed. Both baseline-recount assertions now read
`assert protected == 206` against `assert total == 226`.

## Full repository sweep: `pytest tests/`
11010 passed, 45 failed, 109 errors, 13 skipped (518.88s) — identical
composition to the pre-existing baseline from every prior slice; zero
matches to compliance/dpdp in the failure output (see
`regression-report.md` for detail).

## Overall
All new and pre-existing tests relevant to this slice's scope pass. No
regression introduced.
