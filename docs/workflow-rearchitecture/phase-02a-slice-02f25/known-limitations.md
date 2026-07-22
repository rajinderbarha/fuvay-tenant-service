# Known Limitations — Slice 2F-25

1. **The prefix-based canonical sweep may still be incomplete.** This slice
   found three tenant mutations that were never candidates because they sit on
   a generic `/v1/reviews/*` prefix rather than `/v1/provider|staff|tenant/*`.
   The same blind spot could hide other routes on other generic prefixes. This
   slice reconciled the review engine only — **it did not re-sweep the whole
   application on a persona basis**, which is out of scope. The 229 denominator
   is therefore "complete as far as the prefix convention plus this engine",
   not proven application-wide.

2. **Three legacy reads remain unscoped**, disclosed rather than claimed:
   `GET /aggregates/{entity_type}/{entity_id}`,
   `GET /requests/jobs/{job_id}`, and `GET /customers/{customer_id}` for
   non-customer roles. They return aggregate figures and request status, not
   review content. Privacy closure is asserted for the review-content surface,
   with these named as residuals.

3. **The legacy reply route is broken from the UI** — the portal sends
   `reply_text`, the route reads `body["reply"]` (KeyError -> 500). Pre-existing
   and deliberately not fixed; repairing it would enable a dead write path into
   the superseded table.

4. **The tenant portal calls `resolve`**, which is `require_super_admin` — a
   guaranteed 403 for tenant users. Pre-existing, not fixed.

5. **No live database or HTTP server.** All 49 new tests are deterministic
   source, signature and session-double assertions. The cross-tenant fixes are
   proven by the SQL predicate being present in the WHERE clause and by denial
   paths writing nothing — not by an executed request.

6. **Two live review stacks now coexist**, both secured. That is a
   maintenance burden and a product decision, not a security gap.

7. **`_assert_owns` remains role-conditional.** It is now correctly documented
   as a customer-self-service guard rather than a tenancy boundary, and tenant
   isolation no longer depends on it — but the asymmetry remains in the code.

8. **`create_review` survives on the service** though no mounted route reaches
   it (asserted). Removing it is cleanup, out of scope.

9. **Slice-2D canaries still failing, untouched.** One of them counts files
   using `require_tenant_mutation_permission`; that count moved 8 -> 9 because
   this slice adopted the existing scope-aware dependency. The test was
   already failing and still fails with the same node ID — no state change,
   and it was not rewritten.

10. **`mutation-enforcement-matrix.csv` remains stale**, per standing
    convention.
