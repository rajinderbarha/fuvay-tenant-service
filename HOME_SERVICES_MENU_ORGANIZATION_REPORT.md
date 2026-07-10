# Home Services Menu Organization Report

## Before

`frontend/super-admin/components/layout/AdminLayout.tsx` had "Pricing
Rules" (`/admin/pricing-rules`) living in the common/global "Pricing &
Rules" nav group, alongside genuinely multi-vertical infra (Pricing
Tiers, City/Zip Mapping, Provider Pricing Overrides). This was the one
real menu-organization leak in the app — everything else Home-Services-
specific (Service Catalog, Customer Price Experience, Provider Matching,
Matching Diagnostics) was already correctly grouped under "Home Services"
from prior sprints this session, and no other page (brands, issue-types,
service-options, types-brands) is linked directly in the top nav at all.

## After

- **Removed** `pricing-rules` (`/admin/pricing-rules`) from the "Pricing &
  Rules" common group.
- **Added** `hs-pricing-rules` (`/admin/home-services/pricing-rules`,
  a new, real page) to the "Home Services" group.
- **Added** 3 more new Home Services group items: Service Areas / Zones
  (`/admin/home-services/service-areas`), Completed Job Deduction
  (`/admin/home-services/completed-job-deduction`), Home Services
  Settings (`/admin/home-services/settings`) — all new, real pages.
- "Pricing & Rules" group now contains only genuinely vertical-agnostic
  items: Pricing Tiers, City/Zip Mapping, Provider Pricing Overrides.

## Final "Home Services" nav group (9 items)

Overview, Service Catalog, Pricing Rules, Customer Price Experience,
Provider Matching, Matching Diagnostics, Service Areas / Zones, Completed
Job Deduction, Home Services Settings — matching the ticket's required
list exactly.

## Verification

Confirmed via static test (`test_home_services_nav_group_has_all_required_items`,
`test_pricing_rules_removed_from_common_pricing_group`,
`test_no_home_services_item_duplicated_in_another_group`) that every
Home-Services href appears exactly once, only inside the Home Services
group, never in any other nav group.
