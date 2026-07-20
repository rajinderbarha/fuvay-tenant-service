# Simplified Information Architecture

Navigation reorganized around user goals, not engine names. Derived from `role-navigation-matrix.csv` and `page-disposition-matrix.csv`. No visual redesign — same components, same styling, only grouping/labels/routing change.

## Super Admin (platform-wide)
Home · My Work · Businesses · Services · Operations · Finance · Governance · Reports · Settings

- **Businesses** = tenants + onboarding/verification + packages + trust & quality (merges the two current duplicate onboarding pages).
- **Services** = verticals + categories + pricing (tabs: Tiers, Location Mapping, Overrides, Commission) + Home Services vertical workspace.
- **Operations** = canonical ServiceJob view (legacy /admin/bookings retired from nav) + customers + staff + reviews (pending review-stack confirmation) + complaints.
- **Finance** = Finance Hub with tabs (Usage Credits, Deposits, Topups, Claims, Payouts, Service Invoices, Provider Wallets, Commission Records, Financial Events) — collapses 10 currently-separate/orphaned pages into one workspace.
- **Governance** = Security, Roles, Permissions, Audit Logs, Engines, Workflow Templates, Compliance (moved out of Finance), Users.
- **Reports** = Analytics + Reports + Intelligence + Marketing merged.
- **Settings** = Media, general platform settings, notification templates.
- Real-estate/coaching modules removed from default nav until those verticals go live (still reachable via deep link / advanced).

## Provider Owner (tenant_owner)
Home · My Work · Jobs · Services · Team · Customers · Business · Credits · Settings

- **Jobs** = single merged workspace over jobs/bookings/appointments/service-jobs (contingent on backend booking-model consolidation).
- **Services** = the guided Provider Service & Pricing Setup wizard (collapses 5 current separate pages) plus an "Advanced" tab for one-off edits after initial publish.
- **Team** = staff list + invite + skill/availability.
- **Customers** = merges Reviews + Complaints + Chat + Marketing (each currently duplicated once in nav) + customer directory.
- **Business** = Profile + Documents + Compliance + onboarding status.
- **Credits** = Package + Usage Credit Ledger + Security Deposit as tabs.
- **Settings** = account + engines.

## Provider Manager (staff role, permission-limited subset of tenant_owner shell)
Home · My Work · Jobs · Team · Quotes · Customers · Business
(Same shell as Owner, permission-gated — no separate app.)

## Technician
Today · My Jobs · Inspection · Quote · Parts · Completion · Profile

- Today/My Jobs/Inspection/Quote/Completion map directly to the job-lifecycle screens that already exist (web and mobile).
- Profile consolidates the 4 currently-separate web setup pages (skills, service-areas, availability) plus documents/sessions/activity under an Advanced sub-tab; mobile app should reach parity here (currently narrower — see workflow-gaps-and-blockers.md).
- Parts remains a placeholder until the backend Parts entity is built (see canonical-pipeline-report.md #3) — do not build UI for a workflow that doesn't exist server-side yet.

## Customer
Home · Book · My Bookings · Quotes · Finance · Profile

- Maps directly onto the current (non-legacy) `MainNavigator` screen set. No change needed to the current-generation screens; the nested legacy 19-screen stack is out of scope for nav changes (it's not surfaced in primary nav today either) but flagged for eventual retirement.

## Cross-cutting rule
Every nav item's advanced/technical details (raw IDs, permission internals, audit dumps, deprecated endpoint status) move to Level 3 (see `standard-workspace-patterns.md` and progressive-disclosure rules) — never shown by default.
