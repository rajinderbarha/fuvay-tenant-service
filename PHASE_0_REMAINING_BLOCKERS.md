# Phase 0 — Remaining Blockers

None of these are hard-gate failures. All hard gates in the ticket passed
live verification. These are honest gaps to carry into subsequent
module-by-module certification phases.

1. **No live browser smoke was performed.** All 31 manual-smoke steps were
   reduced to API/DB-level checks. Per the ticket's own rule, this alone
   caps the final recommendation at `PARTIAL_READY_WITH_BASELINE_BLOCKERS`.

2. **`npm run serviceos:reset-dev-data` does not exist** — there is no root
   `package.json` in this repo (it's a Python backend + separate
   `frontend/super-admin` Next.js app with its own `package.json`). The
   backend equivalent (`python scripts/serviceos_reset_dev_data.py
   --confirm`) is the real, working command and is documented as such.

3. **Role taxonomy gap carries forward** (same finding as Phase 1): the
   ticket's `platform_admin`/`finance_admin`/`operations_admin`/
   `support_admin`/`compliance_officer` roles don't exist in code. Section
   5A's role-specific seed accounts were not created for this reason.

4. **`allow_job_completion_when_usage_credit_insufficient` setting doesn't
   exist** — not a Home Services baseline blocker (job completion isn't
   certified until a later phase per this ticket's own scope boundary), but
   flagged so it isn't silently assumed to be `false` by default in a future
   phase.

5. **`customer_credit_ledger`'s 6 pre-existing rows were not cleaned** — the
   table has no `tenant_id` column to scope the delete by, and the script
   correctly refused to guess a different join path rather than risk
   deleting unrelated data. These rows predate this session's tenant and are
   not tied to the new Demo AC Services tenant, so they don't pollute the
   Phase 0 baseline, but they're not "clean" in the strictest sense either.

6. **No admin-level Checklist system exists** (same finding as Phase 2) —
   the ticket's "Checklist: Technician diagnosis note, Before/after service
   photo, ..." baseline items were not seeded because there's no
   `master_service`-linked checklist table to seed them into; only a
   tenant-scoped runtime checklist system exists.

7. **Master service name mismatches vs the ticket's exact list** — e.g. the
   real seed has "AC Maintenance / Servicing" rather than "AC
   Uninstallation", and no "Switch Repair" exists (closest is "Electrical
   Fault Fix" / "Circuit Breaker & Fuse"). Catalog structure and the
   critical AC Repair chain are fully correct; only these peripheral naming
   differences exist. Documented, not changed (renaming existing production
   catalog entries is a data-integrity risk better handled in the Phase 2
   catalog module, not a Phase 0 cleanup task).

8. **Duplicate-concept issue-type row** — `ac_not_cooling` (correctly mapped
   to AC Repair) and a separate, differently-coded `not_cooling` row (from
   an unrelated seed script, unmapped) both exist. Flagged in Phase 2, not
   worsened here, not yet reconciled.
