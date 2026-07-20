# Canonical Inventory Contract

## The two canonical CSVs
1. `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv` — row-level tenant/provider mutation inventory. THIS is the file the canonical X/Y headline is computed from.
2. `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv` — per-module summary (different denominator convention: total mounted mutation routes per module, not tenant-only — see 2F-15C's `canonical-csv-structure.md` for why these intentionally differ).

## Column definitions (CSV #1)
| Column | Meaning |
|---|---|
| `method` | HTTP method(s) |
| `path` | Mounted path (canonical route identity key, together with `method` and `module_source_file`) |
| `endpoint_name` | Python function name |
| `module_source_file` | Dotted module path (e.g. `app.engines.compliance.provider_router`) |
| `auto_classification` | First-pass heuristic classification (not authoritative) |
| `dependency_names` | Pipe-separated FastAPI dependency names attached to the route |
| `guard_status` | The authoritative protection classification (see below) |
| `required_action` | Free-text remediation note |
| `verification_level` | Free-text slice/verification provenance note |

## Route identity key
`(method, path, module_source_file)` — confirmed unique via `test_no_duplicate_rows` (`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`), re-verified this slice, unchanged.

## Protection status field and the `VERIFIED` set
`guard_status` is authoritative. A row counts as protected iff `guard_status` is in:
```python
VERIFIED = {
    "TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
    "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
    "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED",
}
```
(`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount.VERIFIED`, unchanged this slice).

## Included-in-tenant-denominator field
There is no dedicated boolean column — inclusion is implicit: EVERY row physically present in this CSV counts toward the denominator (Design A, established in Slice 2F-15C's `canonical-csv-structure.md`: customer-self-service, platform-only, and false-positive rows are PHYSICALLY REMOVED from this file, not flagged with a column).

## Verification-level field
Free-text, e.g. `SLICE_2F6A_VERIFIED`, `RUNTIME_VERIFIED (live route+dependency introspection)` — provenance notes, not machine-checked, but useful for tracing which slice last touched a row.

## Recount test
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount::test_canonical_totals` — asserts exact `total`/`protected` counts. This is the single source of truth for the canonical numerator/denominator, re-verified and updated this slice.

## Starting point confirmed
Before this slice's row-level recount, the file contained exactly **227 rows, 186 protected** (matching the approved 2F-16A baseline exactly — confirmed by direct count, not assumed).
