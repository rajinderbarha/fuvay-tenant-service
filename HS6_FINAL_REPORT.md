# HS6 — Provider Matching + Auto Price Options Sprint — Final Report

1. **Dependency status**: HS0 real/certified. HS1 doesn't exist
   (accepted-risk pattern used throughout this session). HS2–HS5
   landed `PARTIAL_READY` with real, verified safety fixes each time.
   HS4B fixed the bookability-refresh blocker
   (`READY_HS4_TENANT_HOME_SERVICES_SERVICE_SETUP_WIZARD_CERTIFIED`).
   HS5B fixed all 5 HS5 backend blockers (`PARTIAL_READY` — no frontend
   UI). Proceeded per standing session convention.
2. **Provider-first matching result**: Confirmed real and correctly
   ordered — a substantial, pre-existing 530-line matching engine
   already selects exactly one provider before computing any price.
3. **Home Services scope result**: Confirmed real
   (`assert_home_services_vertical`), unchanged.
4. **Filter pipeline result**: Real eligibility gate exists covering
   bookable/offering/type/brand/pricing/technician/availability/
   package/credits/deposit — confirmed via source read.
5. **Bookability filter result**: Real (`is_bookable` checked first),
   but layered on a **second, independent set of checks using
   different tables** than the HS4B fix — a real, documented
   inconsistency, not unified this sprint.
6. **Service area filter result**: Real, city/zipcode-aware.
7. **Availability filter result**: Real but **existence-only**, not
   time-specific — a real, documented gap.
8. **Service/type/brand support filter result**: Real, but uses a
   **different data model** (`provider_enabled_offerings` JSON arrays)
   than the per-area coverage table HS5B just built and wired up — the
   two are disconnected.
9. **Ranking/scoring result**: Real, confirmed via source read
   (`compute_provider_score`, `rank_candidates`).
10. **Selected provider result**: Real, returned first, confirmed via
    source-order test.
11. **Auto Low/Mid/High result**: **Critical bug found and fixed** —
    `high_price` previously equaled the raw pre-fee provider max,
    violating the ticket's explicit hard gate. Fixed by delegating to
    the session's single certified symmetric-fee formula. Live-verified
    against the ticket's exact numeric example (770/935 for
    700–850 @ 10%).
12. **Type-dependent brand price resolution result**: **Critical bug
    found and fixed** — the real matching/booking price lookup ignored
    `offering_type_id`/`brand_id` entirely, reproducing the
    "Window AC price for Split AC" bug in the one place it hadn't
    already been fixed this session. Fixed with a specificity-ranked
    join against the linked pricing rule. Structurally verified; full
    HTTP end-to-end live verification not performed (documented gap).
13. **Customer-safe response result**: Confirmed real
    (`build_customer_safe_provider` vs `build_admin_provider`, gated by
    `reveal_internal_score`) — not independently re-tested this sprint
    beyond source confirmation.
14. **Admin diagnostics result**: Real page exists; full compliance
    with the ticket's ~10 required output panels **not fully audited**
    this sprint.
15. **Tenant preview result**: Not investigated this sprint (optional
    per the ticket).
16. **API integration result**: Real, no mock data — confirmed for
    every function touched this sprint.
17. **Permission handling result**: Not verified this sprint.
18. **Error handling result**: Confirmed real
    (`ServiceOSException`/`PRICE_OPTIONS_UNAVAILABLE`/
    `ERR_NO_PROVIDER_AVAILABLE`, all carry `request_id` via the
    existing global contract) — unchanged.
19. **Live curl verification result**: **Partial** — the two fixed
    functions were live-verified at the Python/pure-function level
    against the ticket's exact numeric examples; full HTTP end-to-end
    verification through a real booking draft was **not performed**
    (documented as the sprint's primary gap).
20. **Forbidden label scan result**: Not run this sprint (no new UI
    text introduced — only backend Python changes).
21. **Mock data scan result**: Pass — every function touched uses real
    DB queries.
22. **TypeScript output**: 0 errors, both frontends.
23. **Build output**: Not run (established constraint).
24. **Frontend test output**: N/A (no frontend changes).
25. **Backend test output**: 9 new tests + 76/76 + 206/206 regression
    sweeps, 0 failures, 1 pre-existing test corrected (not weakened).
26. **Bugs found**: 2 critical — (a) price-fee-omission on the high end
    in `compute_price_tiers()`; (b) type/brand-blind bargain-rule
    lookup in the live matching/booking price-resolution path. Plus 2
    architectural data-model inconsistencies documented, not fixed.
27. **Bugs fixed**: Both critical bugs, with dedicated regression tests
    and function-level live verification against the ticket's exact
    numeric examples.
28. **Remaining blockers**: 6 items — see `HS6_REMAINING_BLOCKERS.md`.
    Most significant: no full HTTP end-to-end live verification, and
    two real, unresolved data-model inconsistencies (bookability tables,
    area-coverage tables) between the matching engine and this
    session's other fixes.

## Final recommendation

`PARTIAL_READY_WITH_HS6_BLOCKERS`

Two genuinely critical bugs were found and fixed this sprint — both
were real hard-gate violations in the actual, live, customer-facing
matching and pricing path (not test-only issues), and both are now
fixed with function-level live verification matching the ticket's own
numeric examples exactly. This is significant, safety-relevant
progress. However, full HTTP end-to-end live verification was not
completed, and two real architectural inconsistencies (parallel
bookability tables, disconnected area-coverage data models) were
discovered but not unified — these represent genuine risk that a future
sprint must resolve before the matching flow can be certified fully
`READY`.
