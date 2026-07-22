# Known Limitations — Slice 2F-25A

1. **CURRENT_CANONICAL_COVERAGE is not application-wide completeness.** 229 is
   what is currently known. The generic-prefix blind spot 2F-25 exposed may
   hide tenant mutations in other engines. Only a persona-based global sweep
   can close this.

2. **This slice's tests are deterministic doubles, not live integration.** The
   infrastructure was available (see `environment-test-evidence.md`) but the
   36 new tests use session doubles and source introspection by design.
   Security claims rest on SQL-predicate inspection and no-write assertions,
   not on executed cross-tenant requests. An executed-exploit suite would be
   stronger; it is deferred, not claimed.

3. **Node-ID regression comparison cannot see swallowed exceptions.** The
   `field_ops` regression 2F-25 introduced was invisible to it: the failure is
   caught by `except Exception` and logged, and no test covers the path. Exact
   node-ID comparison is necessary but **not sufficient** — it detects test
   outcomes, not silently degraded behaviour.

4. **Same-tenant granularity remains coarse** on `get_review_request` and
   `list_by_customer` — any principal of the owning tenant may read that
   tenant's rows. Narrowing would be invented policy (product decision #3).

5. **No job-status gate on `create_request`** (product decision #2).

6. **`list_by_customer` does not filter hidden/rejected states** from the
   tenant's own rows (product decision #5).

7. **`_recompute_aggregate` was not re-derived.** Whether hidden/rejected
   reviews contribute to aggregates is unproven — one reason the aggregate
   read is not claimed public.

8. **Technicians are not assignment-scoped** — they fall under the tenant
   predicate (product decision #4).

9. **The legacy reply contract is still broken** and `resolve` still 403s for
   tenant callers — both carried from 2F-25, both deliberately unfixed.

10. **Slice-2D canaries untouched.** One still fails; the file count it tracks
    is unchanged by this slice (no new
    `require_tenant_mutation_permission` caller was added).

11. **`mutation-enforcement-matrix.csv` remains stale**, per standing
    convention.
