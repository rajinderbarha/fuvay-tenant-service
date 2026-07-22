# UX-08 Deferred Items

Status: FRESH THIS PASS (a straightforward honest listing).

## Deferred by explicit brief instruction (not a time/scope failure)

- **All pixel-width/responsive certification** — see doc 08. Deferred
  because a design replacement is planned; not a gap in this pass's
  diligence.
- **DB re-verification of the cross-app workflow chain** — see doc 05.
  Attempted for real this pass (checked `psql`, `psycopg2`, `asyncpg`,
  Docker, and a raw TCP probe of port 5432 — all unavailable/unreachable);
  genuinely `ENVIRONMENT_BLOCKED`, not skipped by choice.

## Deferred due to time/scope prioritization (honestly abbreviated, not fabricated)

- **Full mock/fixture census across all 4 apps** (nominal Workstream 16) —
  UX-07 already explicitly deferred this
  (`mock-fixture-census.csv`: "not_attempted_this_round"). This pass did
  not re-attempt a full census either; the registry in doc 06 consolidates
  the specific MOCK_DESIGN_ONLY items already known from UX-05's own
  adapter-contract audit, but a fresh, exhaustive census across
  super-admin/tenant-portal/staff-app/customer-app was not performed.
- **`next build` (production build)** for super-admin and tenant-portal —
  not run this pass (see doc 03). Typecheck/test signal was prioritized
  given time constraints; a full production build, especially for
  tenant-portal with its known React-version-mismatch defect
  (TICKET-UX08-001), would likely surface (not newly create) build-time
  duplicate-instance issues. Marked `NOT_EXECUTED_IN_UX08` in the release
  baseline matrix (doc 10), not assumed passing.
- **`tsc --noEmit` for super-admin and tenant-portal specifically as a
  standalone step** — both apps' `package.json` wire typechecking into
  `next build` rather than a standalone `typecheck` script; since `next
  build` itself was not run (above), no standalone typecheck signal was
  captured for these two apps this pass. Customer-app and staff-app (which
  do have standalone `tsc --noEmit`, run via React Native/Expo, not
  Next.js) WERE fully typechecked this pass (see doc 03).
- **Full re-audit of super-admin (195 route dirs) and tenant-portal (162
  route dirs) route dispositions** — not re-derived from scratch; the
  existing UX-02/UX-03 route-audit CSVs were cited instead (see doc 04).
  These CSVs are from earlier UX rounds and were not independently
  re-verified row-by-row this pass.
- **Full re-audit of staff-app's 28 screens** — same treatment; UX-05's own
  `existing-screen-route-audit.csv` cited, not re-verified this pass beyond
  the fresh typecheck/test run (doc 03).
- **Super-admin's live view of the Round 3 cross-app job/tenant** — UX-07
  Round 1 already noted no super_admin credential was available; not
  re-attempted this pass (moot anyway given the DB/backend was unreachable
  — see above).
- **Tenant onboarding, catalog/pricing continuity beyond the single
  `offering_type_id` defect already documented, and error/recovery-state
  workflows** — out of scope for this pass; inherited gaps from UX-07, not
  newly discovered or newly deferred here.

## Explicitly not deferred — done for real this pass

- Ancestry verification (doc 01) — full, not abbreviated.
- UX program history (doc 02) — full synthesis of all 7 prior phases'
  actual final statuses, including one genuine gap found (UX-03 has no
  canonical status token — documented honestly, not invented).
- Test/typecheck reconciliation for all 4 apps' jest/vitest suites (doc 03)
  — full, fresh, from-scratch installs, real numbers, including a real new
  defect found (TICKET-UX08-001).
- Customer-app's full route inventory (doc 04) — full, fresh, all 19 routes
  individually dispositioned from a full read of both navigation files.
- Redesign functional-contract handoff (doc 07) — full, fresh spec
  document.
