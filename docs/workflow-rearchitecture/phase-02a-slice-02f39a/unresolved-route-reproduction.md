# Unresolved Route Reproduction

## Reproduced fresh, not assumed

`inventory_mutation_routes.py` re-run in this worktree (before any
change): **2,320 total mounted routes**, **1,186 total auto-detected
mutation-like route records**, **261 classifier-`UNVERIFIED`** — bit-for-
bit identical to Slice 2F-38's figures. This is expected (no application
route or guard code changed between 2F-38 and the start of this slice)
and is stated as a reproduced, re-derived fact, not a copied one.

## Precise terminology (per this slice's own instruction)

- **2,320** = mounted route **records** (method+path combinations the
  live FastAPI app actually serves), not "2,320 mutation routes."
- **1,186** = route records the auto-classifier's dependency-name
  heuristic flags as *potentially* mutation-capable (POST/PUT/PATCH/DELETE
  verbs plus some GETs with side-effecting names) — an upper-bound
  candidate set, not a proven mutation count.
- **313 → 321** (this slice) = **confirmed, evidence-backed** canonical
  tenant/provider mutations (8 added this slice from `app/engines/auth/router.py`,
  see `canonical-mutation-additions.csv`).
- **261 → 229** (this slice) = unresolved mutation-like candidates
  remaining after this slice classified all 32 of `auth.router`'s entries
  (see `final-route-classification.csv`). **229 remain genuinely
  unclassified** — not zero.

## What changed this slice

- `auth.router`: 32/32 classified (8 newly canonical, 2 platform-admin, 9
  public/callback, 13 self-service-broadened).
- 32 other modules (`field_ops.router` 28, `platform_commerce.router` 23,
  `pricing.router` 17, `security.router` 12, `quote_checklist.provider_router`
  11, `booking.router` 11, `enterprise_grid.router` 9,
  `appointment.router` 8, `marketing.router` 8, `rag.router` 8,
  `compliance.router` 7, `notification.router` 7, `settings_engine.router`
  7, `chat.router` 6, `data_science.router` 6, `inventory.router` 6,
  `admin_catalog.recommendation_router` 5, `payment.router` 5,
  `review.router` 5, `subscription.router` 5,
  `platform_commerce.billing_endpoint` 4, `dispatch.router` 4,
  `document.router` 4, `geo.router` 4, `quote_checklist.customer_router`
  3, `service_catalog.router` 3, `media.router` 3,
  `media.new_router` 3, `quote_checklist.admin_router` 2, and a small
  remainder — 229 routes total per the auto-classifier's own count
  (261 - 32) — were **not** individually source-inspected this slice.
  The per-module list above is drawn directly from the tool's own
  breakdown and sums to approximately, not precisely, 229; the exact
  229 figure is the tool's total, not a hand-summed approximation.

This is an honest, quantified partial-completion statement, not a claim
of full census closure.
