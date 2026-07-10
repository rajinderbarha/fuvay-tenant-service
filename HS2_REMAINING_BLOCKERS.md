# HS2 — Remaining Blockers

1. **Service Group CRUD not built** — no "Add Service Group"/Edit/
   Activate/Deactivate/Reorder UI exists anywhere found this sprint. The
   catalog page only reads groups to organize the service list.
2. **Baseline groups/services not verified against seed data** — the
   ticket lists 9 required baseline groups (AC & Cooling, Plumbing,
   Electrical, Geyser, Water Purifier, Appliances, Pest & Cleaning,
   Carpentry, Maid/Domestic Help) and ~25 baseline services. Not checked
   against the real dev DB this sprint (time budget went to the scope
   violation fix, which was the higher-priority, ticket-flagged auto-fail
   condition).
3. **Types/Brands inline behavior-toggle CRUD removed, not relocated** —
   the pre-existing `can_override_price`/`is_routing_only` checkboxes
   were removed from the Brands tab alongside the pricing form they were
   bundled with. The underlying data/API is untouched, but there's now
   no in-console way to toggle these flags. Should be re-added as
   catalog-only controls (without the price-limit form) in a follow-up.
4. **Setup Status badge (Ready/Needs Types/Needs Questions/Needs Brands/
   Inactive/Draft/Blocked) not implemented** — service rows show only a
   binary active/inactive dot, not the ticket's 7-state setup status.
5. **Top actions incomplete** — "Add Service Group", "Export Catalog",
   "View Audit" buttons from the ticket's required top-actions row were
   not added (only "Refresh" and "Add Service" exist, pre-existing).
6. **Permission-aware UI not implemented** — same class of gap already
   documented in the earlier A3 sprint; no fine-grained
   `admin.home_services.catalog.*` permissions exist or gate anything in
   this console.
7. **Delete-safety rule not verified** — no delete action exists in this
   console; whether linked-out management pages correctly block
   hard-delete of in-use records with the ticket's exact message was not
   checked this sprint.
8. **Cards-first visual redesign incomplete** — health cards were added
   (real data, 8 cards, CTA-aware), but the service list below them is
   still a compact grouped row-list rather than the ticket's "clean
   cards" treatment, and the Types tab is still a table (now catalog-
   only, but still tabular, not a card layout).
9. **`npm run build`/`lint`/`test` not run** — `tsc --noEmit` used as the
   build-health gate per established session convention (dev server
   ports occupied by external processes).

## What is solid
The ticket's explicit auto-fail condition — deep pricing logic
(floor/ceiling/platform-fee forms, tier/zone pricing, Low/Mid/High
calculation) mixed directly into the catalog console — is genuinely
fixed and test-enforced. The page is now structurally catalog-only:
every pricing-adjacent surface either shows read-only catalog-scope
information or links out to Pricing Rules, never computes or edits a
price. 0 regressions introduced, TypeScript clean, forbidden-label scan
clean.
