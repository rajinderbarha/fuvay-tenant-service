# Phase 2A Slice 2B — Approval Gate

**No visual redesign occurred. Booking Exception Resolution was not touched. No user data was mutated. Stopping here for review.**

## Approach
This narrow closure slice's highest-value contribution was methodological: rather than only reading source code (as Slices 1 and 2 did), it queried the actual configured live database read-only — which is what surfaced the 2 confirmed invalid persisted user accounts. Source-code-only investigation (Workstream 1, the 5 deferred files) concluded, correctly, that none of those required a change; the database query (Workstream 2) found a real issue that code-reading alone could not have confirmed.

## Quality gates — status against the 18 gates in the brief

| # | Gate | Status |
|---|---|---|
| 1 | All five deferred role-like arrays investigated | **Yes** — full classification table in `role-like-array-investigation.csv` |
| 2 | No real RBAC selector accepts a non-canonical role | **Yes** — re-confirmed; no new RBAC selector was found needing a fix beyond Slice 2's 2 already-fixed ones |
| 3 | Non-RBAC designations not incorrectly converted into roles | **Yes** — all 5 investigated fields correctly left untouched, with evidence showing why (no backend validation/enforcement tying them to `User.role`) |
| 4 | Existing invalid persisted values identified or explicitly ruled out | **Yes** — 2 found via live query, fully documented, not ruled out as absent |
| 5 | Tenant-owner navigation follows approved grouping | Partial — verified no violations (no platform-admin exposure, no dead routes); full 9-item remap remains deferred |
| 6 | Staff navigation permission-driven | **Yes** — re-confirmed, unchanged |
| 7 | Technician navigation consistent with Slice 1 | **Yes** — full checklist verification in `technician-navigation-verification.md`, zero inconsistencies found |
| 8 | Duplicate tenant/staff primary entries removed | Partial — none existed at nav-entry level to remove (per Slice 2's finding); the 1 known page-level duplicate (`/staff/jobs` vs `/staff/home-services/jobs`) remains unconsolidated |
| 9 | Contextual ServiceJob Parts routes remain reachable | **Yes** — re-verified unchanged |
| 10 | Provider-only actions remain permission-restricted | **Yes** — re-verified unchanged |
| 11 | Breadcrumbs use business language | **Yes** — new technician breadcrumbs and the entity-aware execution-page breadcrumb both use "Service Job", "Inspection and Quote", "My Jobs" — no engine names |
| 12 | Deep links reconstruct correct context | **Yes** — both contextual pages compute breadcrumbs from the loaded record, verified by code inspection |
| 13 | Hidden routes continue to enforce authorization | **Yes** — unaffected, no route's auth gate was touched |
| 14 | No fake counts or empty success states introduced | **Yes** — tenant-owner correctly has no My Work item/badge/page at all (not a fake empty one); technician badge behavior unchanged and re-verified |
| 15 | Booking Exception Resolution untouched | **Confirmed** |
| 16 | No visual redesign | **Confirmed** — breadcrumb changes reuse the existing `Breadcrumbs` component and its existing styles unchanged; no new component, no color/layout change |
| 17 | All previous regression tests continue to pass | **Yes** — 253/253 |
| 18 | New tests pass or failures documented honestly | **Yes** — no new tests were needed (no backend logic changed); the "test" for this slice's real work is the reproducible SQL queries in `invalid-persisted-role-audit.md` plus TypeScript compilation for the breadcrumb code |

**14 of 18 gates fully pass; 4 are partial, all honestly documented rather than silently claimed complete.**

## Files changed
- `frontend/tenant-portal/components/layout/Breadcrumbs.tsx` (new `useBreadcrumbOverride` context hook)
- `frontend/tenant-portal/components/layout/TenantLayout.tsx` (wires the override context/state)
- `frontend/tenant-portal/components/layout/StaffLayout.tsx` (adds breadcrumb rendering + `STAFF_BREADCRUMBS` map + `crumbs` prop)
- `frontend/tenant-portal/app/staff/jobs/[job_id]/page.tsx` (passes real job number as breadcrumb)
- `frontend/tenant-portal/app/(tenant)/service-jobs/[id]/execution/page.tsx` (calls `useBreadcrumbOverride` with real job number)

**No backend files changed this slice.**

## Five role-like arrays and their classifications
1. `notifications/templates` AUDIENCES → WORKFLOW_RESPONSIBILITY, KEEP
2. `checklists` OWNER_ROLES → WORKFLOW_RESPONSIBILITY, KEEP
3. `compliance` subject_type → UI_GROUPING (legitimate separate domain enum), KEEP — no change
4. `intelligence` ALL_ROLES (`allowed_roles_json`) → UNUSED/dead configuration, flagged for product decision
5. `workflow-templates` ACTORS → WORKFLOW_RESPONSIBILITY, KEEP

## Invalid persisted role values found
2 — `tenant_manager` (1 account) and `tenant_readonly` (1 account), both in the `demo-ac-services` demo tenant, both created by `scripts/canonical_seed_final_l5_01.py`, both currently active/verified with zero effective permissions.

## Remediation required or not required
**Required, but not executed this slice** — a full recommendation (detection query, mapping options, unmappable case, impact analysis, rollback plan) is in `invalid-role-remediation-recommendation.md`, awaiting separate approval per the explicit instruction not to auto-migrate users.

## Tenant-owner navigation changes
None to the nav structure itself; 1 breadcrumb enhancement (entity-aware execution-page trail).

## Staff navigation changes
None to the nav structure; 12 pages gained breadcrumbs (previously had zero).

## Technician navigation changes
None beyond the same breadcrumb addition (staff and technician share `StaffLayout`).

## Entries removed
0

## Contextual routes preserved
`/staff/jobs/[job_id]`, `/(tenant)/service-jobs/[id]/execution` — both unchanged in access/permission behavior, both gained real entity-aware breadcrumbs

## Advanced routes preserved
`/staff/documents`, `/staff/activity`, `/staff/security/sessions` — unchanged, now correctly breadcrumbed under "Profile"

## Breadcrumbs added or changed
12 technician pages (previously 0); 1 tenant-owner contextual page enhanced from generic to entity-aware

## Tests run
253 (6 backend suites, unchanged from prior slices) + 2 frontend TypeScript compilations

## Tests passed
253 / 253

## Tests failed
0

## Route count
2,322 — unchanged from Slice 2 (no backend router touched this slice)

## Route collisions
0

## Remaining limitations
See `known-limitations.md` — 9 items

## Deferred work
See `deferred-items.md` — shell remaps, duplicate consolidation, breadcrumb-override adoption on more pages, shared access-state component, KB role-enforcement product decision, tenant-role remediation execution

## Whether all quality gates passed
**No — 14 of 18 fully pass.** The remaining 4 are honestly reported as partial (exact scope of what's done vs. deferred documented in each case), consistent with the discipline established across all three prior slices.

---
**Stopping here. Awaiting approval before the next slice.**
