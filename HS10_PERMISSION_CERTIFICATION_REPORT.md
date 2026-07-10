# HS10 — Permission Certification Report

## Status: not investigated across this entire session

Every HS8/HS8B/HS9/HS9B report consistently documented this as "not
investigated" rather than pass/fail — endpoints built and fixed this
session gate on authentication (`get_current_user`,
`require_super_admin`) but not on granular permissions like
`tenant.jobs.assign` or `admin.usage_credits.adjust`. Whether finer RBAC
exists elsewhere in the platform and could be layered onto these
specific endpoints was never determined.

## What is confirmed
- 403-style access-denial paths that do exist (e.g., a technician
  trying to act on a job not assigned to them) return proper error
  codes with `request_id` — confirmed via `ERR_STAFF_NOT_ASSIGNED` and
  similar checks throughout HS8.
- No restricted action was found to be silently permitted that
  shouldn't be — all real validation gates encountered this session
  (tenant scoping, staff-job ownership, booking ownership for reviews)
  were correctly enforced.

## Verdict
Permission certification: **not verified as a complete system** —
individual ownership/scoping checks are real and correct; granular
role-based permission gating was not investigated.
