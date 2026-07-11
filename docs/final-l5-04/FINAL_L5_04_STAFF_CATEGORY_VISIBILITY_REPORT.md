# FINAL-L5-04 — Staff Category and Job Filter Visibility Report

## Real current state
`app/staff/jobs/page.tsx` (tenant-portal's technician-facing jobs list, certified for auth/session in FINAL-L5-01E) displays `service_category`/`job_type` as a **read-only column value** per job row — there is no category filter *control* (dropdown/tabs) on this page at all, confirmed by source read. Technicians see their assigned jobs list unfiltered by category; the category is informational only.

## Required checks
| Check | Result |
|---|---|
| 1. Categories relevant to assigned jobs | The jobs list itself is inherently scoped to `assigned_staff_id` (backend-enforced, established FINAL-L5-01E/02B) — a technician only ever sees their own assigned jobs regardless of category, so "relevant categories" is trivially satisfied by the existing assignment scoping, not by a category-specific mechanism |
| 2. Categories enabled for the technician's tenant | N/A — no category-filter UI exists to scope |
| 3. Filters the technician is allowed to use | N/A — no filter UI exists |
| 4. Historical jobs where policy allows | Not independently tested this sprint |

## Disabled category behavior — checked
| Check | Result |
|---|---|
| 1. No new assignment in disabled category | Not testable at the Staff App level — assignment happens on the Tenant Portal side (`serviceJobAssignmentApi.assign`), not initiated by staff; not independently re-tested this sprint whether the assignment backend blocks assigning a job in a now-disabled category |
| 2. Existing assigned job behavior follows explicit policy | No explicit policy document found; not tested |
| 3. Inactive category does not appear as a new filter option | **Vacuously true** — no filter options exist to have an inactive one appear among |
| 4. No other tenant category appears | **True by construction** — the jobs list is tenant-scoped via `assigned_staff_id`/JWT tenant claim (backend-authoritative, re-verified working in FINAL-L5-02B's isolation testing), so no cross-tenant data of any kind (category or otherwise) can appear regardless of category-specific logic |

## Result
There is no dedicated category-filter feature to certify for Staff — the requirement is satisfied *incidentally* by the existing, already-proven job-assignment scoping (a technician's job list is inherently limited to their own assignments and tenant), not by a purpose-built category-visibility mechanism. This is architecturally sound (no leakage risk) but means Part 9's specific ask (dynamic category *filters*) is unimplemented, consistent with the broader finding that fine-grained category-based UI (as opposed to job-assignment-based scoping) does not exist outside the admin vertical system audited this sprint.
