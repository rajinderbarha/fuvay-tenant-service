# FINAL-L5-00 — Route/Page Inventory (Parts 5–6)

Read-only investigation. Covers Super Admin, Tenant Portal, Customer App (all `frontend/*`, Next.js app-router) and Staff/Technician (`mobile/staff-app`, React Navigation). Compiled 2026-07-10.

Classification labels used (only these): ACTIVE_LINKED, ACTIVE_CONTEXTUAL, ACTIVE_HIDDEN_INTENTIONAL, DISCONNECTED_NO_MENU, BROKEN_ROUTE, DUPLICATE_ROUTE, LEGACY_ROUTE, REDIRECT_ROUTE, INCOMPLETE_PAGE, PLACEHOLDER_PAGE, REVIEW_REQUIRED.

Notes on method: routes were enumerated with `Glob app/**/page.tsx` (web) and screen-file glob + navigator grep (mobile). Nav linkage was checked against each app's `lib/nav-config.ts` / `lib/page-registry.ts` (web) or `AppNavigator.tsx`/`TabNavigator.tsx` (mobile). "Menu Item = NONE" means no sidebar/tab entry references the route directly; many of those are legitimate detail pages reached only by clicking through a list (`[id]` routes) and are classified ACTIVE_CONTEXTUAL, not DISCONNECTED_NO_MENU, unless they are top-level list/feature pages with no way in.

---

## 1. Super Admin (`frontend/super-admin`)

144 `page.tsx` routes. Layouts: `app/layout.tsx` (root) and `app/admin/layout.tsx` (AdminLayout + sidebar driven by `lib/nav-config.ts`, `ADMIN_NAV_GROUPS`). Breadcrumb/title metadata in `lib/page-registry.ts` (~55 entries, sparser than full route list).

### 1.1 Entry / auth routes
| Route | Page File | Layout | Menu Item | API Dependency | Classification |
|---|---|---|---|---|---|
| `/` | `app/page.tsx` | root | NONE | redirect | REDIRECT_ROUTE |
| `/login` | `app/login/page.tsx` | root | NONE | authApi | ACTIVE_LINKED (entry point) |
| `/change-password-required` | `app/change-password-required/page.tsx` | root | NONE | authApi | ACTIVE_CONTEXTUAL |

### 1.2 Core admin — linked in sidebar (representative; full API notes in agent transcript)
`/admin/dashboard`, `/admin/tenants` (+`[id]`), `/admin/users` (+`[id]`), `/admin/customers` (+`[id]`), `/admin/staff` (+`[id]`), `/admin/bookings` (+`[id]`), `/admin/operations` (+`[jobId]`), `/admin/real-estate/lead-drafts`, `/admin/coaching/appointment-drafts`, `/admin/bookability/providers`, `/admin/onboarding/providers`, `/admin/home-services/booking-drafts|service-catalog|pricing-rules|price-experience|provider-matching|matching-diagnostics|service-areas|completed-job-deduction|settings`, `/admin/categories` (+`[id]`), `/admin/service-options` (+`[id]`), `/admin/issue-types`, `/admin/checklists`, `/admin/workflow-templates`, `/admin/service-setup` (+`brands`), `/admin/customer-flow`, `/admin/packages`, `/admin/pricing`, `/admin/finance`, `/admin/service-invoices`, `/admin/provider-wallets`, `/admin/commission-records`, `/admin/payments`, `/admin/financial-events`, `/admin/intelligence`, `/admin/analytics`, `/admin/reports`, `/admin/ai/sessions`, `/admin/ai-chat`, `/admin/marketing`, `/admin/notifications`, `/admin/chat`, `/admin/reviews`, `/admin/complaints`, `/admin/automation/recommendation-rules`, `/admin/engines`, `/admin/security`, `/admin/compliance`, `/admin/audit-logs`, `/admin/media`, `/admin/settings`, `/admin/account` (mapped to "profile").
All → Classification **ACTIVE_LINKED**. Detail sub-routes (`[id]`, `[jobId]`, `[key]`) with no direct nav entry → **ACTIVE_CONTEXTUAL**. `/admin/audit-logs` notably uses raw `fetch()` to `/v1/admin/audit-logs` instead of a typed API client — flagged REVIEW_REQUIRED for consistency, not brokenness.

### 1.3 Orphan top-level pages (exist, no sidebar entry) — DISCONNECTED_NO_MENU
`/admin/users/roles`, `/admin/users/permissions`, `/admin/account/sessions`, `/admin/account/login-history`, `/admin/home-services/overview` (uses different `lib/api-foundation` module), `/admin/home-services/service-jobs` (+`[jobId]`), `/admin/catalog-module/[key]`, `/admin/pricing-tiers`, `/admin/pricing-rules`, `/admin/checklist-templates`, `/admin/workflows/templates` (+`[id]`), `/admin/finance/wallets|topups|payouts|deposits|claims|customer-credits|dispute-settlements|tenant-penalties|usage-credits` (all sub-pages of `/admin/finance` with no individual nav link), `/admin/engines/resolver`, `/admin/automation/recommendation-results`, `/admin/notification-templates`, `/admin/notification-outbox`, `/admin/ai/metrics`, `/admin/ai/failed-actions`, `/admin/ai-chat/sessions|logs|prompt-templates|test-console`, `/admin/marketing/templates|events|generate|campaigns|publish-queue|assets|segments|automation`, `/admin/review-flags`, `/admin/review-policies`, `/admin/review-replies`, `/admin/rating-summaries`, `/admin/complaint-policies`, `/admin/rework-requests`, `/admin/refund-requests`, `/admin/verticals` (Sprint P0 Multi-Vertical Catalog page, never wired to sidebar), `/admin/types-brands`, `/admin/master-services` (redirect target of `/admin/catalog` but itself unlinked), `/admin/brands`, `/admin/brand-requests`, `/admin/service-groups`, `/admin/location-mapping`, `/admin/service-setup/brand-requests|brand-templates|service-options|option-groups|issue-types|templates|bulk-wizard|bulk-runs`.
≈70 of 144 routes carry `Menu Item = NONE`; the above list is the top-level/list-page subset (not `[id]` detail pages) — these are the real DISCONNECTED_NO_MENU candidates worth product review.

### 1.4 Legacy / redirect / duplicate routes
| Route | Classification | Notes |
|---|---|---|
| `/admin/catalog` | LEGACY_ROUTE / REDIRECT_ROUTE | Client-side `router.replace("/admin/master-services")`; code comment: "Catalog tabs have been promoted to standalone pages." Confirms prior P0 Duplicate Category cleanup pattern extended here; no old `CategoriesTab` file remains in repo. |
| `/admin/checklists` vs `/admin/checklist-templates` | DUPLICATE_ROUTE | Same feature area (checklist templates); only `/admin/checklists` is in nav. |
| `/admin/workflow-templates` vs `/admin/workflows/templates` (+`[id]`) | DUPLICATE_ROUTE | Only `/admin/workflow-templates` is in nav. |
| `/admin/pricing` vs `/admin/pricing-rules` vs `/admin/home-services/pricing-rules` | DUPLICATE_ROUTE (triplicate) | Three pricing-rule surfaces; only `/admin/pricing` and the home-services variant are in nav. |
| `/admin/notifications/templates` vs `/admin/notification-templates` | DUPLICATE_ROUTE | Neither in nav; different API clients (`notifTemplateAdminApi` vs `sprint27AdminApi`). |
| `/admin/provider-wallets` vs `/admin/finance/wallets` | DUPLICATE_ROUTE | `/admin/provider-wallets` in nav (top-level); `/admin/finance/wallets` orphaned under Finance Hub. |
| `/admin/brand-requests` vs `/admin/service-setup/brand-requests` | DUPLICATE_ROUTE | Both orphaned; likely two implementations of the same brand-request review UI. |
| `/admin/account` vs `/admin/profile` | DUPLICATE_ROUTE | Both resolve to "profile" concept; two separate implementations. |
| `/admin/service-options` vs `/admin/service-setup/service-options` | DUPLICATE_ROUTE | Same concept duplicated under service-setup namespace. |
| `/admin/issue-types` vs `/admin/service-setup/issue-types` | DUPLICATE_ROUTE | Same concept duplicated. |

### 1.5 Placeholder / incomplete signal
A broad grep (`mockData|fakeData|TODO|placeholder|Coming Soon`) hit 88 files; the large majority are `placeholder=` props on form inputs (false positives), not incomplete pages. Flagged REVIEW_REQUIRED (not auto-classified INCOMPLETE_PAGE) pending manual spot-check: `/admin/home-services/overview`, `/admin/verticals`, `/admin/types-brands`, `/admin/master-services`, `/admin/engines/resolver` — these are newer Sprint pages that are functionally complete per memory but structurally unlinked from nav, which is the primary concern rather than incompleteness.

---

## 2. Tenant Portal (`frontend/tenant-portal`)

~95 `page.tsx` routes across the `(tenant)` route group (provider/tenant admin UI, `TenantLayout` + sidebar from `lib/nav-config.ts` → `TENANT_NAV_GROUPS`) and a separate `app/staff/*` segment (staff-worker mobile-web portal, outside tenant sidebar scope entirely — no shared layout, own auth).

### 2.1 Auth / entry (root layout, no sidebar)
`/login`, `/register`, `/forgot-password`, `/change-password`, `/change-password-required`, `/onboarding` — all ACTIVE_LINKED (entry-flow pages, correctly outside the dashboard nav).

### 2.2 Linked in `TENANT_NAV_GROUPS` — ACTIVE_LINKED
`/dashboard`, `/activity`, `/analytics`, `/appointments`, `/bookings`, `/chat`, `/customers`, `/dispatch`, `/documents`, `/finance/package`, `/finance/security-deposit`, `/finance/usage-credit-ledger`, `/jobs`, `/marketing`, `/notifications`, `/profile`, `/provider/availability`, `/provider/service-areas`, `/provider/service-coverage`, `/provider/staff`, `/provider/status`, `/reports`, `/reviews`, `/settings`, `/tenant/setup/services`.

### 2.3 Resolved via path-map only (breadcrumb resolution, not a literal sidebar href) — ACTIVE_HIDDEN_INTENTIONAL
`/account`, `/catalog`, `/inventory`, `/media`, `/onboarding-status`, `/packages`, `/provider/chat`, `/provider/complaints`, `/provider/compliance`, `/provider/marketing`, `/provider/notifications`, `/provider/refund-requests`, `/provider/rework-requests`, `/provider/services` (also a redirect — see 2.5), `/provider/subscription-status`, `/provider/team-members`, `/provider/wallet`, `/service-areas`, `/service-jobs`, `/services` (also a redirect), `/staff` (tenant-side roster page).

### 2.4 DISCONNECTED_NO_MENU (no path-map entry, no sidebar href)
`/ai-chat`, `/insights`, `/provider/customer-price-preview`, `/provider/pricing`, `/provider/service-options`, `/provider/service-setup`, `/tenant/setup/availability`, `/users`, `/wallet`.

### 2.5 Redirect stubs (not real content pages) — REDIRECT_ROUTE
`/services` → `/catalog`; `/provider/services` → `/catalog`; `/setup/checklist` → `/onboarding-status`; `/setup/service-coverage` → `/provider/service-coverage`.

### 2.6 Duplicate/overlapping-feature clusters — DUPLICATE_ROUTE
1. Staff roster: `/staff`, `/provider/staff`, `/provider/team-members` (3 pages).
2. Service setup/offerings: `/provider/offerings`, `/provider/service-setup`, `/provider/service-options`, `/tenant/setup/services`, `/catalog` (5 overlapping pages — largest cluster found in the whole audit).
3. Onboarding/status: `/onboarding`, `/onboarding-status`, `/provider/status`, `/setup/checklist` (redirect).
4. Service areas: `/service-areas` vs `/provider/service-areas`.
5. Wallet: `/wallet` vs `/provider/wallet`.
6. Notifications: `/notifications` vs `/provider/notifications`.
7. Marketing: `/marketing` vs `/provider/marketing`.
8. Chat: `/chat` vs `/provider/chat`.
9. Jobs: `/jobs` vs `/service-jobs` (map to the same nav id).
10. Availability: `/provider/availability` (linked) vs `/tenant/setup/availability` (orphaned).
11. Staff-worker portal: `/staff/jobs` vs `/staff/home-services/jobs`.

### 2.7 Staff-worker mobile-web portal (`app/staff/*`, no dedicated layout)
`/staff/login`, `/staff/dashboard`, `/staff/jobs` (+`[job_id]`), `/staff/home-services/jobs` (+`[job_id]`), `/staff/availability`, `/staff/documents`, `/staff/notifications`, `/staff/profile`, `/staff/security/sessions`, `/staff/service-areas`, `/staff/skills` — all ACTIVE_LINKED within their own auth flow, but architecturally separate from both the tenant sidebar and the native `mobile/staff-app`; flagged REVIEW_REQUIRED (three separate "staff" surfaces exist in the product: native app, this web portal, and tenant-portal's `/staff` roster view — worth a product decision).

### 2.8 Placeholder/incomplete
Grep for `mockData|fakeData|Coming Soon|// TODO|/* TODO` returned zero matches across all tenant-portal `page.tsx` files. No PLACEHOLDER_PAGE/INCOMPLETE_PAGE found.

---

## 3. Customer App (`frontend/customer-app`)

Only 8 `page.tsx` files. Single root `app/layout.tsx` (bare shell, no shared nav — each page self-imports `BottomNav`). No nav-config/page-registry file exists; nav is a hardcoded 4-item `components/BottomNav.tsx` (Home, Services, Book-Now FAB, Bookings, Profile).

| Route | Page File | Menu Item | API Dependency | Classification |
|---|---|---|---|---|
| `/` | `app/page.tsx` | NONE | pure `redirect("/customer/home-services")` | REDIRECT_ROUTE |
| `/login` | `app/login/page.tsx` | NONE | `customerLogin()` | ACTIVE_CONTEXTUAL (reached via `?next=` from booking flow) |
| `/customer/home-services` | `app/customer/home-services/page.tsx` | "Home" and "Services" tabs (both point here) | `getCustomerHomeServicesCatalog`, `getCustomerName`, `isLoggedIn` | ACTIVE_LINKED |
| `/customer/home-services/book` | `app/customer/home-services/book/page.tsx` | "+" FAB | 12 booking-flow API calls (catalog, draft, pricing, provider match, create booking) | INCOMPLETE_PAGE — explicit dev comment: photo upload disabled/not wired to backend, references `CUSTOMER_FRONTEND_01_REMAINING_BLOCKERS.md` |
| `/customer/bookings` | `app/customer/bookings/page.tsx` | "Bookings" | `getCustomerBookings()` | ACTIVE_LINKED |
| `/customer/bookings/[bookingId]` | `app/customer/bookings/[bookingId]/page.tsx` | NONE | `getCustomerBookingDetail`, `getCustomerBookingTracking` | ACTIVE_CONTEXTUAL |
| `/customer/bookings/[bookingId]/rate` | `app/customer/bookings/[bookingId]/rate/page.tsx` | NONE | `getCustomerBookingDetail`, `getCustomerBookingReview`, `submitCustomerBookingReview` | ACTIVE_CONTEXTUAL |
| `/customer/profile` | `app/customer/profile/page.tsx` | "Profile" | `getCustomerName`, `getCustomerId`, `customerLogout` | ACTIVE_LINKED (thin — no address book/payment methods/settings; not flagged INCOMPLETE_PAGE absent an explicit TODO, but worth product review) |

No DISCONNECTED_NO_MENU, no duplicate routes, no MISSING_PAGE. Cosmetic note: BottomNav's "Home" and "Services" tabs are literally the same href — not a duplicate page, just a redundant nav entry (see menu inventory report).

---

## 4. Staff/Technician (`mobile/staff-app`, React Navigation, no Expo Router / no `app/` dir)

8 screens total, all registered, no orphans, no broken references.

| Screen | Screen File | Registered In | Menu/Tab | API Dependency | Classification |
|---|---|---|---|---|---|
| Login | `src/screens/LoginScreen.tsx` | `AppNavigator.tsx` (unauthenticated stack) | none (pre-auth gate) | none directly (via AuthContext) | ACTIVE_LINKED |
| Home | `src/screens/HomeScreen.tsx` | `TabNavigator.tsx` | Tab: Home 🏠 | `Api.myJobs` | ACTIVE_LINKED |
| Jobs List | `src/screens/JobsListScreen.tsx` | `TabNavigator.tsx` | Tab: Jobs 📋 | `Api.myJobs` | ACTIVE_LINKED |
| Job Detail | `src/screens/JobDetailScreen.tsx` | `AppNavigator.tsx` (stack push) | reached from Jobs/Home | `Api.get/updateStatus/close/recordPayment/history`, raw `fetch` | ACTIVE_CONTEXTUAL |
| Chat List | `src/screens/ChatListScreen.tsx` | `TabNavigator.tsx` | Tab: Chat 💬 | `Api.listRooms` | ACTIVE_LINKED |
| Chat Room | `src/screens/ChatRoomScreen.tsx` | `AppNavigator.tsx` (stack push) | reached from Chat List | `Api.getMessages/sendMessage/markRead`, raw `fetch` | ACTIVE_CONTEXTUAL |
| Earnings | `src/screens/EarningsScreen.tsx` | `TabNavigator.tsx` | Tab: Earnings 💰 | `Api.summary/commissions`, raw `fetch` | ACTIVE_LINKED |
| Profile | `src/screens/ProfileScreen.tsx` | `TabNavigator.tsx` | Tab: Profile 👤 | `staffApi.get/updateSchedule/performance`, raw `fetch` | ACTIVE_LINKED |

No mock/TODO/placeholder markers found (all "placeholder" grep hits are legitimate `TextInput placeholder=` UI props).

---

## 5. Headline totals

| Application | Total routes/screens | ACTIVE_LINKED (+contextual/hidden) | DISCONNECTED_NO_MENU | REDIRECT_ROUTE | DUPLICATE_ROUTE clusters | INCOMPLETE/PLACEHOLDER |
|---|---|---|---|---|---|---|
| Super Admin | 144 | ~74 direct + detail pages | ~35 top-level orphans (+ ~35 orphaned detail pages) | 1 (`/admin/catalog`) | 10 clusters (~22 routes) | 0 confirmed (5 flagged REVIEW_REQUIRED) |
| Tenant Portal | ~95 (+11 staff-web) | ~65 | 9 | 4 | 11 clusters (~30 routes) | 0 |
| Customer App | 8 | 7 | 0 | 1 (`/`) | 0 | 1 (`/customer/home-services/book` — photo upload) |
| Staff App (mobile) | 8 | 8 | 0 | 0 | 0 | 0 |

Biggest structural risk found: **Tenant Portal "service setup/offerings" cluster** (5 overlapping pages) and **Super Admin finance/marketing/analytics sub-page sprawl** (dozens of legitimate feature pages built with no sidebar entry — likely intentional information-architecture debt from rapid sprint delivery rather than bugs, but worth a nav-config pass).
