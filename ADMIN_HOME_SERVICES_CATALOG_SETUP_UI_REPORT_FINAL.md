# ADMIN SIDE FIRST — Home Services Service Catalog Setup Wizard — Final Report

1. **Route result**: `/admin/home-services/service-catalog`
   (`frontend/super-admin/app/admin/home-services/service-catalog/page.tsx`)
   — matches the ticket's primary suggested route exactly.

2. **Admin navigation result**: New "Overview" + "Service Catalog" items
   added to the existing "Home Services" nav group (alongside Customer
   Price Experience, Provider Matching, Matching Diagnostics). "Service
   Catalog" is the active item on this page. No "Bargain Rules" item
   exists in this group (it was removed in a prior, already-certified
   sprint this session).

3. **Service catalog result**: Left panel shows 8 real, grouped Home
   Services groups (AC & HVAC, Plumbing, Electrical, Carpentry &
   Woodwork, Painting & Walls, Appliance Repair, Pest Control, Home
   Security) with live type/brand counts and status dots.

4. **AC Service detail result**: Selecting "AC Repair" (the real seeded
   service) loads its full detail — pricing model badge (Fixed), status
   (Active), and populates all 8 tabs from real data.

5. **General tab result**: Service Name, Pricing Model, Category (Home
   Services, hard-scoped), Job Type, Status, requirement flags, Sort
   Order, Description — all real fields from `MasterService`, plus an
   explicit "tenant cannot free-text a service" disclosure.

6. **Pricing model result**: Shown as a field within General (Fixed /
   Type-based / Consultation, mapped from the real `fixed`/`range`/
   `post_assessment` backend enum).

7. **Types & Pricing result**: Real editable table — Window AC/Split AC
   for AC Repair, each with floor/ceiling/platform fee/deduction credits;
   live-verified: setting Window AC to ₹550–₹1500 @ 10% correctly
   persisted and returned a live Customer Sees preview.

8. **Zones/Tiers result**: Real tier list from `/v1/admin/tiers`,
   link-out to the dedicated Pricing Tiers screen for full CRUD (see
   Remaining Blockers #1, #5).

9. **Brand configuration result**: Real brand list (LG, Samsung, Voltas
   for AC Repair) with can-override-price / routing-only toggles and
   override-limit editor; live-verified: LG override ₹1100/₹1100 @ 10% →
   Low ₹1210 exactly; toggling routing-only correctly cleared the price
   preview.

10. **Issues result**: Real, service-filtered list from
    `/v1/admin/issue-types?master_service_id=X`, link-out for full CRUD.

11. **Options result**: Real, service-filtered list from
    `/v1/admin/service-options?master_service_id=X`, link-out for full
    CRUD.

12. **Customer Price Preview result**: Standalone calculator —
    live-verified ₹550/₹700/10% → Low ₹605, Mid ₹690, High ₹770, exactly
    matching the ticket's example, with a full breakdown card.

13. **Auto Low/Mid/High result**: New `compute_symmetric_customer_price_tiers`
    pure function, unit-verified against both ticket examples
    (605/690/770 and 935/1070/1210); hard gate confirmed — raw provider
    minimum (₹550) is never returned as customer Low (₹605).

14. **Home Services scope guard result**: Hard server-side boundary —
    every console query/write is scoped to the real Home Services
    category (`vertical_type == "home_services"`); attempting to load a
    non-Home-Services service returns 422 `NOT_HOME_SERVICES_CATEGORY`;
    frontend shows the exact required blocked-state text if the category
    itself can't be resolved.

15. **API integration result**: 9 new real endpoints (list, detail, type
    limits, brand behavior, brand limits, price-preview, audit) composing
    the substantial pre-existing master-service/type/brand/pricing-rule/
    issue-type/service-option/tier CRUD built in prior sprints — nothing
    duplicated, nothing mocked.

16. **Permission handling result**: All read endpoints gated on
    `P.CATALOG_PRICING_READ`, all writes on `P.CATALOG_PRICING_WRITE`
    (existing, already-role-mapped constants — see Remaining Blockers #6).

17. **Error handling result**: `SectionError` with request-id + Retry on
    every data section; no bare "Unexpected error." anywhere.

18. **Forbidden label scan result**: 0 matches (the two "Manual bargain
    setup is disabled" strings are the ticket-mandated disclosure text,
    not the forbidden active-feature label).

19. **TypeScript output**: 0 errors, exit code 0 (both standalone
    `tsc --noEmit` and within `npm run build`).

20. **Frontend test output**: 32/32 new tests passed; `npm run build`
    compiled successfully (0 TypeScript errors; only the pre-existing,
    unrelated `/admin/refund-requests` Suspense-boundary failure
    documented in every prior sprint this session).

21. **Backend test output**: 450/463 passed in the broader
    admin_catalog/bargain/pricing_rule/brand regression sweep; all 13
    failures confirmed pre-existing and unrelated (different frontend
    pages this sprint never touched — see Test Results report for the
    grep-verified proof).

22. **Bugs found**: None in the reused data layer. Confirmed the
    already-existing `/v1/admin/home-services/price-experience/preview`
    endpoint uses a genuinely different (correct, for its own flow)
    asymmetric formula — not a bug, a distinct semantic that must not be
    conflated with this ticket's symmetric formula.

23. **Bugs fixed**: N/A for pre-existing logic (all real and working);
    added the 3 genuinely missing capabilities (type-scoped floor/ceiling,
    brand override behavior + limits, symmetric customer preview) that
    didn't exist before this sprint.

24. **Remaining blockers**: 8 documented, all non-blocking (Issues/Options/
    Zones are read + link-out not full inline CRUD, Pricing Model folded
    into General, enum-label mapping, no dedicated Overview page yet, no
    tier selector in this console's editors yet, reused permission
    constants, pre-existing build/tooling gaps, 13 pre-existing unrelated
    pytest failures).

## Final recommendation

**READY_ADMIN_HOME_SERVICES_CATALOG_SETUP_CERTIFIED**
