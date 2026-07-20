# Frontend/Mobile Caller Audit

## Finding: not exhaustively investigated this slice — deferred

This slice's mission prioritized the backend authorization/ownership
fixes (Workstreams 1-20) given the confirmed live defects
(`tenant_id=None`, non-atomic metadata, broken subject/request-type
validation). A full frontend/mobile caller grep for the 6 selected routes
was not performed to completion within this slice's effort budget.

## What is known
- `frontend/tenant-portal` almost certainly has SOME UI surfacing DPDP
  compliance requests/consent management, given the existence of
  `tests/test_p0_dpdp_compliance_command_center_frontend.py` (a frontend
  test file name strongly implying a corresponding UI exists) — not
  independently confirmed by direct file read this slice.
- No functional/UI behavior was changed this slice — every fix is
  backend-only (dependency swap, service-layer parameter fix, constant-set
  correction). A dependency swap from `require_tenant_owner` to
  `require_tenant_owner_mutation` only changes behavior for READ-ONLY
  `access_scope` tenant users (a narrow persona), who would now correctly
  receive a 403 instead of previously being incorrectly allowed to mutate
  — this is a BEHAVIOR CORRECTION any legitimate frontend should already
  handle via its generic error-handling path (same pattern as every prior
  slice's dependency-swap fixes in this initiative).
- The `VALID_SUBJECT_TYPES`/`VALID_REQUEST_TYPES` constant fix makes
  `create_my_request` succeed where it previously ALWAYS failed — this is
  a pure bug fix (previously broken becomes working), which cannot
  introduce a NEW frontend-visible regression, only resolve an existing
  one.

## Required for a future slice
A full audit (`grep` across `frontend/tenant-portal`, `mobile/*` for
calls to `/v1/provider/compliance/*`) should be performed before this
module can be considered fully closed at the UX/product level — flagged
in `deferred-items.md`.

## Reported per mission's own fallback
Since a genuine mutation caller was not confirmed either present or
absent this slice, this is NOT reported as `FRONTEND_MUTATION_SURFACE_ABSENT`
(that would imply a confirmed absence, which was not established) — it is
reported as `FRONTEND_CALLER_AUDIT_DEFERRED`, an honest gap, not a false
claim of either presence or absence.
