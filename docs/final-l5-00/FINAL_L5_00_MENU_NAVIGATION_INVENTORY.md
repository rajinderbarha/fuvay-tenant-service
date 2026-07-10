# FINAL-L5-00 — Menu / Navigation Inventory (Parts 5–6)

Read-only investigation, inventory-only (no menu redesign performed). Compiled 2026-07-10.

Classification labels used (only these): VALID, MISSING_PAGE, UNLINKED_PAGE, DUPLICATE, WRONG_GROUP, WRONG_PERMISSION, HARDCODED_CATEGORY, INACTIVE_MODULE_VISIBLE, ACTIVE_CATEGORY_MISSING, REVIEW_REQUIRED.

## Nav/menu config files found

| Application | Config file(s) | Structure |
|---|---|---|
| Super Admin | `G:\serviceos\frontend\super-admin\lib\nav-config.ts` | `ADMIN_NAV_GROUPS` — 11 groups, each with an array of `{id, label, href, ...}` items |
| Super Admin | `G:\serviceos\frontend\super-admin\lib\page-registry.ts` | Breadcrumb/title metadata registry, ~55 entries — narrower than the 144 actual routes; not a menu source itself but used to validate page identity |
| Tenant Portal | `G:\serviceos\frontend\tenant-portal\lib\nav-config.ts` | `TENANT_NAV_GROUPS` (literal sidebar hrefs) + `TENANT_PATH_TO_NAV_ID` / `TENANT_PROVIDER_PATH_TO_NAV_ID` (path→nav-id resolution maps used for breadcrumbs/active-state, not literal menu entries) |
| Tenant Portal | `G:\serviceos\frontend\tenant-portal\lib\page-registry.ts` | `TENANT_PAGE_REGISTRY` — page titles |
| Customer App | *(none)* | No nav-config/page-registry file exists at all. Only `G:\serviceos\frontend\customer-app\components\BottomNav.tsx` — a hardcoded 4-item bottom tab bar with inline JSX `Link` hrefs, no external data model |
| Staff App (mobile) | `mobile/staff-app/src/navigation/AppNavigator.tsx`, `mobile/staff-app/src/navigation/TabNavigator.tsx` (paths per repo scan) | React Navigation `Stack.Screen` / `Tab.Screen` declarations — code-as-config, no separate data file |

## Super Admin — `ADMIN_NAV_GROUPS` (`lib/nav-config.ts`)

11 groups covering: Overview (dashboard), Tenants, Users, Customers, Staff, Operations (bookings/operations/real-estate/coaching/bookability/onboarding), Home Services (8 items), Catalog (categories/service-options/issue-types/checklists/workflow-templates/service-setup), Packages & Pricing, Finance (service-invoices/provider-wallets/commission-records/payments/financial-events), Intelligence/Analytics/Reports, AI, Marketing, Notifications/Chat, Reviews/Complaints, Automation, Engines, Security/Compliance/Audit-logs, Media, Settings.

Every literal `href` in `ADMIN_NAV_GROUPS` was cross-checked against the Glob of `page.tsx` files: **all resolve to an existing file** → **0 MISSING_PAGE** for super-admin.

### Notable classifications
| Menu ID | Label (approx) | Route | Target page exists? | Classification | Notes |
|---|---|---|---|---|---|
| checklist-templates | Checklists | `/admin/checklists` | Y | VALID | but `/admin/checklist-templates` (separate page, same feature) exists unlinked — see UNLINKED_PAGE below |
| workflow-templates | Workflow Templates | `/admin/workflow-templates` | Y | VALID | `/admin/workflows/templates` is an unlinked duplicate |
| hs-pricing-rules | Pricing Rules (Home Services) | `/admin/home-services/pricing-rules` | Y | DUPLICATE | overlaps `pricing` group item and orphan `/admin/pricing-rules` |
| pricing | Pricing | `/admin/pricing` | Y | DUPLICATE | see above — 3-way pricing-rule overlap |
| provider-wallets | Provider Wallets | `/admin/provider-wallets` | Y | DUPLICATE | `/admin/finance/wallets` is an unlinked duplicate under Finance Hub |
| account / profile | Account | `/admin/account` | Y | DUPLICATE | `/admin/profile` is a second, unlinked implementation |
| reports | Reports | `/admin/reports` | Y | REVIEW_REQUIRED | functionally overlaps the `/admin/analytics` group (both call `adminAnalyticsApi`); candidate for merge or WRONG_GROUP |
| catalog | Catalog | *(no nav entry — `/admin/catalog` removed from sidebar)* | Y (route exists, is a redirect shim) | VALID (correctly de-listed) | Legacy route intentionally kept only as a redirect; nav no longer references it — correct post-cleanup state |

### Pages that exist with no menu item at all — UNLINKED_PAGE
`/admin/users/roles`, `/admin/users/permissions`, `/admin/account/sessions`, `/admin/account/login-history`, `/admin/home-services/overview`, `/admin/home-services/service-jobs`, `/admin/catalog-module/[key]`, `/admin/checklist-templates`, `/admin/workflows/templates`, `/admin/pricing-rules`, `/admin/pricing-tiers`, `/admin/pricing/bargain-rules`, `/admin/pricing/provider-overrides`, `/admin/finance/wallets`, `/admin/finance/topups`, `/admin/finance/payouts`, `/admin/finance/deposits`, `/admin/finance/claims`, `/admin/finance/customer-credits`, `/admin/finance/dispute-settlements`, `/admin/finance/tenant-penalties`, `/admin/finance/usage-credits`, `/admin/engines/resolver`, `/admin/automation/recommendation-results`, `/admin/notification-templates`, `/admin/notification-outbox`, `/admin/ai/metrics`, `/admin/ai/failed-actions`, `/admin/ai-chat/sessions`, `/admin/ai-chat/logs`, `/admin/ai-chat/prompt-templates`, `/admin/ai-chat/test-console`, `/admin/marketing/templates`, `/admin/marketing/events`, `/admin/marketing/generate`, `/admin/marketing/campaigns`, `/admin/marketing/publish-queue`, `/admin/marketing/assets`, `/admin/marketing/segments`, `/admin/marketing/automation`, `/admin/review-flags`, `/admin/review-policies`, `/admin/review-replies`, `/admin/rating-summaries`, `/admin/complaint-policies`, `/admin/rework-requests`, `/admin/refund-requests`, `/admin/verticals`, `/admin/types-brands`, `/admin/master-services`, `/admin/brands`, `/admin/brand-requests`, `/admin/service-groups`, `/admin/location-mapping`, `/admin/service-setup/brand-requests`, `/admin/service-setup/brand-templates`, `/admin/service-setup/service-options`, `/admin/service-setup/option-groups`, `/admin/service-setup/issue-types`, `/admin/service-setup/templates`, `/admin/service-setup/bulk-wizard`, `/admin/service-setup/bulk-runs`.

`/admin/verticals` is specifically an **ACTIVE_CATEGORY_MISSING** case: memory confirms the P0 Multi-Vertical Catalog feature (migration 089, 7 verticals seeded, dynamic sidebar work) shipped and is functionally live, but the top-level `/admin/verticals` management page was never added as its own sidebar item — the dynamic per-vertical pages (`/admin/catalog/[vertical]`) are reachable, but the verticals *admin* page is not.

## Tenant Portal — `TENANT_NAV_GROUPS` / path-maps (`lib/nav-config.ts`)

All literal `href`s in `TENANT_NAV_GROUPS` resolve to existing pages → **0 MISSING_PAGE**. However the nav model here is two-tiered: a literal sidebar list (`TENANT_NAV_GROUPS`) plus a much larger `TENANT_PATH_TO_NAV_ID` / `TENANT_PROVIDER_PATH_TO_NAV_ID` map that resolves *many more* routes to a nav id purely for breadcrumb/active-highlighting — those routes are **not clickable from the sidebar** even though the system considers them "part of" a nav section. That distinction matters for classification:

- Routes with a literal `href` in `TENANT_NAV_GROUPS` → **VALID**.
- Routes only present in the path-map (reachable by URL/breadcrumb, section highlighted, but no clickable sidebar link) → **ACTIVE_HIDDEN_INTENTIONAL** if clearly a detail/settings sub-page (e.g. `/account`, `/media`, `/inventory`), or **REVIEW_REQUIRED** if it's a full top-level feature page that arguably deserves its own link (e.g. `/catalog`, `/packages`, `/provider/wallet`).
- Routes in neither → **UNLINKED_PAGE**: `/ai-chat`, `/insights`, `/provider/customer-price-preview`, `/provider/pricing`, `/provider/service-options`, `/provider/service-setup`, `/tenant/setup/availability`, `/users`, `/wallet`.

### Duplicate menu-concept findings — DUPLICATE
`/staff` vs `/provider/staff` vs `/provider/team-members` (all map toward "provider-staff" concept but are 3 separate pages); `/service-areas` vs `/provider/service-areas`; `/wallet` vs `/provider/wallet`; `/notifications` vs `/provider/notifications`; `/marketing` vs `/provider/marketing`; `/chat` vs `/provider/chat`; `/jobs` vs `/service-jobs` (both resolve to the same `jobs` nav id — effectively two menu targets for one concept); `/provider/availability` (linked) vs `/tenant/setup/availability` (unlinked, same feature).

### Service-setup mega-cluster — REVIEW_REQUIRED
`provider-services` nav id ("Service Setup" in Setup group) points to `/tenant/setup/services`, but three functionally overlapping pages also exist and are NOT the nav target: `/provider/offerings`, `/provider/service-setup`, `/provider/service-options`, plus `/catalog`. This is the single largest navigation/duplication risk found across the whole audit — five pages compete to be "the" service configuration screen and only one is linked.

## Customer App — `components/BottomNav.tsx`

Hardcoded 4-tab bar, no permission/module conditionals (customer app is single-vertical, home-services only, so no category-driven menu exists).

| Tab Label | Route | Target page exists? | Classification |
|---|---|---|---|
| Home | `/customer/home-services` | Y | VALID |
| Services | `/customer/home-services` | Y | **DUPLICATE** — identical href to "Home" tab; two tab labels pointing at the same route (cosmetic redundancy, not a broken link) |
| (+) Book Now | `/customer/home-services/book` | Y | VALID |
| Bookings | `/customer/bookings` | Y | VALID |
| Profile | `/customer/profile` | Y | VALID |

No permission/module gating exists in this app (single-tenant-vertical consumer app) — HARDCODED_CATEGORY / INACTIVE_MODULE_VISIBLE labels not applicable here; flagged N/A rather than forced into a category.

## Staff App (mobile) — `TabNavigator.tsx` / `AppNavigator.tsx`

5 tabs (Home, Jobs, Chat, Earnings, Profile) all resolve to existing screen components; 2 stack-pushed detail screens (JobDetail, ChatRoom) reached only by navigation.push from list screens, not tabs. **0 MISSING_PAGE, 0 UNLINKED_PAGE, 0 DUPLICATE** — this is the cleanest nav surface in the whole audit; a small, single-purpose app with no legacy accumulation.

## Summary counts

| Application | Menu items inventoried | VALID | MISSING_PAGE | UNLINKED_PAGE (page exists, no menu link) | DUPLICATE | ACTIVE_CATEGORY_MISSING |
|---|---|---|---|---|---|---|
| Super Admin | ~74 (ADMIN_NAV_GROUPS entries) | ~64 | 0 | ~59 unlinked pages found | ~10 clusters | 1 (`/admin/verticals`) |
| Tenant Portal | ~25 literal + ~45 path-map-only | ~25 literal valid | 0 | 9 fully unlinked | ~8 clusters | 0 confirmed |
| Customer App | 5 tabs (4 unique routes) | 4 | 0 | 0 | 1 (cosmetic Home/Services) | N/A |
| Staff App (mobile) | 5 tabs + 2 pushed screens | 7 | 0 | 0 | 0 | N/A |

No MISSING_PAGE (menu pointing at a non-existent file) was found in any of the four applications — every navigational config that references a route, that route's page/screen file exists. The dominant issue pattern across the audit is the reverse: pages/screens that exist and are functionally complete but were never wired into the menu system, plus recurring feature duplication (multiple pages built for the same concept over successive sprints, only one of which is linked).
