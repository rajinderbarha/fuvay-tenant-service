# ADMIN-TENANT-E2E-09 — Remaining Blockers

None of the following are P0 route/certification-breaking blockers for THIS sprint's strict scope (tenant service setup + coverage UI/API correctness), but are real findings worth carrying forward:

1. **Usage credit balance is 0.0000, not 3958.00** (`tenant_wallets` for Demo AC Services). This has drifted since the prior finance sprint due to real consumption (`lifetime_consumed=1100`). The real matching backend (`match_and_price`) treats credits as a gating factor for bookability — this is a genuine live risk to the tenant's actual bookability, but topping up the wallet is a finance/payment action explicitly out of this sprint's scope. Recommend a dedicated top-up or finance-sprint follow-up before relying on Demo AC Services for future live-matching tests.

2. **access_scope not enforced on any of the 12 tenant service-setup/coverage mutation endpoints** in `app/engines/admin_catalog/tenant_router.py` (set-types, set-brands, set-type-pricing, set-brand-pricing, publish, save-draft, enable-service, disable-service, update-enabled-service). Confirmed live: a `tenant.readonly` (customer_support_limited) token reaches full business-logic validation (422) rather than being blocked with 403. This is the same class of gap as the already-known `PUT /v1/provider/business-profile` issue from a prior sprint, now confirmed to also cover these endpoints. Fixing this was judged out of this sprint's "minor fix" allowance given its breadth (12 endpoints) — recommend a dedicated access_scope hardening pass across the whole `tenant_router.py`.

3. **Publish Readiness UI does not include a usage-credit-balance check**, even though the backend's real matching eligibility gate depends on credits. Minor readiness-UX gap, not a route break.

4. **Area-level per-type-per-brand coverage rows are sparse** (`tenant_service_area_services` has only 1 row — Split AC+LG in 141001 — despite both Split AC+LG and Window AC+LG having full tenant-side pricing configured). Window AC's own area-coverage row may not yet exist; this is a data-completeness observation, not a code defect, and was not created/fixed this sprint to avoid unnecessary mutation of the shared tenant.

5. Full live customer-facing `match-and-price` browser flow (Part 10) was verified via code review rather than a live end-to-end browser run, per the spec's own safety guidance and given finding #1 above (zero credit balance would make a live test's failure ambiguous — coverage vs. credits). Recommend re-running as a live browser test once the credit balance is restored.

6. A pre-existing (not introduced by this sprint) React hydration warning was observed on `/dashboard` (`<div>` nested inside `<p>` in a `Skeleton` usage at `app/(tenant)/dashboard/page.tsx:182` via `components/shared/ui.tsx:273`). Out of this sprint's strict scope (dashboard is only a smoke-tested peripheral route here, not one of the 5 core setup/coverage surfaces) — flagged for a future UI-polish sprint, not fixed here.

None of the above prevented certifying the actual in-scope surfaces (Service Setup, Service Coverage, Type-Specific Brand Pricing, Provider Price Range, Publish Readiness mechanics, API contract, mock/label scans, enterprise UI quality) as real, correct, and working.
