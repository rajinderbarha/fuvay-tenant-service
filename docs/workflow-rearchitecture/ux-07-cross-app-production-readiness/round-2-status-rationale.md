# Round 2 Status Rationale

## Status: UX07_INTEGRATION_PARTIAL

## Why this status, not a more severe blocked token

- Not `UX07_TEST_ENVIRONMENT_BLOCKED`: the test environment IS operational
  — clean WSL installs succeeded for all 4 relevant app groups, typecheck
  ran clean or with precisely-diagnosed pre-existing errors for every app,
  and unit/component tests ran (and mostly passed) for 3 of 4 app groups.
- Not `UX07_SUPER_ADMIN_ACCESS_BLOCKED`: super_admin access was fully
  resolved and verified live this round (`super-admin-access-investigation.md`).
- Not `UX07_BACKEND_INTEGRATION_BLOCKED`: the one real backend defect found
  (offering_type_id) has a clear workaround (supply the field) and does not
  block the core cross-app proof or this round's other verifications; the
  `500` vs `403` finding is a real but narrow defect, not a blocker to
  anything else this round attempted.
- Not `UX07_AUTHORIZATION_CONTRACT_BLOCKED`: role boundaries were largely
  confirmed correct (customer/tenant_owner/technician all correctly
  rejected from `/v1/admin/*`); the one ambiguous finding (technician
  reading a provider-scoped list) is disclosed as unresolved, not asserted
  as a violation requiring this status.
- Not `UX07_BASELINE_CONFLICT` or `CONCURRENT_WORKTREE_INTERFERENCE`: the
  worktree/branch/HEAD were exactly as the coordinator described at
  session start, and remained so throughout (re-verified before every
  major write).
- Not `INCOMPLETE`: real, meaningful, verifiable progress was made across
  environment setup, super-admin resolution, role verification, catalog/
  pricing continuity, and the offering_type_id root-cause diagnosis — this
  is not a stalled or abandoned round.

## Why PARTIAL, not further progress toward CROSS_APP_PRODUCTION_READY

Per the brief's own explicit instruction, Round 2 was never meant to close
the whole phase. Large workstreams remain deliberately untouched (full
Playwright suites, new automated tests for this round's specific findings,
visual evidence, full onboarding field-by-field trace, backend
remediation) — all honestly itemized in `deferred-workstreams.md` and
`known-limitations.md`.

## Real evidence backing this status

- 1 backend-owned defect root-caused precisely
  (`offering-type-contract-defect.md`) with a ready backend ticket.
- 1 more backend-owned defect discovered (`500` vs `403` on
  provider-service-jobs for a customer token).
- 1 frontend-owned defect found AND fixed
  (`@testing-library/dom` missing dependency), verified stable across 2
  repeated runs.
- 1 frontend-owned defect found and deliberately NOT fixed with full
  reasoning (React version pin mismatch).
- super_admin access fully resolved and live-verified.
- Round 1's real booking (`BK-20260721-000008`) confirmed still intact and
  unmodified.
