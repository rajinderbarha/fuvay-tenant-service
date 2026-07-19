# Known Limitations

1. **Mode B throughout** — no `npm install`, `tsc`, `vitest`, or
   `next build` executed. All source is unverified by a real compiler/test
   run this phase (matches UX-01/UX-02 precedent).
2. **Not wired into production** — `UX03_NAV_GROUPS`, the new patterns, and
   fixtures exist as source but `lib/nav-config.ts` and production
   `app/(tenant)/**` pages were not modified to consume them. Swapping
   production pages over to the new patterns is a product decision (see
   product-decisions-required.md), same precedent as UX-02's super-admin
   nav.
3. **25 of 25 required showcase topics covered, but not every state
   combination** (light/dark/desktop/tablet/mobile/loading/empty/error/
   restricted/read-only/long-text) per example — breadth was prioritized
   over exhaustive per-example state coverage, per the task's own
   pragmatism instruction.
4. **Route audit is a naming/config cross-reference, not a full manual
   per-file read-through** of all 84 existing tenant-portal pages (that
   depth of read was infeasible in this session) — see
   orphaned-and-broken-route-report.md's stated method.
5. **N01 media-integrity backlog** — referenced per the task brief but not
   independently re-verified against the current repo state this phase;
   the Media showcase note repeats the existing memory-index reference.
6. **Multi-service setup wizard, dedicated Quote/Checklist showcase** not
   separately built — the generic `SetupWizard` pattern demonstrates the
   mechanism but a dedicated multi-service instance was deferred (see
   deferred-items.md).
7. **Geo/service-area mutation readiness** is asserted from the task
   brief's "frozen slice" description, not independently re-derived from
   `app/engines/geo/` this phase.
