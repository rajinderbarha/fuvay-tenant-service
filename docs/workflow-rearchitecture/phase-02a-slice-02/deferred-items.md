# Deferred Items

## Workstream 2 — Super-admin navigation
- Full re-audit of admin_readonly mutation-exclusion across all ~50+ admin pages (only 2 spot-checked).
- Closing the backend `require_super_admin` gating gap (Phase 1A backend-blockers.md #7) — separate backend workstream.

## Workstream 3 — Tenant-owner navigation
- Remapping the tenant-owner shell to the approved 9-item grouping (Home, My Work, Jobs, Services, Team, Customers, Business, Credits, Settings) — the current 8-group shell was not restructured.
- Tenant-owner My Work source/page/badge — no aggregation endpoint exists yet for this role.

## Workstream 4 — Staff and technician navigation
- Distinct 7-item "Staff/Manager" shell separate from technician's — requires new pages (Team, Customers, Business views), out of this slice's "no new workflow pages" constraint.
- Relabeling/reorganizing the technician shell's 12 items into the approved 5-item target grouping (Today, My Work, My Jobs, Inspection and Quote, Work Completion, Profile) — this is page-consolidation-scale work.

## Workstream 6 — Non-canonical entry restrictions
- 5 files with placeholder-role-shaped tag arrays (`notifications/templates`, `checklists`, `compliance`, `intelligence`, `workflow-templates`) — needs per-file investigation of whether each tag has a real authorization consequence before a correct fix can be made.

## Workstream 7 — Navigation counts and badges
- Deduplicating the My Work badge's network call against the My Work page's own fetch (minor perf item).

## Workstream 8 — Route access states
- A shared, reusable route-access-state component/pattern across all 3 apps.

## Workstream 9 — Breadcrumbs
- Full breadcrumb reconciliation to workflow-grouped, non-engine-named labels across all apps.

## Not in scope for any future slice unless separately approved
Booking Exception Resolution, booking pipeline merging/adapters, visual redesign, AI chat consolidation, broad page consolidation.

## Recommended next slice
Given this slice found a genuine, previously-undiscovered authorization bug (tenant-user placeholder roles) purely by reading code carefully rather than assuming Phase 1's audit was exhaustive, the next slice should likely include a **targeted grep-and-read pass over the remaining 5 placeholder-role-tag files** before any further nav/page work — cheap to do, and this slice demonstrated it's a real risk area (2 for 2 confirmed bugs found this way, both undiscovered by prior phases).
