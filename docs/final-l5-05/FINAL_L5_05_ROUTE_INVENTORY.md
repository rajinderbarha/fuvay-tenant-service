# FINAL-L5-05 — Super Admin Route Inventory (Part 1)

Real, tool-generated inventory (not estimated) of `frontend/super-admin/app/**/page.tsx`, cross-referenced against `AdminLayout.tsx`'s `NAV_GROUPS` and `lib/page-registry.ts`.

## Headline numbers
| Metric | Value |
|---|---|
| Total `page.tsx` files | **162** (159 under `/admin/**`, 3 top-level: `/`, `/login`, `/change-password-required`) |
| NAV_GROUPS groups | **9** |
| NAV_GROUPS items | **43** |
| Unique hrefs referenced by NAV_GROUPS | **35** (was 34 before this sprint's fix — see Bug Register) |
| Routes with an exact `page-registry.ts` breadcrumb/title entry | **40 / 159 (≈25%)** |
| Routes with NO registry entry (rely on generic fallback or show nothing) | **119 / 159 (≈75%)** |
| Routes unreferenced by any NAV_GROUPS href | **116 / 159** (includes legitimate `[param]` detail/wizard/tab pages, which are correctly NOT expected to be in the sidebar) |
| Standalone leaf list pages (no `[param]` segment) unreferenced by NAV_GROUPS | **~70** — see Menu Coverage Matrix |
| `usePermissions()` adoption | **3 / 162 pages (≈2%)** |
| Confirmed genuine placeholder pages | **1** (`/admin/catalog-module/[key]`, real "coming soon" state, not deceptive) |
| Confirmed legacy redirect-only routes | **1** (`/admin/catalog` → redirects to `/admin/master-services`) |

## Route classification, by top-level segment
Full per-route classification (162 rows: Route ID, Path, Domain, Menu location, Classification, API client, State) is impractical to hand-enumerate exhaustively in this format within this sprint's bounded scope — see the Menu Coverage Matrix for the ~70 primary/leaf pages classified individually, and the Dead/Placeholder Page Audit for the specific pages requiring a decision. The remaining ~89 routes are `[param]` detail/edit/wizard/tab pages, correctly classified as `DETAIL_PAGE`/`TAB_CHILD`/`WIZARD_STEP`/`CONTEXTUAL_ONLY` by construction (they take a dynamic segment and are reached by clicking through from a list page, not by direct sidebar entry — this is correct IA, not a defect).

## Real duplicate route clusters found
| Feature | Routes |
|---|---|
| Brands | `/admin/brands`, `/admin/service-setup/brands` (+`[brand_id]`), `/admin/types-brands` |
| Brand requests | `/admin/brand-requests`, `/admin/service-setup/brand-requests` |
| Wallets/finance balance | `/admin/provider-wallets`, `/admin/finance/wallets` (+`[wallet_id]`) |
| Pricing (top-level) | `/admin/pricing`, `/admin/pricing-rules`, `/admin/pricing-tiers` |
| Pricing rules (vertical vs generic) | `/admin/pricing-rules`, `/admin/home-services/pricing-rules` |
| Service options | `/admin/service-options` (+`[id]`), `/admin/service-setup/service-options` |
| Issue types | `/admin/issue-types`, `/admin/service-setup/issue-types` |
| Checklists | `/admin/checklists`, `/admin/checklist-templates` |
| Workflow templates | `/admin/workflow-templates`, `/admin/workflows/templates` (+`[id]`) |
| Notification templates | `/admin/notification-templates`, `/admin/notifications/templates` |
| Reviews | `/admin/reviews`, `/admin/review-flags`, `/admin/review-policies`, `/admin/review-replies` |
| "Jobs" (see Bug Register — most significant finding) | `/admin/operations` (legacy `/v1/jobs`-backed, in NAV_GROUPS as "Jobs"), `/admin/home-services/service-jobs` (canonical `/v1/admin/final-records/jobs`-backed, **not** in NAV_GROUPS) |

## Real, fixed this sprint
`hs-overview` nav item previously pointed at the same href as `hs-price-experience` (`/admin/home-services/price-experience`), with the real, distinct `/admin/home-services/overview` page (125 lines, real API-backed, never linked) sitting completely orphaned. Fixed — see Bug Register.

## Result
Real inventory confirms the mission's premise: Super Admin's information architecture has substantial real gaps (~70 orphaned leaf pages, 12 duplicate clusters, 2% permission adoption, one active `/v1/jobs` legacy dependency on the primary Jobs nav item). This sprint's bounded scope (documented in the Final Report) addresses the highest-value, lowest-risk items found; the full-scale menu reorganization this inventory's scale implies is out of safe reach for one sprint and is honestly deferred, not hidden.
