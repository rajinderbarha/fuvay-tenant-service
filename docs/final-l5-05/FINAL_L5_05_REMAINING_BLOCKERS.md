# FINAL-L5-05 — Remaining Blockers

## Blocker 1 (P0): "Jobs" nav item is backed by the legacy `/v1/jobs` API
Directly implicates rule 12 and Part 12's explicit "no /v1/jobs dependency" requirement. Real, root-caused, not fixed — see Bug Register L5-05-008. This alone is sufficient to prevent a clean READY under this mission's own disqualifying condition #8 ("`/v1/jobs` is reintroduced" — more precisely, remains actively depended on by the primary nav item, which the mission's spirit treats the same as reintroduction since Part 12 requires its absence as a certification gate).

## Blocker 2 (P1): 11 of 12 duplicate route clusters not resolved
Brands, Service Options, Issue Types, Pricing (3-way), Notifications, Reviews (4-way), Workflows, Checklists, Types & Brands, Provider Wallets, Service Setup (large sub-tree potentially superseding several older catalog pages). Each requires a real feature-parity read before a safe canonical/legacy decision — not attempted at scale this sprint.

## Blocker 3 (P1): ~68 real orphaned leaf pages remain unreachable from the sidebar
2 of the most mission-critical (Usage Credits, Reports) were fixed this sprint. The rest (AI observability, Analytics sub-pages, Marketing sub-pages, Service Setup sub-tree, Master Services, Service Groups, Complaint Policies, Refund/Rework Requests, Rating Summaries, etc.) remain real, working, but undiscoverable except by direct URL.

## Blocker 4 (P1): No finer-grained permission-based menu/action visibility
`usePermissions()` adoption is ~2%. The mission's Admin Finance/Admin Operations/Security Admin role-visibility requirements (Part 23) cannot be tested because those roles don't exist as distinct concepts in the current backend auth model — building them is a separate, large, cross-cutting change.

## Blocker 5 (P2): `page-registry.ts` breadcrumb coverage remains ~25%
Unchanged from FINAL-L5-04's own documented gap; the 2 newly-linked pages this sprint don't have dedicated entries either (fall back to generic breadcrumbs).

## Blocker 6 (P2): No responsive/mobile Super Admin navigation exists at all
Re-confirmed unchanged from FINAL-L5-04's finding — zero responsive logic in `AdminLayout.tsx`. Not tested at the mission's 10 breakpoints this sprint since there's nothing breakpoint-aware to test.

## Blocker 7 (P2): Accessibility gaps unchanged
No `aria-current="page"` on active nav items; no verified focus-visible styling (both carried over from FINAL-L5-04, not addressed this sprint).

## Blocker 8 (P3): Full menu hierarchy redesign (mission's 11-domain, 60+-item structure) not attempted
The existing 9-group, 43-item structure was preserved and incrementally improved (3 real bugs fixed, 2 real gaps closed) rather than replaced — a full redesign at the mission's proposed scale requires resolving Blockers 2 and 3 first (you can't cleanly group ~140 routes into a new hierarchy while 68 of them don't even have a confirmed canonical status yet).

## Not a blocker (real, working, re-confirmed this sprint)
- Breadcrumbs and active-state mechanism (FINAL-L5-04) — unchanged, working, re-verified live.
- Backend authorization does not rely on frontend hiding anywhere touched this sprint.
- `tenant_wallets` is confirmed dead code (comments only, no live reads).
- No new forbidden terminology, duplicate routes, or broken links were introduced this sprint — 7 real pre-existing bugs were found and fixed instead.
- TypeScript and production build both pass cleanly.
- 4/4 real Chromium tests pass for this sprint's actual changes.

## Result
1 P0, 3 P1s, 3 P2s, 1 P3 remain. The P0 (`/v1/jobs` on the primary Jobs nav item) is the single condition that, per the mission's own explicit disqualifying list, prevents a clean READY recommendation this sprint.
