# Phase 3 — Pricing & Rules Bug Fix Report

## Bugs found and fixed

1. **`completed_job_deduction_credits` never existed as a schema field.**
   The Phase 0 baseline requirement ("Completed Job Deduction = 21 usage
   credits") had never actually been implemented — confirmed absent from
   `service_pricing_rules` via research before this sprint. Fixed via
   migration 111 (new column, `Integer`, default 0, `>= 0` validated on
   create/update), wired into the pricing resolver response, and the AC
   Repair baseline rule explicitly set to `21`.

2. **Migration index name collision.** The first attempt at migration 111
   used `ix_br_status` for a new `bargain_rules` index — collided with a
   pre-existing `ix_br_status` index on the unrelated `brand_requests`
   table (same `br` abbreviation, different table). Alembic failed with
   `DuplicateTableError`. Fixed by renaming to `ix_bargain_rules_status`
   (and the two sibling indexes similarly) — verified no other name
   collisions before re-running.

3. **Bargain floor could be set below the pricing rule's own min_price.**
   The pre-existing validation only checked `bargain_floor > base_price`;
   a bargain floor below `min_price` (which shouldn't be possible — the
   floor is a price ceiling for negotiation, not something below the
   platform's own minimum) was silently allowed. Added
   `bargain_floor < min_price` validation on both create and update.

4. **Small/Large pricing tiers were never seeded** — the ticket's Module 1
   hard gate ("Small/Mid/Large tiers exist") was failing; only Mid existed.
   Fixed by seeding both with documented placeholder multipliers (see
   `PHASE_3_PRICING_DATA_INTEGRITY_REPORT.md`).

## Bugs found, not fixed (documented as blockers)

None — every bug found this sprint that affected a stated hard gate was
fixed and re-verified live before moving on.

## Non-bugs investigated and ruled out

- Cross-vertical "Pricing Tiers" module injection for Coaching/Real
  Estate/Beauty/Restaurant/Product Marketplace/Professional Services (each
  shows a "Pricing Tiers" catalog module in their per-vertical sidebar
  section). Initially looked like a possible duplicate-menu violation, but
  the ticket's explicit hard gate is scoped to Home Services specifically
  ("No pricing pages appear under Home Services"), which is confirmed
  correct. This is pre-existing Phase 2 behavior for other verticals, not
  a Phase 3 regression — documented, not changed, since "fix incorrect
  vertical/category mapping" for verticals outside Home Services is out of
  this phase's scope.
