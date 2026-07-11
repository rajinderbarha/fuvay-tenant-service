# FINAL-L5-04B — Staff Entitlement Scope Report

## Not implemented this sprint — honest scope statement
No code change was made to staff/technician category filters or job-assignment logic (`/staff/*` routes within `frontend/tenant-portal`, backed by `app/engines/*` staff routers). No entitlement check was added to any staff-facing endpoint.

## Required checks — status
| # | Check | Result |
|---|---|---|
| 1 | Staff category filters include only tenant-entitled categories | Not implemented — staff category filters (wherever they exist in the technician UI) are unaware of `tenant_category_entitlements` |
| 2 | New assignments cannot use disabled categories | Not implemented |
| 3 | Staff cannot access another tenant's categories | **Unaffected, pre-existing** — tenant isolation for staff is already enforced by the existing `tenant_id` JWT-scoping used throughout the app (unrelated to this sprint, not re-verified here) |
| 4 | Existing assigned jobs follow historical-job policy | **True by default** — no historical job data was touched this sprint |
| 5 | `StaffContextProvider` remains the single auth-context owner | Unaffected — no auth-context code was touched this sprint |
| 6 | No duplicate `/v1/auth/me` requests | Unaffected — no changes to auth-context fetching were made |

## Why deferred
Consistent with the Matching and Customer Availability gaps: staff category-scope filtering is only meaningful once the underlying entitlement-aware provider/category resolution exists somewhere staff-side code can consume. Given the same category-level plumbing gap exists here as in matching/customer discovery, and no staff-specific code was touched or needed to be touched to deliver this sprint's real, verified core (data model, admin API, tenant self-read API, module-level nav gating, service-setup enforcement), this was left out of scope rather than attempted as an unverified surface change.

## Result
Not implemented. Documented as a real, honest gap — see Remaining Blockers.
