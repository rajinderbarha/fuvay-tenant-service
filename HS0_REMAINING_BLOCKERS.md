# HS0 — Remaining Blockers (all non-blocking for certification)

1. **Dual navigation source architecture** — both frontends have a live,
   hardcoded nav array inside `components/layout/{Admin,Tenant}Layout.tsx`
   *and* a separate, currently-unused `lib/nav-config.ts`. This sprint
   fixed the real bug (duplicate/forbidden items in the live
   `TenantLayout.tsx` array) and kept `nav-config.ts` in sync for
   consistency, but did not resolve the underlying duplication. See
   `HS0_MANUAL_REVIEW_FILES.md`.
2. **218 of 221 root-level markdown reports not individually reviewed**
   — only the Home-Services-pricing/bargain lineage was audited for
   obsolescence this sprint. A dedicated documentation-cleanup sprint is
   needed for the rest.
3. **42 pre-existing test failures remain** in the full suite, none
   caused by this sprint (net change: -2 failures). Concentrated in
   `test_sprint34a_ui_foundation.py`, `test_sprint34c_master_data.py`,
   `test_sprint38_universal_catalog.py`, `test_sprint34k_navigation.py`,
   `test_p0_tenant_portal_compliance.py`, and one assertion in
   `test_phase3c_frontend_certification.py` — all asserting on UI-shell/
   nav-config structure that drifted in earlier, unrelated sprints. Out
   of HS0's Home-Services scope; not fixed.
4. **Baseline plan/limit/deposit/credit values not individually
   re-verified** (Plan="Starter Home Services", Service Area Limit=5,
   Staff Limit=5, Security Deposit=₹5000, Included Usage Credits=1000) —
   tenant identity, location, and the full price-calculation example were
   verified against the real DB and the real pricing formula; the
   package/plan-level config values were not (out of this sprint's
   route/menu/test-cleanup scope).
5. **`/admin/pricing` label proximity** — the platform-wide city-tier
   floor-price page's sidebar label ("Pricing Rules") is close enough to
   the Home Services "Pricing Rules" label to potentially confuse an
   admin, even though they're legitimately different, vertical-agnostic
   vs. vertical-scoped features. Not renamed (outside the ticket's
   explicit forbidden-label list).
6. **Stale-data script coverage is not exhaustive** — 6 target checks
   covering tenants/tenant_service_types/tenant_service_brands/tenant_
   services/provider_availability_rules/bookings were implemented and
   verified live; other tables not explicitly named in the ticket
   (customer_booking_drafts, service_bookings, home_service_booking_
   drafts) were not added as cleanup targets this sprint.

None of the above block the tenant/admin Home Services menu, routes, or
test-suite cleanup itself — every ticket-specified forbidden item was
confirmed removed from live navigation, every ticket-specified canonical
route was confirmed real and reachable, the stale duplicate-availability-
rule data bug was found and fixed live, and the pricing baseline example
matches exactly against the real formula.
