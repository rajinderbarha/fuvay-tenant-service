# Navigation Before/After

## Super-admin (`frontend/super-admin`)

### Home Services group
**Before:** hs-overview, hs-service-catalog, hs-pricing-rules, hs-price-experience, hs-provider-matching, hs-matching-diagnostics, hs-service-areas, hs-completed-job-deduction, hs-settings (9 items)
**After:** + `bookability` ("Provider Bookability" → `/admin/bookability/providers`) — **added this slice**

### Finance group
**Before:** finance, finance-usage-credits, finance-deposits, finance-topups, finance-claims, finance-payouts, compliance (7 items)
**After:** + `finance-service-invoices`, `finance-provider-wallets`, `finance-commission-records`, `finance-payments`, `finance-financial-events` (5 items) — **all added this slice**, inserted between finance-payouts and compliance

### Unchanged (verified, not drifted despite Phase 1 flagging them)
Analytics, Reports — both already present in `Marketing & Growth` group with real permission gating (`analytics:dashboard:read`). Real-estate/coaching — dynamically injected per-vertical, not static drift. AI/AI-chat — correctly absent from top-level nav per the approved `CONTEXTUAL_ROUTE` disposition (Decision 4 chat consolidation remains explicitly out of scope).

## Tenant-owner (`frontend/tenant-portal`)

### Rendered nav — no change
`TenantLayout.tsx`'s `NAV_GROUPS` already contained no duplicate entries pointing at `/reviews`+`/provider/reviews`, `/marketing`+`/provider/marketing`, or `/chat`+`/provider/chat` — only the single canonical href in each case. Phase 1's "duplicate nav entries" finding referred to duplicate *pages existing in the codebase*, not duplicate *menu entries* — those pages already had zero menu entries before this slice.

### Real bug found and fixed
`MarketingLaunchWidget.tsx` (a dashboard component, not the sidebar) linked to `/provider/marketing` — the orphaned duplicate page — instead of `/marketing`. This was a genuine navigation inconsistency: a user clicking "Details" on their dashboard's Marketing widget landed on a different page than the one reachable from the Marketing nav item. Fixed to link to `/marketing`.

## Staff/technician (`frontend/tenant-portal` StaffLayout)

### Before
Dashboard, My Work (added Slice 1), My Profile, Skills & Services, Service Areas, Availability, Assigned Work, Messages, Documents, Notifications, Activity, Security/Sessions (12 items)

### After
Same 12 items — no additions/removals this slice. **Change:** the My Work nav item now shows a real-data badge (see `navigation-badge-sources.md`).

## Summary of net navigation changes this slice
- **6 nav entries added** (super-admin): bookability, service-invoices, provider-wallets, commission-records, payments, financial-events
- **0 nav entries removed** (none were duplicated in the first place)
- **1 broken internal link fixed** (tenant-owner dashboard widget)
- **1 badge added** (technician My Work count)
