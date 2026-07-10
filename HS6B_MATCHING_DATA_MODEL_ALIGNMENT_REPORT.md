# HS6B — Matching Data Model Alignment Report

## 1. Bookability tables/fields previously read by matching
`_passes_full_eligibility_gate` read **5 different signals from 4
different tables**: `provider_visibility_statuses.is_bookable` (correct,
canonical) PLUS independently re-derived checks against
`provider_enabled_offerings.status`, `provider_team_members.status`,
`provider_availability_rules` (count), `tenant_package_assignments.status`,
`tenant_wallets.credit_balance`, and `security_deposits.status` — a
**second, parallel readiness calculation**.

## 2. Bookability tables/fields written by HS4B
`_evaluate_provider_bookability()` (`provider_portal/router.py`) writes
`provider_visibility_statuses.is_visible`/`is_bookable`/
`visibility_blockers`/`bookability_blockers`/`last_evaluated_at`,
computed from `tenants`, `tenant_billing.credit_balance`/
`security_deposit_paid`, `tenant_service_areas`, `provider_availability_rules`,
`tenant_services`+`tenant_service_types`+`tenant_service_brands`.

## 3. Area coverage model previously read by matching
`provider_enabled_offerings.supported_type_ids`/`supported_brand_ids` —
JSON array columns on a table unrelated to HS5B's work, keyed only by
`offering_id`, with no per-area (zipcode/city) scoping at all.

## 4. Area coverage model written by HS5B
`tenant_service_area_services` (extended in migration 121 with
`service_type_id`/`brand_id`), joined to `tenant_service_areas` for
per-zipcode/city scoping — the real, normalized, already-live-verified
(in HS5B) coverage model.

## 5. Mismatches found (both real, both confirmed via live testing)
- **Bookability mismatch**: a real dev-DB tenant had
  `provider_enabled_offerings.status = 'pending_approval'` (an
  unrelated admin-approval workflow field) — this would have **wrongly
  excluded** a tenant that HS4B's canonical `is_bookable` already said
  was `true`. Confirmed via direct `psql` query before the fix.
- **Coverage mismatch**: the JSON-array `supported_type_ids`/
  `supported_brand_ids` columns are completely disconnected from the
  `tenant_service_area_services` table this session's HS5B sprint built
  and wired up — configuring coverage correctly in Service Areas had
  **zero effect** on matching eligibility before this fix.

## 6. Files updated
- `app/engines/home_service_booking/matching_engine.py` —
  `_passes_full_eligibility_gate()` rewritten to read only the canonical
  bookability flag and the normalized coverage table; `select_best_provider()`
  now passes `zipcode` through so coverage can be checked per-area;
  `ELIGIBILITY_GATE_CODES` updated to match the new reality.
- `tests/test_provider_first_matching_and_price_choice.py` — updated
  `REQUIRED_ELIGIBILITY_CHECKS` and added a regression guard against the
  removed parallel-readiness tables reappearing.

## 7. Compatibility/fallback rules
**No legacy JSON-array fallback was implemented.** Per the ticket's own
guidance ("Do not silently keep two active competing sources"), and
since every real `tenant_service_area_services` row created this
session (HS5B + this fix's own live verification) already covers the
normalized case, a fallback was judged to reintroduce exactly the
inconsistency risk this sprint exists to remove. If a genuine legacy
tenant with only JSON-array coverage and zero normalized rows exists in
production, it would now be excluded from matching until an admin/
tenant configures normalized coverage — documented as a real migration
consideration in Remaining Blockers, not silently handled.

## 8. Deprecated model usage left
`provider_enabled_offerings.supported_type_ids`/`supported_brand_ids`
columns are no longer read by matching — `LEGACY_FALLBACK_ONLY` status
per the ticket's own labeling convention, though no fallback code path
actually reads them (see #7). `tenant_wallets`, `security_deposits`,
`tenant_package_assignments` are no longer read by matching at all
(their signals are folded into the canonical `is_bookable` flag, which
already accounts for usage credits and security deposit via
`tenant_billing`).

## Verdict
Both real data-model mismatches identified in HS6 are **fixed**: a
single canonical bookability source and a single canonical area-
coverage source, both live-verified to correctly include and exclude
candidates.
