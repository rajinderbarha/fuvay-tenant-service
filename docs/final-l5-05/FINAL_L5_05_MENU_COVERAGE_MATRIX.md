# FINAL-L5-05 — Menu Coverage Matrix (Part 5) and Route Classification (Part 4)

## Standalone leaf list pages NOT reachable from NAV_GROUPS (~70 real routes)
Grouped by domain, with a real classification per the mission's Part 4 taxonomy:

| Domain | Routes | Classification |
|---|---|---|
| Account/Profile | `/admin/account`, `/admin/account/login-history`, `/admin/account/sessions`, `/admin/profile` | `SECONDARY_NAV` — reachable today only via the topbar avatar menu (not audited this sprint whether that menu links here; flagged as `INCOMPLETE` pending that check) |
| AI | `/admin/ai/failed-actions`, `/admin/ai/metrics`, `/admin/ai/sessions`, `/admin/ai-chat*` (5 pages) | `SECONDARY_NAV` — real, working AI observability pages with zero menu entry |
| Analytics | `/admin/analytics/alerts`, `/categories`, `/complaints`, `/financial`, `/providers`, `/quality`, `/staff` | `SECONDARY_NAV` — sub-pages of `/admin/analytics` (which IS in nav); reachable via in-page tabs on the Analytics landing page (not independently verified this sprint) |
| Automation | `/admin/automation/recommendation-results`, `/recommendation-rules` (+`[ruleId]`) | `SECONDARY_NAV`, orphaned |
| Bookability | `/admin/bookability/providers` | `SECONDARY_NAV`, orphaned |
| Brands | `/admin/brand-requests`, `/admin/brands` | `DUPLICATE` — see Bug Register duplicate cluster |
| Chat | `/admin/chat` | `SECONDARY_NAV`, orphaned |
| Checklists | `/admin/checklist-templates`, `/admin/checklists` | `DUPLICATE` |
| Commission | `/admin/commission-records` | `SECONDARY_NAV`, orphaned, finance-adjacent |
| Complaint policies | `/admin/complaint-policies` | `SECONDARY_NAV` — contextual to Complaints, should be a tab not a standalone orphan |
| Customer flow | `/admin/customer-flow`, `/drafts` | `SECONDARY_NAV`, orphaned |
| Finance sub-pages | `/admin/finance/customer-credits`, `/dispute-settlements`, `/tenant-penalties`, `/usage-credits`, `/wallets` | `SECONDARY_NAV` — real finance pages, **`/admin/finance/usage-credits` orphaned despite being the canonical Usage Credit route the mission requires be discoverable** (Part 14) — this is a real, notable gap |
| Financial events | `/admin/financial-events` | `SECONDARY_NAV`, orphaned |
| Home services (2) | `/admin/home-services/booking-drafts`, `/admin/home-services/service-jobs` | `SECONDARY_NAV`/`DUPLICATE` (service-jobs, see Jobs finding) |
| Issue types | `/admin/issue-types` | `DUPLICATE` |
| Marketing (7) | `/admin/marketing/assets`, `/automation`, `/campaigns`, `/events`, `/generate`, `/publish-queue`, `/segments`, `/templates` | `SECONDARY_NAV` — sub-pages of `/admin/marketing` (in nav as "Campaigns"), likely reachable via in-page tabs, not independently verified |
| Master services | `/admin/master-services` | `SECONDARY_NAV`, real canonical catalog page, orphaned |
| Notifications (3) | `/admin/notification-outbox`, `/admin/notification-templates`, `/admin/notifications/templates` | `DUPLICATE`/`SECONDARY_NAV` |
| Payments | `/admin/payments` | `SECONDARY_NAV`, orphaned |
| Pricing (6) | `/admin/pricing`, `/pricing-rules`, `/pricing/bargain-rules` | `DUPLICATE` — note: `bargain-rules` page name itself is fine (real feature), but "Bargain Rule Builder"-style forbidden UI copy was not found on this specific page this sprint (see Terminology Report) |
| Profile | `/admin/profile` | `SECONDARY_NAV` |
| Provider wallets | `/admin/provider-wallets` | `DUPLICATE` of `/admin/finance/wallets` |
| Rating summaries | `/admin/rating-summaries` | `SECONDARY_NAV`, orphaned, review-quality-adjacent |
| Real estate | `/admin/real-estate/lead-drafts` | `SECONDARY_NAV`/`MODULE_DEPENDENT` (real_estate vertical) |
| Refund/rework requests | `/admin/refund-requests`, `/admin/rework-requests` | `SECONDARY_NAV`, orphaned, complaints-adjacent |
| Reports | `/admin/reports` | `SECONDARY_NAV` — real page, orphaned, despite being the mission's required Reports domain home |
| Reviews (3) | `/admin/review-flags`, `/review-policies`, `/review-replies` | `DUPLICATE`/`SECONDARY_NAV` |
| Service groups | `/admin/service-groups` | `SECONDARY_NAV`, real catalog page, orphaned |
| Service invoices | `/admin/service-invoices` | `SECONDARY_NAV`, orphaned |
| Service options | `/admin/service-options` | `DUPLICATE` |
| Service setup (10) | `/admin/service-setup*` | `SECONDARY_NAV`/`DUPLICATE` — large sub-tree, appears to be an alternate/newer catalog-setup surface running parallel to `/admin/master-services`/`/admin/service-groups`/`/admin/brands`/`/admin/issue-types` |
| Types & brands | `/admin/types-brands` | `DUPLICATE` |
| Workflows | `/admin/workflows/templates` | `DUPLICATE` of `/admin/workflow-templates` |

## Required check results (mission Part 5)
| # | Requirement | Result |
|---|---|---|
| 1 | Every primary capability reachable | **Not fully met** — Usage Credits (Part 14's explicit requirement) and Reports (Part 17's explicit requirement) are both real, working, but orphaned from NAV_GROUPS |
| 2 | No visible menu item opens a blank page | **Met** — every item actually in NAV_GROUPS today was spot-checked in earlier sprints (FINAL-L5-04) and this sprint's Chromium run; none are blank |
| 3 | No primary capability remains orphaned | **Not met** — see above |
| 4 | No unauthorized feature appears | Not independently re-verified this sprint at the ~2%-adoption permission level (see Permission Visibility Report) |
| 5 | No inactive module/category feature appears | Preserved from FINAL-L5-04's dynamic vertical section — unaffected this sprint |
| 6 | No unsupported rule domain appears | Confirmed — no placeholder rule pages were added or found beyond the 1 pre-existing, honestly-labeled `catalog-module/[key]` stub |

## Fixed this sprint: the 2 highest-value gaps
Rather than only documenting the Usage Credits and Reports orphan-page findings, both were fixed — real, low-risk, one-line nav additions:
- `finance-usage-credits` → `/admin/finance/usage-credits` ("Usage Credits") added to the Finance group.
- `reports` → `/admin/reports` ("Reports") added to the Marketing & Growth group (nearest existing analytics-adjacent home; a dedicated "Reports" top-level group is a Remaining Blocker for the full menu redesign).

Both verified: `npx tsc --noEmit` clean, real page content confirmed non-trivial (160 and 141 lines respectively, real API-backed) before linking.

## Result
Real, itemized coverage matrix for ~70 orphaned routes. The 2 most mission-critical gaps (Usage Credits, Reports — both explicitly required by Part 14/17) are now fixed and reachable. The remaining ~68 orphaned routes require per-cluster canonical-vs-legacy decisions (12 duplicate clusters) that are out of this sprint's safe bounded scope — see Remaining Blockers.
