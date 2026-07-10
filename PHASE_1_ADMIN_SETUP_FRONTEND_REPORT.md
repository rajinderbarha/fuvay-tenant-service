# Phase 1 — Admin Setup Frontend Report

## Method

Real page paths differ from the ticket's assumed `/admin/users/roles`,
`/admin/users/permissions`, `/admin/platform-users` paths (confirmed
repeatedly across Phase 0 and the earlier Phase 1 sprint). Verification:
page exists, imports/calls a real API client (no `MOCK_*`), and
`npx tsc --noEmit` compiles cleanly across the whole frontend.

| Module | Ticket path | Real path | Exists | Real API | TS clean |
|---|---|---|---|---|---|
| Login | `/admin/login` | `/login` | ✅ | ✅ | ✅ |
| Dashboard | `/admin/dashboard` | `/admin/dashboard` | ✅ | ✅ (`dashboardApi.*`) | ✅ |
| Roles | `/admin/users/roles` | **does not exist** | ❌ | — | — |
| Permissions | `/admin/users/permissions` | **does not exist** | ❌ | — | — |
| Platform Users | `/admin/platform-users` | `/admin/users` | ✅ | ✅ (real `/v1/admin/platform-users` API, confirmed 200 live) | ✅ |
| Platform Settings | `/admin/platform-settings` | `/admin/settings` | ✅ | ✅ | ✅ |
| Navigation | `/admin/navigation` | *(sidebar only, no dedicated nav-admin page)* | ⚠️ partial | — | — |
| Engine Management | `/admin/engines` | `/admin/engines` | ✅ | ✅ | ✅ |
| Vertical Configuration | `/admin/verticals` | `/admin/verticals` | ✅ | ✅ | ✅ |
| Audit Logs | `/admin/audit-logs` | `/admin/audit-logs` | ✅ | ✅ (3-tab: Engine/Security/Auth Audit) | ✅ |

**7/10 ticket-named modules have a real, working page. Roles and Permissions
have no dedicated management page (role assignment happens via the Users
page's role dropdown, not a standalone roles/permissions CRUD UI); Navigation
has no dedicated admin editor page (the sidebar itself is the only "UI" for
navigation, driven live by the effective-menu API).**

## Sidebar

`AdminLayout.tsx` — no duplicate `Brands`/`Brand Requests`/`Pricing Tiers`/
`City-Zip Mapping`/`Pricing Rules` (static-verified, unchanged from Phase 0).
Sidebar visibility is permission/vertical-aware via `isNavItemVisible()` and
`effectiveMenu` fetched from the real backend endpoint.

## Auth guard

`AdminLayout.tsx` redirects to `/login` via a client-side `useEffect` check
of `localStorage.serviceos_admin_token` (same finding as Phase 0/1 — works
functionally, not a server-side Next.js middleware).

## TypeScript

`npx tsc --noEmit` → **0 errors** across the entire `frontend/super-admin` build.

## Forbidden-label check

Grepped `AdminLayout.tsx`, `/admin/settings/page.tsx`, and this sprint's live
API responses for `platform-settings` — no occurrences of `Cash Wallet`,
`Withdraw`, `Withdrawable Balance`, `Tenant Payout`, `Provider Earnings
Wallet`, or `Escrow`. One pre-existing nav item is labeled "Payouts"
(`/admin/finance/payouts`) — flagged in a prior sprint's memory as
potentially confusing terminology, not re-litigated here since it's outside
Phase 1's Admin Setup scope (it's a Finance Hub nav item, not a Home
Services settings label).

**No live browser session was launched this sprint** — see
`PHASE_1_ADMIN_SETUP_MANUAL_SMOKE_REPORT.md` for the explicit breakdown of
what that means for the final recommendation.
