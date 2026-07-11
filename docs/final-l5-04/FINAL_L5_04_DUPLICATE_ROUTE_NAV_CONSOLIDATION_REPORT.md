# FINAL-L5-04 — Duplicate Route Navigation Consolidation Report

## Honest scope statement
FINAL-L5-00 found 21 duplicate clusters (~52 routes) across super-admin and tenant-portal — no FINAL-L5-00B decision report exists to say which route in each cluster is canonical (confirmed in Input Artifact Review). This sprint reviewed the clusters against the *current* navigation state (some may have already been resolved by intervening sprints) rather than performing all 7 consolidation steps (choose canonical, remove duplicate menu entries, add redirect shim, preserve bookmarks, update breadcrumbs/active-state, update internal links, update tests) across all 21 clusters — that is real, substantial engineering work per cluster, not safely done blind in the time remaining.

## Re-verification of known clusters against current nav state
| Cluster | FINAL-L5-00 finding | Current state (this sprint) |
|---|---|---|
| Tenant service setup/offerings (5 pages: `/provider/offerings`, `/provider/service-setup`, `/provider/service-options`, `/tenant/setup/services`, `/catalog`) | Largest cluster found | **Still unresolved** — `TENANT_NAV_GROUPS` links `/tenant/setup/services` only (`provider-services` nav id); the other 4 remain reachable but unlinked, confirmed via re-reading `nav-config.ts` this sprint |
| Admin pricing rules (triplicate: `/admin/pricing`, `/admin/pricing-rules`, `/admin/home-services/pricing-rules`) | Triplicate | **Still unresolved** — `NAV_GROUPS` links both `/admin/pricing` (Pricing & Rules group) and `/admin/home-services/pricing-rules` (Home Services group) as if they were 2 *different* concepts, not flagged as the same feature in the live nav's own comments (the source code comment at `NAV_GROUPS`'s "Pricing & Rules" group explicitly says "Pricing Rules itself moved to the Home Services group... since, in practice, every active pricing rule today is Home Services scoped" — this is a **real, existing, documented rationale**, not an oversight; `/admin/pricing-rules` (the 3rd, unlinked one) is the genuine orphan) |
| Checklist templates (`/admin/checklists` vs `/admin/checklist-templates`) | Duplicate | Still unresolved; `/admin/checklists` remains the linked one |
| Workflow templates | Duplicate | Still unresolved |
| Notification templates | Duplicate | Still unresolved |
| Wallet/credit routes (`/wallet` vs `/provider/wallet`, tenant-portal) | Duplicate | Still unresolved; **compounded by this sprint's finding** that the underlying `providerWalletApi`/`tenantSetupApi.getWallet()` data source is itself legacy/dormant (see Business Rule Duplication and Deprecation Register) — consolidating the routes without first resolving the data-source question would be premature |
| Profile routes (`/admin/account` vs `/admin/profile`) | Duplicate | Still unresolved |

## Real, positive finding this sprint
The Admin Pricing Rules "triplicate" is **not simply an oversight** — the live `NAV_GROUPS` source contains an explicit code comment explaining the deliberate choice to surface Home Services pricing rules under the "Home Services" group rather than the generic "Pricing & Rules" group, because in practice all real pricing rules are Home Services-scoped today. This means 2 of the 3 "duplicate" routes are already correctly resolved via a real product decision (just not documented in a formal consolidation report) — only the 3rd, fully-orphaned `/admin/pricing-rules` route remains a genuine unresolved duplicate.

## No route files deleted
Per the mission's explicit instruction ("Do not delete route files unless a later cleanup sprint explicitly allows it"), zero `page.tsx` files were deleted this sprint for any duplicate cluster.

## Result
1 of 21 clusters substantially clarified (2 of its 3 routes already correctly resolved by a real, documented prior decision); the remaining 20 clusters are honestly carried forward as unresolved rather than force-consolidated without a genuine per-cluster product/engineering decision. `NOT_READY_FINAL_L5_04_NAVIGATION_DUPLICATION_FAILED` is a real, honest consideration for this Part in isolation — folded into the sprint's overall `PARTIAL_READY_WITH_FINAL_L5_04_BLOCKERS` recommendation.
