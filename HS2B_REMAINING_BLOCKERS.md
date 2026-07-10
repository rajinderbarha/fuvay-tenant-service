# HS2B — Remaining Blockers

1. **Cards-first visual redesign incomplete** — service groups/services
   still render as a compact row-list, not the ticket's card/accordion
   layout with per-card setup-status badges. Health cards (the
   summary-level cards-first requirement) are done; the main content
   area is not. See `HS2B_CARDS_FIRST_UI_REPORT.md`.
2. **Baseline seed data has real naming divergence from the ticket** —
   5 of 9 ticket-required groups have near-duplicate existing groups
   under different names (e.g. "AC & HVAC" vs "AC & Cooling"). No
   records were auto-created this sprint to avoid creating true
   duplicates; this needs an explicit content decision from the catalog
   owner (rename existing groups vs. create new ones), not an automated
   fix. 4 groups (Geyser, Water Purifier, Appliances, Maid/Domestic
   Help) are genuinely absent with no duplicate risk and are a safe,
   low-risk follow-up.
3. **Service Group model has no separate customer_visible/
   provider_selectable flags** — only `status`. The ticket's "inactive
   group cannot be customer visible/provider selectable" validation
   rules aren't independently enforceable without a schema change.
4. **Permission split incomplete** — `catalog:services:write` covers
   create/update/delete together; there's no way to grant "can edit but
   not delete" today, unlike the ticket's 5 separate permission
   verbs.
5. **Permission wiring not live-verified** — implemented and statically
   tested, but no restricted-permission test user login was performed
   to confirm real runtime 403 behavior.
6. **Delete-safety gaps**: Option/Add-on delete safety not verified
   (endpoint not located this sprint); no entity's hard-delete checks
   direct booking/job history references (only pricing-rule and
   tenant-enablement references are checked) — a type/brand used only
   in a past completed booking could still be hard-deleted today.
7. **Provider Setup Rules tab uses 2 proxy fields** — no dedicated
   `requires_technician`/`photo_upload_allowed` columns exist on
   `MasterService`; the tab reuses `requires_schedule`/
   `requires_issue_type` as best-effort stand-ins.
8. **`npm run build`/`lint`/`test` not run** — established constraint,
   `tsc --noEmit` used as gate.

## What is solid and newly fixed this sprint
- Service Group CRUD is real, complete, and now reachable from the
  catalog console (was already built, just not linked).
- A real delete-safety bug (`hard_delete_service_type` had no usage
  check at all) was found and fixed.
- Provider Setup Rules tab is real, data-driven, and provably contains
  no pricing fields (regression-tested).
- Permission-aware UI is implemented against real, existing permission
  constants (not the ticket's assumed, non-existent namespace).
- The core HS2 scope guarantee (no pricing forms, no Low/Mid/High
  calculator, no Zones/Tiers tab) was re-verified and remains intact,
  with an explicit new regression test added on top of the original one.
- 0 regressions introduced; TypeScript clean; 40/40 HS2-scoped tests
  passing.
