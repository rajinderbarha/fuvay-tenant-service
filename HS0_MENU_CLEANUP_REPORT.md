# HS0 — Menu Cleanup Report

## Admin menu (`frontend/super-admin/components/layout/AdminLayout.tsx`)
Already correct before this sprint (from an earlier, undocumented-in-this-
session "Home Services Menu Isolation" sprint — comment in the source
references `HOME_SERVICES_MENU_ORGANIZATION_REPORT.md`). Confirmed:
- Dedicated "Home Services" sidebar group exists with all 8 ticket items
  (Overview via price-experience, Service Catalog, Pricing Rules, Customer
  Price Experience, Provider Matching, Matching Diagnostics, Service
  Areas/Zones, Completed Job Deduction, Home Services Settings).
- Common "Pricing & Rules" group contains only vertical-agnostic items
  (Pricing Tiers, City/Zip Mapping, Provider Pricing Overrides) — no
  Bargain Rules, no Home-Services-specific Pricing Rules.
- No "Home Services" items leak into the common/global menu groups.

No changes were needed on the admin side. The secondary
`lib/nav-config.ts` file was updated in this sprint to add a matching
dedicated "Home Services" group (previously it only had a single flat
"Home Services" link inside "Operations") purely for consistency, even
though `AdminLayout.tsx`'s own inline array — not `nav-config.ts` — is
what actually renders.

## Tenant menu (`frontend/tenant-portal/components/layout/TenantLayout.tsx`)
This is where the real forbidden items lived. Fixed this sprint:

| Removed from live nav | Reason |
|---|---|
| "Pricing Setup" (→ `/provider/pricing`) | Ticket-forbidden exact label |
| "Service Pricing Setup" (→ `/tenant/setup/services`, mislabeled) | Ticket-forbidden exact label — the destination itself is canonical and correct, only the label/duplicate-entry was wrong |
| "Customer Price Preview" (→ `/provider/customer-price-preview`) | Ticket-forbidden exact label |
| duplicate "Service Setup" entry (→ `/provider/service-setup`, the superseded page) | Duplicate of the canonical Service Setup nav item |

Setup group now reads exactly: Setup Checklist, Business Profile, Service
Areas, Service Setup, Service Coverage, Availability — matching the
ticket's required 5 items plus Service Coverage (kept as real,
non-duplicate functionality rather than deleted, since the ticket's menu
spec doesn't mention removing it, only doesn't list it).

Standalone "Coverage" group (previously holding Service Areas + Service
Coverage) was removed entirely; both items relocated into Setup.

No bargain-related items ("Bargain Settings", "Bargain Rules", "Manual
Bargain Setup") were ever present in the tenant nav — confirmed via grep,
0 matches both before and after this sprint.

## Verification
`npx tsc --noEmit` clean on both frontends after all menu edits. Grep
confirms 0 occurrences of "Pricing Setup", "Service Pricing Setup",
"Customer Price Preview", "Bargain Settings", "Bargain Rules", "Manual
Bargain Setup", "Price Override Setup" in either live-rendered layout
component.

## Verdict
Menu cleanup: **complete**. Admin was already clean; tenant nav's real
duplicate-menu-item bug found and fixed.
