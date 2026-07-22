# Test Quality Report

Every positive assertion added or modified this slice has an adjacent
negative control:

| Positive | Negative control |
|---|---|
| Scope guard admits all roles | `test_guard_does_not_narrow_admitted_roles` fails if a role-restricted dependency is substituted |
| Tenant check runs on mutation routes | `test_missing_tenant_context_fails_closed` fails if `actor_tenant_id is None` doesn't raise |
| File-name sanitized | `test_raw_client_file_name_no_longer_reaches_storage_key` fails if the raw f-string returns |
| No direct-call bypass | `test_media_service_mutation_methods_have_no_other_internal_callers` fails if a new call site appears anywhere in `app/` |
| Historical artifacts unchanged | `TestHistoricalArtifactsImmutable` fails if either CSV is rewritten again |
| Coverage arithmetic | `test_coverage_is_238_of_262`/`test_unprotected_is_24` fail on any further canonical edit without a matching test update |

`verify_n01_2f31a.py --selftest` independently proves all 21 verifier
conditions (a superset/parallel check, not a duplicate of the pytest file)
fire when violated. No test in this slice asserts a tautology (`True ==
True` or equivalent) — every assertion reads a real file, live route, or
`inspect.getsource` result.
