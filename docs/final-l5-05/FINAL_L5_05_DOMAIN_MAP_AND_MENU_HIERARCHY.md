# FINAL-L5-05 — Domain Map and Menu Hierarchy (Parts 2-3)

## Real current domain map (as-is, not the mission's idealized 18-domain target)
The mission's Part 2 asks for 18 named domains. Mapping them against what's **actually implemented and reachable** today:

| Mission domain | Real canonical route(s) | Completeness |
|---|---|---|
| Dashboard | `/admin/dashboard` | Working |
| Tenants | `/admin/tenants` (+`[id]`, `/onboarding`) | Working |
| Modules and Categories | `/admin/verticals`, `/admin/categories` (+`[id]`) | Working (FINAL-L5-04/04B) |
| Catalog | `/admin/master-services`, `/admin/service-groups`, `/admin/types-brands` — **fragmented**, no single "Catalog" landing page (`/admin/catalog` is a deprecated redirect) | Partial |
| Home Services Configuration | `/admin/home-services/*` (9 real pages) | Working, well-organized already |
| Providers and Staff | `/admin/tenants` (providers ARE tenants in this codebase), `/admin/staff` (+`[id]`) | Working |
| Jobs and Operations | `/admin/operations` (legacy `/v1/jobs`) **and** `/admin/home-services/service-jobs` (canonical `/v1/admin/final-records/jobs`) — **real duplicate, not consolidated this sprint** | Partial — see Bug Register |
| Pricing and Matching | `/admin/pricing*` (4 fragmented pages) + `/admin/home-services/pricing-rules`, `/provider-matching`, `/matching-diagnostics` | Partial — fragmented |
| Usage Credits and Deductions | `/admin/finance/usage-credits`, `/admin/home-services/completed-job-deduction` — **`/admin/finance/usage-credits` not in NAV_GROUPS** | Partial |
| Security Deposits and Packages | `/admin/finance/deposits`, `/admin/packages` | Working |
| Notifications and Engagement | `/admin/notifications`, `/admin/notification-templates`, `/admin/notification-outbox` — **3-way split, not consolidated** | Partial |
| Reviews, Complaints and Quality | `/admin/reviews`, `/admin/complaints`, `/admin/review-flags`, `/admin/review-policies`, `/admin/review-replies` — **4 review-adjacent pages, only 1 in nav** | Partial |
| Geography and Coverage | `/admin/location-mapping` | Working, minimal |
| Users, Roles and Permissions | `/admin/users` (+`[id]`, `/roles`, `/permissions`) | Working |
| Security and Governance | `/admin/security` (+`/threats/[id]`), `/admin/audit-logs` | Working, minimal |
| Reports and Analytics | `/admin/reports`, `/admin/analytics/*` (9 sub-pages) — **`/admin/reports` itself not in NAV_GROUPS** | Partial |
| Platform Configuration | `/admin/settings`, `/admin/engines` (+`[key]`, `/resolver`) | Working |
| Admin Profile and Security | `/admin/profile`, `/admin/account/*` | **Not in NAV_GROUPS at all** — reachable only by direct URL |

## Final menu hierarchy — real decision, not the mission's full idealized redesign
Given this sprint's bounded scope (see Final Report), a **full** menu re-architecture into the mission's 11-domain, 60+-item recommended hierarchy was **not implemented**. That scale of change (moving ~70 orphaned pages into new menu groups, several of which are duplicate-cluster members that first need a canonical-vs-legacy decision) requires dedicated verification per group that exceeds this sprint's safe capacity. What **was** done:
1. Fixed the one real broken nav link found (`hs-overview` → now points to the real, previously-orphaned Overview page).
2. Left the existing 9-group, 43-item NAV_GROUPS structure otherwise intact — it is a real, working, permission-gated (at the shell level), FINAL-L5-04-compliant single source of truth. No second navigation registry was created (rule 1 honored).

## Result
Real domain-by-domain completeness assessed and documented. Menu hierarchy redesign at the mission's full scale is a genuine, large follow-up effort — see Remaining Blockers — not attempted this sprint beyond the one concrete bug fix, to avoid an unverified, high-risk restructuring of the entire admin sidebar.
