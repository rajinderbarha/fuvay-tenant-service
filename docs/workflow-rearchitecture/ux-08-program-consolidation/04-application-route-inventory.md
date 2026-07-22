# UX-08 Workstream 3: Application / Route Inventory

## Customer App — FRESH-VERIFIED THIS PASS

Source: `mobile/customer-app/src/navigation/AppNavigator.tsx` (131 lines) and
`TabNavigator.tsx` (77 lines), read in full this pass.

### Bottom tabs (`TabNavigator.tsx`, `TabParamList`)

| Route | Component | Disposition |
|---|---|---|
| Home | `HomeScreen` (default export) | ACTIVE_PRODUCTION — real IA rebuilt UX-07 Pass 3d (search, SmartBot CTA, active-booking/empty states, category tiles, trust row) |
| Bookings | `BookingsListScreen` | ACTIVE_PRODUCTION |
| AIAssistant ("SmartBot" tab label) | `DeepSeekChatScreen` | ACTIVE_PRODUCTION — real, live-verified DeepSeek chat/booking flow (UX-06 Round 3); accepts optional `{ initialCategoryLabel }` for Home category handoff (UX-07 Pass 3d) |
| Notifications | `NotificationsScreen` | ACTIVE_PRODUCTION |
| Profile | `ProfileScreen` | ACTIVE_PRODUCTION |

Note: a standalone "Chat" tab was deliberately removed from the primary
bottom nav in UX-07 Pass 3d (narrowed to exactly 5 tabs per that pass's
brief) — it is real, not deleted, just relocated (see root-stack row below).

### Root stack (`AppNavigator.tsx`, `RootStackParamList`)

| Route | Component | Disposition |
|---|---|---|
| Tabs | `TabNavigator` | ACTIVE_PRODUCTION (root) |
| BookingDetail | `BookingDetailScreen` | ACTIVE_PRODUCTION |
| ServiceDetail | `ServiceDetailScreen` | ACTIVE_PRODUCTION |
| JobTracking | `JobTrackingScreen` | ACTIVE_PRODUCTION |
| QuoteApproval | `QuoteApprovalScreen` | ACTIVE_PRODUCTION (approve/reject; see doc 06/07 for quote-fixture caveats) |
| Review | `ReviewScreen` | ACTIVE_PRODUCTION |
| Invoice | `InvoiceScreen` | ACTIVE_PRODUCTION |
| Settings | `SettingsScreen` | ACTIVE_PRODUCTION |
| Notifications | `NotificationsScreen` | ACTIVE_PRODUCTION (dup entry point, also a tab) |
| Chat | `ChatScreen` | ACTIVE_PRODUCTION — real human/provider support thread, reachable from Profile > Support > "Messages", not a primary tab (UX-07 Pass 3d relocation, not a deletion) |
| AddressBook | `AddressBookScreen` | ACTIVE_PRODUCTION |
| ServiceHistory | `ServiceHistoryScreen` | ACTIVE_PRODUCTION |
| HelpSupport | `HelpSupportScreen` | ACTIVE_PRODUCTION |
| PaymentMethods | `PaymentMethodsScreen` | ACTIVE_PRODUCTION |
| Login (unauthenticated root) | `LoginScreen` | ACTIVE_PRODUCTION |

### Confirmed genuinely deleted (not just unregistered), per UX-06 Round 5

`BookServiceScreen`, `SmartBotScreen`, `AIAssistantScreen`, `AIChatScreen` —
source code fully removed (see `old-scaffold-closure-report.md` in the UX-06
docs), all four called dead APIs (`bookingsApi.create`, `aiApi`) that never
existed server-side, fully superseded by `DeepSeekChatScreen`'s real, live
booking/chat flow. Verified this pass by their absence from the current
`AppNavigator.tsx`/`TabNavigator.tsx` import lists (both read in full above)
— no import, no reference, confirming the removal held across UX-07.

**Total customer-app routes: 19 unique screens (5 tabs + 14 root-stack
entries, with 1 screen — Notifications — reachable both ways; Login is the
unauthenticated-only 15th root-stack entry).** All 19 are
ACTIVE_PRODUCTION. Zero fixture-only, zero dead, zero orphaned routes found
in this pass's full read of both navigation files.

## Super Admin — CONSOLIDATED-FROM-PRIOR-EVIDENCE (lighter-weight this pass)

- Route surface size (fresh-counted this pass via `find
  frontend/super-admin/app -type d`): **195 directories** under the Next.js
  App Router tree (many are dynamic `[id]` segments or route groups, not all
  independently navigable leaf pages).
- Full per-route disposition audit already exists and is NOT re-derived from
  scratch this pass: `docs/design/ux-02-super-admin/existing-super-admin-
  route-audit.csv` (71 lines/rows) is the authoritative prior audit, cited
  here rather than repeated. `dashboard-widget-inventory.csv` and
  `super-admin-showcase-inventory.csv` in the same directory cover
  widget-level and dev-showcase-level inventories respectively.
- Nav structure source: `frontend/super-admin/lib/nav-config.ts` and
  `lib/ux02/nav-ia.ts` (the latter has a dedicated passing test,
  `__tests__/ux02/nav-ia.test.ts`, confirmed green in this pass's Workstream
  14 vitest run — 13/13 passing, see doc 03).
- UX-08 disposition: **CONSOLIDATED, not re-audited.** No evidence found
  this pass that the route surface changed since UX-02's audit (this
  worktree branches from `50fe95b`, which never touched
  `frontend/super-admin/app/**` per the non-change audit, doc 11).

## Tenant Portal — CONSOLIDATED-FROM-PRIOR-EVIDENCE (lighter-weight this pass)

- Route surface size (fresh-counted this pass): **162 directories** under
  `frontend/tenant-portal/app/(tenant)/**`.
- Full per-route disposition audit already exists and is cited, not
  re-derived: `docs/design/ux-03-tenant-portal/existing-tenant-route-audit.csv`
  (85 rows), plus `orphaned-and-broken-route-report.md`,
  `tenant-route-duplication-map.csv`, and `tenant-design-debt-inventory.md`
  in the same directory — these already document known duplicate/orphaned
  routes from UX-03's own audit.
- UX-08 disposition: **CONSOLIDATED, not re-audited**, with one live caveat
  surfaced fresh this pass: the `PartsRequestList`/`SetupWizard` component
  test failures found in Workstream 14 (doc 03) are a dependency-version
  defect, not a route-disposition change — the routes themselves
  (`(tenant)/inventory`, `ux04` parts-request surfaces) are still the same
  ones UX-04's audit already covered.

## Staff/Technician App — CONSOLIDATED-FROM-PRIOR-EVIDENCE (lighter-weight this pass)

- Screen count (fresh-counted this pass): **28 `.tsx` files** under
  `mobile/staff-app/src/screens/`.
- Navigation structure: `AppNavigator.tsx`, `TabNavigator.tsx`, plus three
  UX-05-era role-aware navigators —
  `navigation/ux05/RoleAwareTabNavigator.tsx`,
  `StaffTabNavigator.tsx`, `TechnicianTabNavigator.tsx` (staff vs.
  technician role split, confirmed present, not re-read line-by-line this
  pass).
- Full per-route disposition audit already exists and is cited, not
  re-derived: `docs/design/ux-05-staff-technician-app/existing-screen-
  route-audit.csv` and `screen-route-inventory.md` (both from UX-05's own
  audit rounds).
- UX-08 disposition: **CONSOLIDATED, not re-audited.** This pass's fresh
  typecheck run (doc 03) found 19 pre-existing type errors across 8+ screen
  files, consistent with the already-known `STAFF_TECHNICIAN_APP_DESIGN_
  PARTIAL` status (doc 02) — this is a code-quality finding, not a
  route-disposition change, so it does not require re-auditing which
  screens are reachable/real vs. fixture-only.

## Disposition legend used across this document (per brief's allowed set)

`ACTIVE_PRODUCTION` (real, reachable, backed by a real API contract),
`SAFE_INFORMATIONAL` (reachable but read-only/non-critical),
`MOCK_DESIGN_ONLY` (reachable, fixture-backed, not wired to a real backend
— see doc 07 for the registry of these), `DEAD_CONFIRMED_REMOVED` (source
deleted, not just unregistered — customer-app's four UX-06 Round 5
removals qualify), `CONSOLIDATED_FROM_PRIOR_AUDIT` (this pass reused an
existing, still-valid audit rather than re-deriving it).
