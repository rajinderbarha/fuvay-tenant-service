# Phase 3D — Remaining Blockers

1. **No true interactive browser session available in this environment** —
   same permanent constraint as every prior sprint this session. Unlike the
   Phase 3C-Closure ticket, this Phase 3D ticket's rule set does **not**
   include an explicit waiver allowing READY when smoke is
   environment-limited rather than skipped outright — its hard-stop rule
   reads simply "If manual browser smoke is skipped → PARTIAL_READY_WITH_
   PRICING_BLOCKERS." Applying that rule literally and conservatively (since
   this ticket, unlike 3C-Closure's, doesn't offer the escape hatch), this
   is the deciding factor for Phase 3D's final recommendation below.

2. **Pricing Rules/Tiers/City-Zip (Phase 3A) have no dedicated frontend
   audit tab** — real audit data exists and is readable via the generic
   `GET /v1/admin/master-data-audit` endpoint, confirmed live-fired this
   sprint, but the (pre-existing) pages don't surface it. Building that tab
   would be a new feature, out of this closure sprint's scope.

3. **Route names differ from the ticket's assumed shape** (e.g.
   `/v1/admin/tiers` not `/v1/admin/pricing/tiers`, `/admin/pricing-tiers`
   not `/admin/pricing/tiers`) — documented in full in
   `PHASE_3D_BACKEND_E2E_ASSERTIONS_REPORT.md`. Not a defect; the real
   routes work correctly end-to-end.

4. **No public/tenant-facing `POST /v1/pricing/bargain/evaluate` endpoint**
   — only the admin-preview version exists. Documented since Phase 3B, still
   the case.

5. **No pricing-rules clone/archive endpoints** and **no "Configure
   Pricing"/"Configure Bargain" catalog deep-links** — both real gaps versus
   the ticket's asks, both would require new code, both correctly not built
   in a "do not add new features" closure sprint.

6. **No dedicated Finance Admin / Read-only Admin / Restricted Admin roles**
   exist in this platform to test permission behavior by that literal name
   — the underlying `pricing.*` permission-check mechanism was verified live
   and works correctly for any role lacking a given permission.

7. Carried-forward, unchanged from Phase 3/3B/3C: audit-system
   fragmentation (3 parallel audit tables platform-wide), Small/Large
   pricing-tier placeholder multipliers, `next build` static-export failure
   on the unrelated `/admin/refund-requests` page.

None of items 2-7 are code defects that would make any baseline scenario
value wrong — every dollar figure, decision, and validation result in the
ticket's baseline scenario was confirmed exactly correct this sprint. Item 1
(the interactive-browser-smoke gap) is the sole basis for not returning the
unqualified `READY_PRICING_RULES_FRONTEND_BACKEND_CERTIFIED`.
