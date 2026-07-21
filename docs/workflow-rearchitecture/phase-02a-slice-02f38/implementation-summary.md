# Slice 2F-38 — Implementation Summary

## Final status: `MIGRATION_AND_ROLE_DATA_READINESS_BLOCKED`

This is the second attempt at Slice 2F-38. The first correctly stopped
with `FROZEN_SCOPE_MISMATCH` (the authorization program was entirely
uncommitted, on an unrelated UX branch). Slices 2F-37R and 2F-37R-A
closed that blocker by recovering and committing a verified baseline
(`security/phase-2f-authorization-recovered @ 01e6ee4`). This slice
restarted from that commit in a fresh, dedicated worktree
(`G:/serviceos-phase2f38-certification`, branch
`security/phase-2f38-certification`).

## What is solidly proven

- Canonical 313/313 tenant/provider mutation coverage, independently
  re-derived (not copied from docs) via `verify_2f37.py`, run 3 times
  across 3 separate worktrees this program (21/21 PASS each time),
  including a fresh `--selftest` confirming all 21 rules genuinely detect
  their own violation.
- Exactly the 10 canonical roles are executable; the one alias reference
  found (`roles_permissions/service.py`'s display catalog) is read-only,
  non-executable, confirmed by full code read.
- `tests/test_phase2f*.py`: 2445/2445 passed twice, identical — the
  fourth independent confirmation of this figure in this program.

## What blocks full certification — three independent, sufficient reasons

1. Both demo accounts (`manager@`/`readonly@demo-ac-services.local`)
   remain `MANUAL_ROLE_CONFIRMATION_REQUIRED` — no evidence-backed
   canonical role mapping exists for either.
2. No PostgreSQL/Docker environment is available to execute or prove
   Migration 144's apply/rollback/reapply sequence.
3. **New this slice**: running the complete backend test suite (12,096
   tests, not just Phase-2F's 2445) for the first time in this program
   surfaced that `scripts/canonical_seed_final_l5_01.py::get_or_create_user()`
   has zero role-validation logic — a live, currently-unguarded path that
   could reintroduce invalid-role accounts.

A fourth, independent gap (not a blocker on its own but material to the
overall claim boundary): the mounted-route census is incomplete — 261 of
~1,186 auto-detected mutation routes remain unclassified beyond the 313
canonical set.

See `final-certification-report.md` for the full reasoning and
`final-status-rationale.md` for why this specific token was chosen over
the other 8 candidates.

## What this slice did

- Created and verified an isolated certification worktree (guard never
  fired interference).
- Reconfirmed the recovered baseline via `verify_2f37.py` (21/21 PASS).
- Ran the existing mutation-route inventory tool (1,186 routes
  auto-classified) and spot-checked ambiguous categories.
- Investigated the canonical role registry live (`ROLE_PERMISSIONS`),
  found and resolved two apparent alias-usage concerns (one read-only
  display catalog, one dead-but-harmless default value), and traced a
  third to an unresolved-but-non-blocking static-data question.
- Reconfirmed the demo-account investigation and wrote a formal manual
  decision request for both accounts.
- Re-audited Migration 144 statically (safe) and confirmed the
  PostgreSQL/Docker environment gate (blocked).
- Ran `tests/test_phase2f*.py` twice (2445/2445, identical) and the
  complete `tests/` suite once (12,096 collected, 12,030 passed, 45
  failed — all 45 classified, none hidden).
- Produced 65 documentation artifacts (see `artifact-manifest.csv`).

## What this slice did not do

Did not apply Migration 144 anywhere; did not assign a role to either
demo account; did not modify the seed script (flagged, not fixed — outside
this slice's allow-list); did not modify any UX branch or historical
artifact; did not begin Slice 2F-38's own certification claim beyond this
bounded, bounded-scope report; does not begin any further phase.
