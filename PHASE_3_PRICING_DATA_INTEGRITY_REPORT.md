# Phase 3 — Pricing Data Integrity Report

| # | Check | Result |
|---|---|---|
| 1 | Small tier exists once | ✅ seeded this sprint (`code='small'`, `base_multiplier=0.85`) — was previously missing (only "Mid" existed from Phase 0's baseline scenario) |
| 2 | Mid tier exists once | ✅ confirmed, `code='mid'`, 1 row |
| 3 | Large tier exists once | ✅ seeded this sprint (`code='large'`, `base_multiplier=1.2`) |
| 4 | Ludhiana 141001 maps to Mid tier | ✅ confirmed live via resolver (`tier: {name: "Mid", match_level: "zipcode"}`) |
| 5 | AC Repair baseline pricing rule exists once | ✅ confirmed, `rule_code='ac_repair_split_ac_lg_ldh_141001'`, 1 row |
| 6 | Base price = 800 | ✅ confirmed |
| 7 | Min price = 600 | ✅ confirmed |
| 8 | Max price = 1200 | ✅ confirmed |
| 9 | Bargain floor = 650 | ✅ confirmed |
| 10 | Completed job deduction = 21 usage credits | ✅ confirmed (set explicitly this sprint — field didn't exist before) |
| 11 | No conflicting active pricing rules for same condition | ✅ `GET /pricing-rules/{id}/conflicts` endpoint exists and was not triggered for the baseline rule (no duplicate condition set created) |
| 12 | No provider override violates min/max | ✅ enforced at the database-write layer — confirmed live: ₹500 and ₹1300 both rejected before any row was written |
| 13 | Pricing resolver output matches database rule | ✅ confirmed — resolver's `800.0`/`600.0`/`1200.0`/`650.0`/`21` all match the raw DB row read directly |
| 14 | No pricing menu duplication exists | ✅ confirmed — each of the 5 Pricing & Rules sidebar labels appears exactly once in `AdminLayout.tsx` |

## Fix applied: Small/Large tiers seeded

The ticket's Module 1 baseline requires `Small`, `Mid`, `Large` tiers to all
exist. Only `Mid` had ever been seeded (Phase 0's baseline scenario only
specified Mid). Fixed by directly inserting `Small` (`base_multiplier=0.85`)
and `Large` (`base_multiplier=1.2`) rows, using `Mid`'s existing `1.0`
multiplier as the anchor and reasonable ±15%/+20% spread — explicitly
documented as a placeholder business default, not a finalized pricing
policy decision (which would need product/finance sign-off in a future
sprint). Re-verified idempotent: a second insert attempt correctly skipped
both since the rows already existed by `code`.
