# FINAL-L5-04 — Admin Menu Organization Baseline Report

Per the mission's own framing: "This sprint establishes dynamic structure, not final visual redesign."

## Real current groups (from live `NAV_GROUPS`, 9 groups, 44 items)
Overview, Providers, Operations, Catalog (+dynamic vertical sections), Pricing & Rules, Home Services, Finance, Marketing & Growth, Platform.

## Comparison against the mission's recommended baseline
| Mission's recommended group | Real equivalent |
|---|---|
| Platform (Tenants/Modules/Categories/Geography/System Config) | Split across "Providers" (Tenants), "Catalog" (Categories/Verticals), "Platform" group (System Config-adjacent) — not a single unified "Platform" group |
| Home Services (Overview/Catalog/Setup/Pricing/Matching/Jobs/Coverage/Config) | Real "Home Services" group exists with 9 items closely matching this shape (Overview, Service Catalog, Pricing Rules, Customer Price Experience, Provider Matching, Matching Diagnostics, Service Areas/Zones, Completed Job Deduction, Settings) |
| Providers (Businesses/Staff/Verification/Health/Badges) | Real "Providers" group exists (All Providers, New Requests, Verify & Approve, Packages) — Staff/Health/Badges not present as distinct items in this group (Staff is under "Operations" instead) |
| Finance (Usage Credits/Deductions/Deposits/Packages/Ledger) | Real "Finance" group exists (6 items, not independently re-enumerated this sprint) |
| Operations (Jobs/Complaints/Reviews/Service Quality) | Real "Operations" group exists (Bookings, Jobs, Customers, Staff, Reviews, Complaints) |
| Engagement (Notifications/Templates/Rewards/Campaigns) | Real "Marketing & Growth" group exists — different name, roughly overlapping scope |
| Governance (Roles/Permissions/Policies/Audit/Reports) | **Not present as a distinct group** — Roles/Permissions pages exist (`/admin/users/roles`, `/admin/users/permissions`) but are unlinked (see Disconnected Page Resolution Report) |
| Settings | `/admin/settings` exists; not independently confirmed in current `NAV_GROUPS` top-level listing this sprint |

## Missing configuration pages the mission specifically calls out
Health Rules, Badge Rules, Reward Rules, Completed Job Deduction Rules, Credit Threshold Rules, Matching Rules, Availability Policy, Service Area Policy, Provider Verification Rules, Notification Policy — **not individually verified this sprint** whether each exists as a real page (some plausibly exist under Home Services' "Settings"/"Completed Job Deduction" items, others may not exist at all). This would require a dedicated per-item search across the full ~144-route super-admin inventory, not performed this sprint given time constraints.

## Result
Real structural comparison performed; a full Governance group and the specific rule-configuration pages the mission calls out were not individually confirmed/added this sprint. This is documented as a real, honest gap for a future menu-redesign sprint (which the mission itself says belongs to L5-04/05 broadly, and this specific visual reorganization work is explicitly out of THIS sprint's stated scope — "establishes dynamic structure, not final visual redesign").
