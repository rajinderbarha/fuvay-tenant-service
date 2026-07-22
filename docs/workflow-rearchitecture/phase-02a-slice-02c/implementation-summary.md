# Phase 2A Slice 2C — Implementation Summary

## Outcome in one sentence
Both confirmed invalid-role accounts were investigated thoroughly but **remain unremediated** — the evidence for one is name-similarity only (explicitly disallowed as sufficient), and the other has no canonical role equivalent at all. Per the brief's own explicit allowance ("if either mapping remains ambiguous, leave that account unchanged and report the blocker"), zero data was mutated. What this slice *did* deliver is real: an idempotent, safety-guarded remediation tool ready to execute once a human approves a mapping, a database-level integrity guard (migration) that is proven to correctly refuse to apply while these 2 accounts remain unresolved, a full role-write-path audit, and a conclusive disposition for the Slice 2B-flagged intelligence KB field.

## Workstream 1 — Account investigation (deepened past Slice 2B)
New evidence gathered this slice via further live, read-only queries:
- `manager@demo-ac-services.local` (`tenant_manager`): **zero logins, zero sessions, zero audit records of any kind, no team-member profile, no assigned jobs.** The only "evidence" of intended role is the email local-part and `full_name` field ("Tenant Manager") — both are name-similarity, which the rules explicitly forbid using as sufficient basis for automatic remapping.
- `readonly@demo-ac-services.local` (`tenant_readonly`): **7 successful logins across 2026-07-11 through 2026-07-13, with 7 currently unrevoked sessions** — someone has been actively trying to use this account. But zero non-login audit actions were ever recorded (consistent with hitting a permission wall every time, since the role grants nothing), no team-member profile, no assigned jobs. There is no canonical role matching "tenant-side read-only user" at all (confirmed again this slice) — so even with strong usage evidence, there is no safe target to map to.

Full detail with verification levels in `affected-account-investigation.md`.

## Workstream 2 — Remediation decision
Both accounts: **MANUAL_ROLE_CONFIRMATION_REQUIRED.** Neither qualifies for `SAFE_AUTOMATIC_REMAP` under the brief's evidentiary bar. See `remediation-decision-register.md` for the full reasoning per account.

## Workstream 3 — Remediation tool (built, dry-run tested, not applied)
`scripts/workflow_rearchitecture/remediate_invalid_roles.py` — dry-run by default, requires both `--apply` and `--confirm` to mutate, validates every target role against the canonical 10, refuses platform-role-to-tenant-account combinations, refuses to run in apply mode if any invalid account isn't covered by `--mapping`, wraps changes in a transaction, writes one `auth_audit_logs` row per change. **Exercised live against the real database in dry-run and guard-rejection modes only** (verified: rejects non-canonical roles, rejects incomplete mappings, rejects platform-role-on-tenant-account, rejects `--apply` without `--confirm`) — never run with `--apply --confirm` against a real mapping, since no mapping was approved. See `remediation-dry-run-report.md` and `remediation-apply-report.md` (the latter explicitly states no application occurred).

## Workstream 5 — Database integrity guard (built and proven)
Migration `144_users_role_canonical_check.py` adds a CHECK constraint restricting `users.role` to the 10 canonical values. **Actually run against the live database this slice** (`alembic upgrade head`) — it correctly detected both invalid accounts, printed a clear, actionable error naming them, and aborted without applying any schema change (confirmed via `alembic current` showing revision unchanged at 143, and a live role-distribution query showing the database byte-for-byte identical before and after the attempt). See `database-integrity-guard.md`.

## Workstream 4 — Role-write-path audit
All backend paths that can write `User.role` were traced. Two paths were already correctly validated pre-existing (`auth/service.py`'s `change_platform_role`/`invite_platform_user`, gated by `VALID_PLATFORM_ROLES`) or fixed in Slice 2 (`tenant_engine/admin_service.py`, gated by `VALID_TENANT_ROLES`). The only unvalidated write path found was the seed script (`scripts/canonical_seed_final_l5_01.py`), which bypasses all API-level validation by design (it's a raw-SQL/ORM seeding tool, not an API) — this is the confirmed, sole source of both invalid accounts. Full detail in `role-write-path-audit.csv`.

## Workstream 8 — Intelligence KB `allowed_roles_json`
**Disposition: DISPLAY_ONLY.** Exhaustively re-searched the entire `app/` tree (not just `kb_service.py`) — confirmed 4 total references, all either the model definition, serialization, or write-path; zero enforcement anywhere. See `intelligence-kb-role-field-decision.md`.

## Non-negotiable rules compliance
No data mutated. No role mapped from name similarity alone. No platform role granted to either account. No booking/job pipeline touched. No UI redesign. All Slice 1/2/2B tests still pass (260/260 combined this slice, up from 253 with 7 new tests added).
