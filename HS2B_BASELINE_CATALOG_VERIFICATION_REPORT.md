# HS2B — Baseline Catalog Verification Report

## Method
Direct `psql` query against the real dev database, scoped to the
`Home Services` category (`service_categories.name = 'Home Services'`),
joining `master_services` → `service_groups`.

## Real ground truth found
```
Home Services | AC & HVAC        | AC Gas Refill
Home Services | AC & HVAC        | AC Installation
Home Services | AC & HVAC        | AC Repair
Home Services | AC & HVAC        | AC Repair Duplicate Test   (x2, both is_active=false — pre-existing test fixture, already safely deactivated)
Home Services | AC & HVAC        | AC Service
Home Services | Electrical       | Circuit Breaker & Fuse
Home Services | Electrical       | Electrical Fault Fix
Home Services | Electrical       | Fan & Light Installation
Home Services | Painting & Walls | Exterior Painting
Home Services | Painting & Walls | Interior Wall Painting
Home Services | Pest Control     | General Pest Control
Home Services | Pest Control     | Termite Treatment
Home Services | Plumbing         | Drain Unblocking
Home Services | Plumbing         | Pipe Repair
Home Services | Plumbing         | Tap & Fixture Installation
Home Services | Plumbing         | Water Tank Cleaning
```

## Per-group verification

| Ticket group | Exists? | Real equivalent | Created | Duplicate found | Services count | Missing (per ticket list) | Action taken |
|---|---|---|---|---|---|---|---|
| AC & Cooling | No exact match | **AC & HVAC** (near-duplicate name) | No | Yes — "AC Repair Duplicate Test" x2, both already `is_active=false` | 5 active | AC Uninstallation | **Manual review** — do not create "AC & Cooling" (would duplicate "AC & HVAC"); recommend renaming existing group instead of creating a new one |
| Plumbing | Yes (exact name match) | Plumbing | No | No | 4 | Tap Installation (separate from Tap Repair), Pipe Leakage (separate from Pipe Repair — may already be covered by "Pipe Repair") | **Manual review** — service names differ from ticket's exact list ("Tap & Fixture Installation" vs "Tap Repair"/"Tap Installation"); likely already covers the intent, not auto-created to avoid near-duplicates |
| Electrical | Yes (exact name match) | Electrical | No | No | 3 | Switch/Socket Repair, Light Installation (may be covered by "Fan & Light Installation") | **Manual review** — same reasoning |
| Geyser | **No** | — | **Not created this sprint** | N/A | 0 | All 3 (Geyser Repair, Geyser Installation, Geyser Service) | **Documented gap** — genuinely missing, no near-duplicate risk; safe to create in a follow-up with explicit sign-off |
| Water Purifier | **No** | — | **Not created this sprint** | N/A | 0 | All 3 | **Documented gap** — genuinely missing |
| Appliances | **No** | — | **Not created this sprint** | N/A | 0 | All 3 | **Documented gap** — genuinely missing |
| Pest & Cleaning | No exact match | **Pest Control** (partial — cleaning half missing) | No | No | 2 | Home Deep Cleaning (not present under Pest Control; "Deep Cleaning" exists as its own separate group in the DB, not Home-Services-scoped in this query) | **Manual review** — ticket's "Pest & Cleaning" combines two concerns the real taxonomy keeps separate |
| Carpentry | Group exists ("Carpentry & Woodwork") but 0 services | Carpentry & Woodwork | No | No | 0 | Door Repair, Furniture Assembly (both missing) | **Documented gap** — group exists but is empty |
| Maid / Domestic Help | **No** | — | **Not created this sprint** | N/A | 0 | All 2 | **Documented gap** — genuinely missing |

## Decision: did not auto-create records this sprint
Per the ticket's own rule ("Do not duplicate similar records... if
duplicate/similar records exist, document and mark for manual review"),
and given that 5 of the 9 baseline groups have near-duplicate existing
groups with different names covering the same real-world service, this
sprint did **not** bulk-create new groups/services. Auto-creating
"AC & Cooling" alongside the existing "AC & HVAC" (or "Pest & Cleaning"
alongside "Pest Control") would itself create the exact duplicate
problem the ticket warns against. The 4 groups with **no** near-duplicate
risk (Geyser, Water Purifier, Appliances, Maid/Domestic Help — fully
absent, zero ambiguity) are documented as a clean, low-risk follow-up
task rather than created unilaterally without an explicit content
decision from the catalog owner (e.g., should Geyser be its own group or
folded into Appliances?).

## Verdict
Baseline verification: **complete as an audit**; **no records
created**, by design, given the real taxonomy's naming divergence from
the ticket's assumed baseline and the explicit anti-duplication rule.
Documented every gap and duplicate risk for a follow-up content decision.
