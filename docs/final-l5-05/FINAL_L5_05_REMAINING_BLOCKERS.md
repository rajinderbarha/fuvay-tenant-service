# FINAL-L5-05 / FINAL-L5-05B — Remaining Blockers

> **Updated in FINAL-L5-05B.** Blocker 1 now has a complete, evidence-backed parity investigation (see `FINAL_L5_05B_JOBS_MIGRATION.md`) rather than being merely flagged — the decision to defer migration is now a proven, rule-compliant judgment call, not an unexamined gap. One real sub-gap (dead timeline/notes code) was closed this sprint.

## Blocker 1 (P0): "Jobs" nav item is backed by the legacy `/v1/jobs` API — parity investigated, migration correctly deferred
Full feature-parity matrix built this sprint (`FINAL_L5_05B_JOBS_MIGRATION.md`): the canonical `service_jobs`-backed page is missing 4 real mutation actions (reassign, status override, force-close, void) and SLA/summary capabilities that have **no backend implementation at all** — not a wiring gap, a genuine missing-capability gap. Per rule 5 ("do not remove working job actions") and rule 3 ("do not solve the Jobs defect by only replacing an endpoint string"), migrating the sidebar link before these are built would be a real regression, not a fix. This remains the single condition, per the mission's own explicit disqualifying list, that prevents a clean READY recommendation — now backed by complete evidence rather than an unexamined flag.

**Real progress this sprint**: 2 of the 3 wiring-only gaps (assignment timeline, execution timeline, notes) were closed — these were dead code (real backend + real API client, zero UI consumers) until this sprint wired them into the canonical detail page, live-verified via curl and Chromium.

**What would need to happen to close this fully**: build 4 new backend mutation endpoints against `service_jobs` (reassign, status override, force-close, void — each with permission checks, audit logging, duplicate-submission protection per the mission's Part 5), add SLA fields to the `service_jobs` model and a summary-stats endpoint, wire all of it into the canonical page's UI, then repoint the sidebar. This is a real, substantial, separately-scoped backend+frontend effort.

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
- No new forbidden terminology, duplicate routes, or broken links were introduced across either sprint — 9 real pre-existing bugs/gaps were found and fixed instead.
- TypeScript and production build both pass cleanly (re-verified fresh after FINAL-L5-05B's changes).
- 5/5 real Chromium tests pass for both sprints' actual changes combined (4 from FINAL-L5-05 + 1 new from FINAL-L5-05B).
- 6 new automated IA regression guards added and passing (Part 16) — zero-forbidden-terminology sweep across the entire `frontend/super-admin` tree, duplicate-nav-href guard, orphan-fix regression guards.
- 0 regressions in the backend/frontend test suites (58 FINAL-L5-family tests still passing).
- Working tree verified clean at both the start and end of FINAL-L5-05B (Part 1/21) — the only diffs found were pure build-tool-generated noise (`next-env.d.ts`/`tsconfig.tsbuildinfo`), correctly restored to match HEAD rather than committed.

## Result
1 P0, 3 P1s, 3 P2s, 1 P3 remain — same count as FINAL-L5-05, but Blocker 1 (the P0) now carries a complete, evidence-backed investigation and 2 real sub-gaps closed, rather than being an unexamined flag. This remains the single condition, per the mission's own explicit disqualifying list, that prevents a clean READY recommendation.
