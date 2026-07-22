# Tenant-Owner Navigation Implementation

## Verified, not changed
`frontend/tenant-portal/components/layout/TenantLayout.tsx`'s rendered nav already matches the approved 9-group shape reasonably closely and contains **zero duplicate menu entries** — Phase 1's flagged duplicates (`/provider/reviews`, `/provider/marketing`, `/provider/chat`) are duplicate *pages*, not duplicate *nav entries*; the nav config only ever listed the canonical route in each case.

## Real bug found and fixed
`components/dashboard/MarketingLaunchWidget.tsx` (rendered on the tenant-owner Home dashboard) linked to `/provider/marketing` instead of `/marketing`. This is exactly the kind of inconsistency Workstream 5's "navigation-to-route consistency" check is meant to catch — a widget pointing somewhere different from the canonical nav-listed page for the same feature. Fixed.

## Not done this slice (deferred)
- Full reconciliation of the tenant-owner shell against the approved 9-item grouping (Home, My Work, Jobs, Services, Team, Customers, Business, Credits, Settings) — the current shell has more/different groupings (Overview, Setup, Team, Operations, Finance, Engagement, Insights, More) that were not remapped this slice; remapping ~30+ pages into the new grouping is a page-consolidation-scale change, explicitly excluded ("no broad page consolidation") from this slice.
- Tenant-owner "My Work" nav item and badge — only technician's was implemented in Slice 1; tenant-owner's own My Work source list (business setup incomplete, verification changes requested, etc.) was never built, so there is no tenant-owner My Work page to add to nav yet.
- Removal of `/provider/reviews`, `/provider/marketing`, `/provider/chat`, `/staff/home-services/jobs` as routes (they remain in code, unreferenced from nav, per the "preserve valid functionality without exposing it" rule — no further action was judged necessary since they already have zero real referrers other than the one widget link just fixed).
- Setup-template duplicate entry point reconciliation (two competing template engines per Phase 1A) — backend engine consolidation, out of scope.
- Booking exception actions — correctly absent (not built, not referenced).

## Parts / Credits / Security-deposit placement (verified unchanged, correct)
ServiceJob Parts approval and Mark Installed remain contextual to the job detail page (`/(tenant)/service-jobs/[id]/execution`) — not exposed as a standalone top-level menu item, matching the approved disposition. Security-deposit and credit capabilities remain under their existing Finance-area pages; not relocated this slice (relocating them into a unified "Credits" group per the approved 9-item shell is part of the deferred broader tenant-owner nav remap above).
