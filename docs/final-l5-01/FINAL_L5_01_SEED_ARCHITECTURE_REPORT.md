# FINAL-L5-01 — Seed Architecture Report

## Actual structure used (not the mission's suggested `seeds/canonical/...` tree)
This repo already had an established `scripts/seed_*.py` convention (15 existing scripts) predating this sprint. Rather than introduce a parallel `seeds/` directory tree (which would fragment seed logic across two conventions), this sprint added two new scripts following the existing convention:

- `scripts/canonical_seed_final_l5_01.py` — the canonical deterministic seed (Part 7 of this mission)
- `scripts/reset_final_l5_01.py` — the paired destructive reset (Part 5 of this mission)

## Relationship to existing seed scripts
The canonical seed **reuses** rather than duplicates prior sprints' catalog seeding (`seed_master_services.py`, `seed_brands.py`, `seed_ac_repair_baseline_mappings.py`, `seed_issue_types.py`) — it verifies AC Repair / Split AC / Window AC / LG / "AC Not Cooling" exist via `SELECT` and fails loudly with an instructive message if they don't, rather than re-implementing catalog creation. This avoids the "do not duplicate the same seed logic across multiple scripts" rule.

It does **not** reuse `scripts/seed_phase0_baseline.py` (single flat-price rule, `pending_setup` tenant status) or `scripts/seed_demo_users.py` (different email convention, no tenant-owner/manager/readonly separation) — both are superseded by this sprint's canonical seed for the purposes of Level-5 testing, since neither matches the mission's exact entity spec (active tenant, range-based pricing, distinct Split/Window AC rules, 5-state job lifecycle, ledger deduction). They are not deleted (see cleanup report) since they may still serve their original, narrower purpose for other flows.

## Fixture separation
No automated-test fixtures were touched or created by this sprint — backend pytest fixtures operate independently of the persisted dev database (confirmed via `pytest --collect-only` succeeding both before and after every reset performed this sprint, with 8,915 tests collecting cleanly regardless of dev-DB state). E2E-specific fixture separation (a dedicated `seeds/e2e/` path) was not built this sprint — flagged as a gap in remaining blockers, since Playwright E2E specs currently rely on whatever is in the dev database rather than a dedicated E2E seed profile.

## Why not the full `seeds/canonical/{platform_users,tenant,catalog,...}` directory split
Splitting the ~400-line canonical seed script into 9 separate files (per mission's suggested tree) was judged to add indirection without benefit at this repo's current seed-script scale (16 total scripts) — the existing flat `scripts/` convention with descriptive filenames already provides equivalent discoverability. This is a deliberate scope decision, not an oversight; revisit if the seed script grows significantly larger.
