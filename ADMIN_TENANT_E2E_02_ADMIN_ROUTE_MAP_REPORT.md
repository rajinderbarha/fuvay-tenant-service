# Admin Route Map Report (ADMIN-TENANT-E2E-02, Part 1)

Full `frontend/super-admin/app/admin/` top-level directory (verified via `ls`):
account, ai, ai-chat, analytics, audit-logs, automation, bookability, bookings, brand-requests,
brands, catalog, catalog-module, categories, chat, checklist-templates, checklists, coaching,
commission-records, complaint-policies, complaints, compliance, customer-flow, customers,
dashboard, engines, finance, financial-events, home-services, intelligence, issue-types,
location-mapping, marketing, master-services, media, notification-events, notification-outbox,
notification-templates, notifications, onboarding, operations, packages, payments, pricing,
pricing-rules, pricing-tiers, profile, provider-wallets, rating-summaries, real-estate,
refund-requests, reports, review-flags, review-policies, review-replies, reviews,
rework-requests, security, service-groups, service-invoices, service-options, service-setup,
settings, staff, tenants, types-brands, users, verticals, workflow-templates, workflows.

The spec's illustrative examples (`/admin/home-services/overview`, `/admin/home-services/service-catalog`,
`/admin/home-services/pricing-rules`) turned out to be **real** — `home-services/` does exist with
sub-routes: `booking-drafts`, `service-catalog`, `service-jobs`, `pricing-rules`, `price-experience`,
`provider-matching`, `matching-diagnostics`, `service-areas`, `completed-job-deduction`, `settings`.
(Confirmed via `npm run build`'s route table and by grepping page files for `activeNav="hs-*"`.)

## Rendered sidebar (what's actually shown) vs config file
`components/layout/AdminLayout.tsx` owns the **rendered** sidebar via its own `NAV_GROUPS` array
(9 groups: Overview, Providers, Operations, Catalog, Pricing & Rules, Home Services, Finance,
Marketing & Growth, Platform). Separately, `lib/nav-config.ts` has its OWN independent
`ADMIN_NAV_GROUPS` array (11 groups) that is **not** used to render the sidebar at all — it was
only used by `app/admin/layout.tsx` to compute the active-nav id from the URL. The two lists have
drifted: `nav-config.ts` references items (`real-estate`, `coaching`, `bookability`, `reports`,
`ai`, `ai-chat`, `service-invoices`, `provider-wallets`, `commission-records`, `payments`,
`financial-events`, `packages` as own group, etc.) that are NOT in `AdminLayout.tsx`'s rendered
`NAV_GROUPS` at all — meaning several real, working pages under `app/admin/` (e.g.
`/admin/real-estate`, `/admin/coaching`, `/admin/bookability`, `/admin/reports`, `/admin/ai`,
`/admin/service-invoices`, `/admin/provider-wallets`, `/admin/commission-records`,
`/admin/payments`, `/admin/financial-events`) have **no sidebar entry at all** — they're
reachable only by direct URL or from links inside other pages. This is a real navigation gap
(documented further in Part 2) — out of strict scope to add 10+ new sidebar items in this sprint,
but flagged as the top follow-up item.

## Representative route table (spot sample; full set is the 70 directories above)
| Route | Page file | Sidebar group (rendered) | API calls (grep) | Status |
|---|---|---|---|---|
| /admin/dashboard | app/admin/dashboard/page.tsx | Overview | dashboard/summary-ish endpoints | OK, 200 |
| /admin/tenants | app/admin/tenants/page.tsx | Providers | /v1/admin/tenants* | OK, 200 |
| /admin/tenants/onboarding | app/admin/tenants/onboarding/page.tsx | Providers ("New Requests") | /v1/admin/onboarding* | OK, 200, active-state fixed (Part 3) |
| /admin/onboarding/providers | app/admin/onboarding/providers/page.tsx | Providers ("Verify & Approve") | /v1/admin/onboarding/providers | OK |
| /admin/home-services/service-catalog | .../home-services/service-catalog/page.tsx | Home Services | /v1/admin/... catalog | OK, 200 |
| /admin/home-services/pricing-rules | .../home-services/pricing-rules/page.tsx | Home Services | /v1/pricing/... | OK, 200 |
| /admin/categories | app/admin/categories/page.tsx | Catalog | /v1/admin/categories | OK |
| /admin/pricing-tiers | app/admin/pricing-tiers/page.tsx | Pricing & Rules | /v1/pricing/tiers | OK |
| /admin/finance | app/admin/finance/page.tsx | Finance | /v1/admin/finance/* | OK |
| /admin/security | app/admin/security/page.tsx | Platform | /v1/admin/trust-quality / security | OK |
| /admin/audit-logs | app/admin/audit-logs/page.tsx | Platform | direct `fetch()` to `/v1/admin/audit-logs` (bypasses lib/api.ts — see Part 12) | OK |
| /admin/users/roles | app/admin/users/roles/page.tsx | Platform ("Roles") | /v1/admin/users/roles | OK, active-state fixed (Part 3) |
| /admin/users/permissions | app/admin/users/permissions/page.tsx | Platform ("Permissions") | /v1/admin/users/permissions | OK, active-state fixed (Part 3) |
| /admin/real-estate/... | exists on disk | **not in rendered sidebar** | n/a | reachable, orphaned nav |
| /admin/coaching/... | exists on disk | **not in rendered sidebar** | n/a | reachable, orphaned nav |
| /admin/bookability/providers | exists on disk | **not in rendered sidebar** | n/a | reachable, orphaned nav |

`npm run build` (Next.js production build, see Part 18 TEST_RESULTS) compiled every one of the 70
directories with no route-level build errors — confirms the full route set is real, buildable,
routable.
