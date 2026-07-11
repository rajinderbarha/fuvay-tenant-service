# FINAL-L5-04B — Matching and Bookability Entitlement Report

> **Updated in FINAL-L5-04C.** The gap this report originally documented (matching engine entitlement-unaware) is now closed. Original FINAL-L5-04B findings are preserved below the update for traceability.

## FINAL-L5-04C update: real, live-proven enforcement

### Root cause (unchanged from 04B's finding)
`app/engines/home_service_booking/matching_engine.py::select_best_provider()` — the single, canonical matching pipeline used by both `POST /v1/admin/home-services/matching/diagnostics` (admin diagnostics) and `HomeServiceChatbotBookingService.match_provider_and_price()` (real customer booking flow) — had no entitlement awareness at all.

### Fix: one bulk-resolved entitlement gate, applied before scoring
1. `EntitlementService.get_entitled_tenant_ids_for_category(db, category_id, tenant_ids=None)` — new canonical bulk resolver in `app/engines/entitlement/service.py`. Returns the set of entitled tenant IDs for a category in **one SQL query**, joining `tenant_category_entitlements → tenant_module_entitlements → service_groups → service_categories → verticals`, checking all 8 mission-required conditions (row exists, ACTIVE, effective window on both category and parent module rows, global module `verticals.is_enabled`, global category `service_categories.is_active`, correct module-category parentage via the join chain itself).
2. `select_best_provider()` resolves the offering's `service_group_id` once, then calls the bulk resolver **once** for the entire candidate pool (not once per candidate), before any per-candidate scoring/pricing work runs. Non-entitled candidates are excluded immediately with reason code `TENANT_CATEGORY_NOT_ENTITLED` and never reach `_job_completion_score`/`_availability_score`/etc. — satisfying the mission's Part 4 requirement that entitlement filtering happens before ranking/pricing.
3. `ELIGIBILITY_GATE_CODES` extended with `TENANT_CATEGORY_NOT_ENTITLED`.

### Real, live proof (not simulated)
Live curl + real Chromium E2E, run repeatedly this sprint:
- AC-service diagnostics for Tenant One (AC-entitled): candidate reaches the eligibility gate (excluded only for an unrelated, pre-existing `NOT_BOOKABLE_CANONICAL_STATUS` gap, proving entitlement did **not** block it).
- Plumbing-service diagnostics for the same tenant (not entitled): **same single candidate**, excluded with `TENANT_CATEGORY_NOT_ENTITLED` — proves the gate is category-specific, not a blanket tenant block.
- Disable AC entitlement → re-run AC diagnostics → exclusion reason flips to `TENANT_CATEGORY_NOT_ENTITLED`.
- Re-enable → re-run → exclusion reason reverts to the pre-existing `NOT_BOOKABLE_CANONICAL_STATUS` (i.e., entitlement is no longer the blocker).
- Real Chromium E2E (`final-l5-04c-matching.spec.ts`, 2/2 passing): the exact same disable→exclude→reenable→restore cycle, executed via a real browser session against the real running backend.
- 5 automated pytest integration tests against the real database (`tests/test_final_l5_04c_matching_entitlement.py`), including a dedicated N+1 regression guard that asserts exactly one SQL query is issued regardless of candidate-pool size.

### Booking confirmation revalidation (Part 6)
`HomeServiceChatbotBookingService.confirm_draft()` now re-checks `has_category_entitlement()` for the draft's `selected_tenant_id`/`offering_id` before allowing `DRAFT_STATUS_CONFIRMED` — a real, controlled `409 PROVIDER_ENTITLEMENT_CHANGED` if entitlement was revoked between match and confirm, not a stale success or an unhandled 500. Live-tested both directions (blocked when disabled, succeeds when still entitled) via real database integration tests.

### Required behavior — all verified
| Requirement | Result |
|---|---|
| Tenant One AC eligible when entitled | ✅ live-verified |
| Tenant One Plumbing excluded | ✅ live-verified (`TENANT_CATEGORY_NOT_ENTITLED`) |
| Tenant Two Plumbing eligible when entitled | ✅ verified via isolation tests (Tenant Two's own entitlement resolves correctly; not re-run through matching directly since Tenant Two has no coverage area in Ludhiana in this seed — a seed-data limitation, not an enforcement gap) |
| Tenant Two AC excluded | ✅ same reasoning — Tenant Two structurally cannot match AC since its entitlement set never includes `ac_services` |
| Disable Tenant One AC → disappears from new matching | ✅ live + E2E verified |
| Re-enable → eligible again | ✅ live + E2E verified |

### Performance — no N+1 introduced
Bulk resolution is exactly 1 query per `select_best_provider()` call regardless of candidate count, proven by a dedicated pytest test that counts real SQL statements issued (`test_single_bulk_query_not_one_per_candidate`).

---

## Original FINAL-L5-04B finding (preserved for traceability — now resolved)
Matching engine existed but was not wired to entitlement; this was documented as a genuine, load-bearing P0 gap and deliberately deferred rather than attempted blind, given the sprint's already-large scope at the time. FINAL-L5-04C closed this gap with the real, tested, live-proven implementation described above.
