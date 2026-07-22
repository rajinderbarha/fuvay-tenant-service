# Known Limitations — Slice 2F-3A

1. **The shadowed `staff_accept_job`/`staff_reject_job` functions remain in
   the codebase, unreachable** — left in place per the brief's explicit
   prohibition on deleting routes based on naming-similarity findings alone.
   A future cleanup slice, if ever approved, could remove them with a
   proper compatibility/retirement plan; not done here.
2. **`home_service_assignment`'s accept/reject implementation has no
   explicit tenant_id filter in `_load_job()`** — relies solely on
   assignment-ownership matching for isolation. Not proven exploitable
   (a cross-tenant assignment match would require a staff member from one
   tenant somehow being assigned a job in another, which the assignment
   creation path should prevent), but flagged as a documented,
   non-blocking observation for the future guard-application slice to
   examine more rigorously (e.g. add a defense-in-depth tenant check
   alongside the existing assignment check).
3. **`cancel_assignment`, `assign_job`, `reassign_job`, `schedule_job`
   (home_service_assignment.provider_router) were not independently
   re-verified for tenant/object-ownership correctness this slice** — out
   of the narrow overlap-adjudication scope (they have no competing route
   to adjudicate against); flagged for the future guard-application slice.
4. **The 14 execution-progress endpoints' `_assert_staff_owns_job`
   mechanism was not independently re-verified for every edge case** this
   slice (e.g. cross-tenant technician rejection specifically) — same
   reasoning as above.
5. **Whether the accept/reject duplication was an intentional incomplete
   migration or an accidental re-implementation remains UNVERIFIED** — no
   commit history, changelog, or code comment was found clarifying original
   intent. Documented as unverified rather than guessed.
6. **Other verticals' (`coaching_router`, `real_estate_router`) potential
   shadowing against their own assignment modules was not audited** — out
   of scope (this slice's mandate names only the 3 home-services modules).
7. **1 pre-existing, unrelated flaky test** in the targeted regression run
   (`TestRealConcurrencyMatrix::test_concurrent_debits_never_produce_negative_balance`)
   — passes in isolation, fails intermittently under combined-suite load;
   not caused by this slice's changes (zero billing/concurrency code was
   touched).
8. **A full-repository test run was not completed** — 806 combined tests
   (490 targeted + 316 broader partition), 1 pre-existing unrelated flake,
   0 real failures, is the evidence base.
9. **`readonly@demo-ac-services.local` remains untouched; migration 144
   remains unapplied; `tenant_engine.router` and `provider_portal.router`
   were not modified** — all confirmed per the brief's explicit exclusions.
