# Slice 2F-38 Verification Report

## Existing verifier (`verify_2f37.py`), re-run in this worktree

21/21 PASS, 21/21 selftest "fires when violated" — see
`recovered-baseline-verification.md`, `verifier-negative-fixture-report.md`.

## Manual/documented findings this slice (not covered by an automated verifier)

| Finding | Result |
|---|---|
| Exactly 10 canonical roles executable | CONFIRMED (`canonical-role-certification.md`) |
| No alias role is assignable through any executable path | CONFIRMED for the 2 paths investigated (`roles_permissions` display catalog, `admin_service.create_user` default) |
| Both demo accounts' role status | CONFIRMED unchanged: `MANUAL_ROLE_CONFIRMATION_REQUIRED` |
| Migration 144 static safety | CONFIRMED (fail-closed, no data mutation) |
| Migration 144 runtime safety | **NOT PROVEN** — no PostgreSQL |
| Mounted route census completeness | **NOT COMPLETE** — 261/2320 routes remain auto-classifier-UNVERIFIED |
| Full Phase-2F regression | 2445/2445 twice |
| Full backend regression | see `full-backend-regression-report.md` |

## Combined verdict

The mutation-authorization-specific claim (313/313, the canonical set this
whole program built) is well-supported by both the automated verifier and
this slice's own independent re-derivation. The *application-wide* claim
this slice was asked to adjudicate is **not** supportable: two
independent hard blockers (role data, migration environment) plus one
newly-quantified scope gap (261 unclassified mounted routes) all point the
same direction. See `final-certification-report.md` for the reasoned
final status.
