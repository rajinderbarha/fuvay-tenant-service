# Final Certification Report — Slice 2F-38

## Final status

**`MIGRATION_AND_ROLE_DATA_READINESS_BLOCKED`**

## What is solidly proven

- The 313 canonical tenant/provider mutations remain protected, 0
  unprotected, independently re-derived (not copied) via
  `verify_2f37.py` (21/21 PASS, run 3 separate times across 3 separate
  worktrees this program: 2F-37R-A ×2, this slice), plus a fresh
  `--selftest` confirming all 21 rules genuinely detect their own
  violation.
- Exactly the 10 canonical roles are executable
  (`ROLE_PERMISSIONS.keys()` introspected live); the one alias reference
  found in the codebase (`roles_permissions/service.py`'s display catalog)
  is read-only and non-executable, confirmed by reading the module in
  full.
- `tests/test_phase2f*.py`: 2445/2445 passed, 0 failed, run twice,
  identical — the fourth independent confirmation of this exact figure
  across this program.

## Why full application-wide certification is blocked — three independent reasons

1. **Role data.** `manager@demo-ac-services.local` and
   `readonly@demo-ac-services.local` remain `MANUAL_ROLE_CONFIRMATION_REQUIRED`
   — no evidence-backed canonical mapping exists for either, reconfirmed
   this slice, unchanged since Slice 2C. See
   `manual-role-confirmation-request.md`.
2. **Migration environment.** No PostgreSQL/Docker is reachable in this
   environment; Migration 144's apply/rollback/reapply sequence cannot be
   executed or proven safe here. See `postgres-environment-evidence.md`.
3. **New finding this slice: seed-script role guard.** Running the
   complete backend suite (not just Phase-2F) for the first time in this
   program surfaced that `scripts/canonical_seed_final_l5_01.py::get_or_create_user()`
   has zero role-validation logic — it will insert any string as a
   user's role with no canonical check. This directly falsifies the
   required claim "no seed recreates invalid roles" and represents a live,
   currently-exploitable path to reintroduce exactly the class of defect
   this whole slice is trying to close. See `full-backend-regression-report.md`.

Any one of these three would independently block
`APPLICATION_WIDE_MUTATION_AUTHORIZATION_CERTIFIED` and
`..._CERTIFIED_WITH_KNOWN_DOMAIN_LIMITATIONS`. All three exist
simultaneously.

## Additional finding that would independently block full certification even if the above were resolved

**The mounted-route census is incomplete.** Of ~1,186 auto-detected
mutation routes, only the 313 canonical ones received this program's full
manual audit. 261 remain classifier-`UNVERIFIED`; 89 more were only
spot-checked (12 of 89). See `mutation-disposition-census.md`. This alone
— independent of role data or Migration 144 — means "no UNKNOWN route
remains" and "platform-admin/customer/internal mutations are certified"
cannot be honestly claimed today. Completing this is comparable in scope
to the entire 2F-35/36/37 program and was not achievable within this
slice.

## Full-backend regression status

12,096 collected, 12,030 passed, 45 failed, 21 skipped (one run; see
`full-backend-regression-report.md` for full classification: 1 test-order
artifact, 8 tied to the seed-script finding above, 36 pre-existing/
unrelated-domain failures not caused by this program). This is not a
clean complete-suite regression, but the failures are attributable and
explained, not concealed.

## Preserved limitations (unchanged, not resolved by this slice)

N01 media (`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`), payments financial
integrity, pricing/item-location read-path privacy gaps, Booking Exception
Resolution, customer cancellation/rescheduling — see
`final-known-limitation-registry.csv` for the complete registry.

## What this slice did NOT do

- Did not apply Migration 144, anywhere, including non-production.
- Did not assign a role to either demo account.
- Did not fix the seed-script gap (outside this slice's allow-list;
  flagged for a future authorized slice).
- Did not modify any UX branch, any application file outside its own new
  documentation/tooling, or any historical artifact.
- Did not begin Slice 2F-38's own certification claim beyond this bounded
  report, and does not begin any further phase.
