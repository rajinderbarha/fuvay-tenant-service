# HS4 — Tenant Home Services Service Setup Wizard Sprint — Final Report

1. **Dependency status**: HS0 certified this session. HS1 doesn't exist
   as a real prior sprint (same accepted-risk pattern used throughout
   this session). HS2/HS2B landed `PARTIAL_READY_WITH_HS2_CATALOG_
   BLOCKERS`. HS3 landed `PARTIAL_READY_WITH_HS3_BLOCKERS` — its two
   safety-critical fixes (type-dependent brand pricing enforcement,
   duplicate-rule prevention) are real and live-verified, which is what
   HS4 actually depends on functionally. Proceeded per "continue only if
   instructed," consistent with standing session convention.
2. **Tenant setup route result**: `/tenant/setup/services` real,
   working, unchanged.
3. **Wizard UI result**: Functionally covers all 5 conceptual steps but
   does **not** match the ticket's literal step-indicator wizard
   presentation — pre-existing architecture.
4. **Service selection result**: Confirmed admin-approved-only (catalog
   card grid sourced from the Home-Services-scoped available-services
   endpoint fixed in an earlier sprint); no free-text service creation
   path exists.
5. **Type selection result**: Confirmed real, type-based services
   require at least one type before publish (`SERVICE_SETUP_INCOMPLETE`
   if missing).
6. **Provider price range result**: **Live-verified this sprint** — real
   `PUT .../pricing` calls against the real backend, both success and
   both boundary-violation cases tested fresh.
7. **Admin boundary validation result**: **Confirmed enforced
   server-side**, live-verified with real 422s and correct
   `request_id`s (`TENANT_PRICE_BELOW_ADMIN_MIN`/`_ABOVE_ADMIN_MAX`).
8. **Customer Low/Mid/High preview result**: Formula confirmed correct
   in the prior HS3 sprint (shared `compute_symmetric_customer_price_
   tiers`); Low/High include platform fee (hard gates pass).
9. **Type-dependent brand override result**: **Already fixed in a prior
   sprint, re-confirmed intact this sprint** (29/29 regression tests
   passing, no new work needed).
10. **Review & publish result**: **Live-verified this sprint** — real
    `POST .../publish` call succeeded, `setup_status` correctly updated
    to `"published"` with a `published_at` timestamp.
11. **Setup checklist impact result**: **Real bug found** —
    `POST /v1/provider/status/refresh` is a complete stub (no-op); a
    real publish did not update `is_visible`/`is_bookable`/
    `last_evaluated_at` on `GET /v1/provider/status`. Documented in
    detail in Remaining Blockers.
12. **API integration result**: Real, no mock data.
13. **Permission handling result**: Backend enforces `P.TENANT_UPDATE`;
    frontend has no permission-aware UI.
14. **Error handling result**: Existing error contract (RFC 7807 +
    `request_id`) confirmed working via live 422 responses this sprint.
15. **Forbidden label scan result**: **Pass, 0 matches.**
16. **Mock data scan result**: **Pass, 0 mock data.**
17. **TypeScript output**: 0 errors.
18. **Build output**: Not run (established constraint); tsc used as
    gate.
19. **Frontend test output**: N/A (Python static-inspection convention).
20. **Backend test output**: 142/142 passing across 6 wizard-scoped
    test files, 0 regressions (no code changed this sprint besides
    verification).
21. **Bugs found**: `POST /v1/provider/status/refresh` is a no-op stub
    — tenant bookability/visibility status doesn't actually update after
    a real service publish.
22. **Bugs fixed**: None this sprint — the discovered bug requires
    building real status-computation logic that doesn't currently exist
    anywhere in the codebase, which is beyond this sprint's remaining
    time budget. The type-dependent brand pricing and boundary
    validation fixes that HS4 depends on were already fixed and are
    re-confirmed intact, not newly fixed this sprint.
23. **Remaining blockers**: 6 items — see `HS4_REMAINING_BLOCKERS.md`.
    Most significant: the status-refresh stub bug, and the UI not
    matching the ticket's literal 5-step wizard structure.

## Final recommendation

`PARTIAL_READY_WITH_HS4_BLOCKERS`

The safety-critical requirements this sprint was actually gated on —
type-dependent brand pricing and provider price boundary enforcement —
are both real, live-verified, and correctly enforced server-side with
zero regressions. Publish itself works correctly for the checks it
performs. However, a real, previously-undiscovered bug was found this
sprint: the tenant bookability/visibility status does not actually
update after a successful publish (the refresh endpoint is a no-op
stub), which directly undermines the "Bookability status must update
only when all required checks pass" acceptance criterion. Combined with
the UI not matching the ticket's literal step-wizard structure and the
missing permission-aware UI, full `READY` certification would not be
honest.
