# Navigation Before/After — Slice 2B

## Navigation entries
**No nav entries added, removed, or reordered this slice.** All 5 "role-like array" investigations concluded KEEP (no RBAC field was actually wrong) or flag-for-product-decision (intelligence KB's unenforced `allowed_roles_json` — not a nav item). The 2 confirmed-fixed placeholder-role bugs from Slice 2 remain fixed; this slice found their live-data consequence (2 invalid persisted accounts) but did not touch navigation for them.

## Breadcrumbs (the real change this slice)
| Shell | Before | After |
|---|---|---|
| Technician (`StaffLayout`) | No breadcrumbs at all on any of 12 pages | Breadcrumbs on all 12 pages via `STAFF_BREADCRUMBS`; 2 pages (`/staff/jobs/[job_id]`) show the real job number |
| Tenant-owner, `/service-jobs/[id]/execution` | Generic static "Jobs > Service Jobs" regardless of which job | "Jobs > Service Job {job_number} > Inspection and Quote" |

## Forms (carried over from Slice 2, re-verified unchanged, not re-touched this slice)
Super-admin platform-user invite default, tenant-user role selector — both still correct, still tested, no regression.

## Backend (none this slice)
No backend code was changed this slice. The `VALID_TENANT_ROLES` fix from Slice 2 remains as-is; this slice only investigated its live-data consequences (read-only) and produced a remediation recommendation, not an executed fix.
