# Phase 2A Slice 2B — Implementation Summary

## Approach
This is explicitly framed as a narrow closure slice. Per the established discipline from Slices 1 and 2, work was scoped to what could be done with real, verified evidence rather than broad rebuilds. The single most valuable action this slice took was **querying the actual live database** (read-only) rather than reasoning only from source code — this surfaced a confirmed, currently-live authorization bug that source-reading alone (Slice 2's approach) had not caught.

## Workstream 1 — Role-like array investigation (all 5 files classified)

| File | Field | Classification | Action |
|---|---|---|---|
| `notifications/templates/page.tsx` | `AUDIENCES` | WORKFLOW_RESPONSIBILITY | KEEP — never written to `User.role`, no backend validation, used only to select which notification template to send |
| `checklists/page.tsx` | `OWNER_ROLES` | WORKFLOW_RESPONSIBILITY | KEEP — same pattern, `owner_role` is an unenforced descriptive tag on a checklist step |
| `compliance/page.tsx` | `subject_type` options | UI_GROUPING (legitimate distinct domain enum) | KEEP, no change — this is `ComplianceRequest.subject_type`, a real, backend-validated (`VALID_SUBJECT_TYPES`), self-consistent DPDP categorization scheme unrelated to RBAC; "fixing" it to match RBAC roles would break a working, validated feature |
| `intelligence/page.tsx` | `ALL_ROLES` (→ `allowed_roles_json`) | UNUSED / dead configuration | Flagged for product decision — stored, returned by the API, but never read back to gate anything at query time; cosmetic today, but presents as a working access control when it isn't one |
| `workflow-templates/page.tsx` | `ACTORS` | WORKFLOW_RESPONSIBILITY | KEEP — same unenforced descriptive-tag pattern as checklists' `owner_role`, confirmed by the pre-existing hardcoded step data in `workflow_service.py` using the same vocabulary |

**None of the 5 required a code change.** All are non-RBAC fields (template targeting, checklist/workflow step responsibility tags, or a legitimate separate domain enum) that happen to contain role-sounding words — exactly the trap the brief's rule 1 ("do not blindly replace every role-like string") warns against. Full evidence trail in `role-like-array-investigation.csv`.

## Workstream 2 — Persisted invalid-role data check (real finding)

A read-only query against the live configured database (`postgresql+asyncpg://serviceos:serviceos@127.0.0.1:5432/serviceos`) found:
- **2 active, verified user accounts with invalid `role` values right now**: `manager@demo-ac-services.local` (`role='tenant_manager'`) and `readonly@demo-ac-services.local` (`role='tenant_readonly'`), both created 2026-07-11 by `scripts/canonical_seed_final_l5_01.py`, both in the `demo-ac-services` demo tenant.
- Both role strings were already removed from `VALID_TENANT_ROLES` in Slice 2 (so this seed script's write path is now blocked going forward for new users) — but these 2 **existing** rows were written before that fix and are untouched by it (Slice 2's fix only prevents new invalid writes, per its own scope).
- A **related bug was already found and fixed by a prior engineer**: `scripts/seed_admin_roles_final_l5_05l.py` exists specifically to repoint 3 demo admin accounts that this same seed script (`canonical_seed_final_l5_01.py`) had created with `role='super_admin'` instead of their intended least-privilege roles. The live database confirms this remediation **has been applied** (`admin_operations`/`admin_finance`/`admin_security`/`admin_readonly` each show exactly 1 row; `super_admin` shows 3, not 6).
- No equivalent remediation script exists yet for the 2 `tenant_manager`/`tenant_readonly` accounts — that gap is addressed in `invalid-role-remediation-recommendation.md`.
- Confirmed low blast radius: 4 total tenants in this database, 0 `staff_permissions` override rows for either broken account, and the seed script is not referenced by any Dockerfile/docker-compose/CI file found — manual-invocation-only risk.

**No data was mutated.** Full detail in `invalid-persisted-role-audit.md` and the required remediation recommendation in `invalid-role-remediation-recommendation.md`.

## Workstreams 3-5 — Navigation shells (verified, narrow fixes only)
No broad shell rebuild was attempted (explicitly excluded — "guided onboarding, provider setup redesign" etc. are out of scope, and a full remap of ~30 tenant-owner pages or a distinct staff/manager shell would be page-consolidation-scale work). Verified: no platform-admin pages exposed to tenant-owner, no dead brand routes, Parts/Mark Installed scoping unchanged and correct, technician shell unchanged and consistent with Slice 1. See `tenant-owner-navigation.md`, `staff-navigation.md`, `technician-navigation-verification.md`.

## Workstream 7 — Breadcrumbs (real implementation, not just verification)
The technician shell (`StaffLayout`) had **zero breadcrumb rendering at all** before this slice — a genuine gap, not previously documented. Implemented:
1. A `Breadcrumbs` render call in `StaffLayout.tsx` with a technician-specific static map (`STAFF_BREADCRUMBS`) plus an optional `crumbs` prop for contextual override.
2. A new `useBreadcrumbOverride()` context hook in the shared `Breadcrumbs.tsx`, allowing a contextual detail page several component-levels below the auto-mounted `TenantLayout` to inject a real entity name into the trail — used by the `/service-jobs/[id]/execution` page to show `Jobs → Service Job {job_number} → Inspection and Quote` instead of the generic static "Jobs → Service Jobs" the shared page-registry previously produced for every job.
3. The technician job detail page (`/staff/jobs/[job_id]`) now shows `My Jobs → {job_number}`.

## Non-negotiable rules — compliance check
No invented role aliases (`tenant_manager` etc.) were reintroduced. No automatic user migration was performed — the 2 confirmed invalid accounts remain untouched, with a remediation recommendation (not an executed fix) provided per the explicit instruction. Booking/job pipelines untouched. No visual redesign — breadcrumb work reuses the existing `Breadcrumbs` component and its existing styling unchanged. All Slice 1 and Slice 2 tests still pass.
