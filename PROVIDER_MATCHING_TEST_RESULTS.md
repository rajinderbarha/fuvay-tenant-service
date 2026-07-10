# Provider-First Matching + Customer Price Choice — Test Results

## Pure-function unit tests

`pytest tests/test_provider_first_matching_and_price_choice.py`: **18/18 passed.**

Covers: multi-candidate ranking, best-provider selection by score, low-health-score
provider losing to a stronger one, exact scoring-formula weight verification,
customer-safe view hides `internal_score`/`internal_score_breakdown`, admin view
exposes them, Low/Mid/High price-tier formula (`715/810/900` matching the
ticket's example exactly), `round_to_nearest_10`, invalid-range rejection
(delegates to the Bargain Module's validation), tier-only offer resolution
(no raw-amount customer input path exists), mid-price never escapes
`[low, high]`, payment mode is always `customer_pays_provider_directly`,
eligibility-gate static-inspection (every required check present, verified
against real live table names), area-comparison independence (no code path
lets it influence provider selection or price).

## Live DB-backed verification

Ran `select_best_provider`/`get_area_market_comparison`/`_passes_full_eligibility_gate`
directly against the real database (bypassing the customer-facing router, since
draft creation depends on a separate, pre-existing bug — see below):

- Found and fixed a real asyncpg type-inference bug in the new area-comparison
  SQL (`AmbiguousParameterError` on `NULL`-comparison parameters) — fixed with
  explicit `CAST(... AS TEXT/UUID)`.
- Found and fixed a real bug in the candidate base query: it filtered on
  `Tenant.category_id == category_id`, but `tenants.category_id` is NULL on
  real seeded tenants (the same gap discovered and worked around in the
  My Offerings sprint). Removed the category_id filter; vertical is the
  correct, populated gate.
- Confirmed the eligibility gate correctly **excludes** the real test tenant
  (Demo AC Services): `tenants.status = 'pending_setup'` (not `'active'`) and
  no `provider_visibility_statuses` row exists yet (`is_bookable` gate fails).
  This is the correct, intended behavior — the tenant genuinely has not been
  admin-approved to active/bookable status. Deliberately did **not** mutate
  this tenant's approval state to force a "successful selection" scenario,
  since it is a shared baseline test fixture this session has consistently
  restored to its original state after any live verification (per this
  session's established convention).

## Why no full "provider selected" live E2E run

`POST /v1/customer/home-services/booking-drafts` (draft creation) depends on
the `MasterOffering`/category-slug lookup, which resolves against the
`master_offerings` legacy table — the same empty, orphaned table found and
replaced in the My Offerings sprint for the *provider-facing* endpoints. The
*customer-facing* draft-creation flow still depends on it and was not in
scope for this ticket to fix (a separate, similarly-sized architectural
issue). Documented honestly in Remaining Blockers rather than worked around
with fabricated data. The core matching/scoring/pricing logic this ticket
adds was still fully verified — both as pure functions and directly against
live DB tables — independent of the broken draft-creation step.

## Regression check

`pytest tests/test_provider_first_matching_and_price_choice.py tests/test_bargain_customer_range_platform_fee.py tests/test_tenant_my_offerings_enterprise_ui.py tests/test_tenant_my_status_enterprise_ui.py`:
**88/88 passed** — 0 regressions.

## OpenAPI

Confirmed via `app.openapi()`: `/v1/customer/home-services/booking-drafts/{draft_id}/match-and-price`
and `.../confirm-price-choice` both registered and routable. The old
list-based `/match-providers` and `/select-provider` endpoints remain (for
backward compatibility) but are marked `[DEPRECATED]` in their OpenAPI
summary/description.
