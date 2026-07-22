# Slice 2F-15B — Implementation Summary

## Scope
Adjudicate the 5 items 2F-15A left unapproved: (1) whether `BookingStatusHistory.changed_by_role` proves the creation actor specifically, (2) whether later customer activity can retroactively legitimize a provider-created Booking, (3) whether missing/ambiguous legacy provenance fails closed, (4) whether `require_tenant_mutation_permission` correctly separates customer self-service from tenant mutation scope, and (5) whether the 179/220 coverage figure double-counts or mis-scopes customer/platform routes.

## What this slice found
Investigating the EXISTING code (from Slices 2F-15/2F-15A) rather than writing new authorization logic, this slice determined that **the code was already correct on all 5 points** — the gap was that these properties were asserted from source-reading, not proven by executed tests, and the coverage CSV still carried `booking_preflight` as a labeled-but-uncounted row rather than a physically excluded one. This slice closes both gaps:

1. **Exact creation-event predicate proven.** `from_status IS NULL` is written exactly once per Booking, only by `create_booking`, atomically with the Booking's own persistence. Every other `_write_history` call site reads a real prior status. Classification: `EXACT_CREATION_EVENT_BY_CUSTOMER` (see `exact-customer-origination-predicate.md`).
2. **Later customer activity cannot establish provenance — proven by test.** Cancellation writes `from_status = b.status` (never None); reschedule-request doesn't touch `BookingStatusHistory` at all; notes go to a different table entirely (see `later-customer-activity-test-matrix.csv`).
3. **Missing/ambiguous history fails closed — proven by test.** No history, NULL `changed_by_role`, and provider-confirmation-only history all fall through to the independent-evidence check and raise `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` with zero persistence (see `missing-history-legacy-behavior.md`).
4. **Customer dependency independence — proven by test.** `require_tenant_mutation_permission` denies only `access_scope in {"customer_support_limited"}`; customer accounts never carry `access_scope`, so the customer branch degenerates to a plain permission check. Proven directly, including an adversarial forged-scope case (still correctly denied — fail-closed) (see `customer-dependency-semantics.md`).
5. **Coverage reclassified with single-persona-per-route labels and `booking_preflight` physically removed.** Final canonical figure unchanged in value (179/220) but now backed by `final-booking-persona-matrix.csv` (one persona per route, no combined labels) and separate customer-self-service (3) / platform-internal (1) / false-positive (1, excluded) counts (see `canonical-tenant-coverage-recount.md`).

## Code changes
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py`: added `BOOKING_ROUTE_PERSONA` map and `BOOKING_DUAL_CUSTOMER_SELF_SERVICE_ROUTES`, plus a persona-breakdown report and documentation-vs-code drift check for `--verify-module app.engines.booking.router`.
- `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`: `booking_preflight` row physically removed (was previously left in with a distinct guard status).
- No application/service-layer code changes were required — all 5 adjudicated items were already correctly implemented in Slices 2F-15/2F-15A; this slice's contribution is proof (new tests) and coverage-bookkeeping precision.

## Test results
- New file `tests/test_phase2f15b_booking_creation_provenance_and_customer_dependency.py`: 13/13 passing.
- 2 pre-existing tests (`test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount`) updated to the corrected canonical figures (220/179) — not weakened, corrected.
- Full regression sweep: **1726 passed, 9 skipped, 0 failed** (up from 1713 at the 2F-15A gate: +13 new).
- Runtime verification: `booking.router` 0 unverified (exit 0) with persona breakdown `{TENANT_PROVIDER_MUTATION: 9, PLATFORM_INTERNAL_MUTATION: 1, FALSE_POSITIVE_NON_MUTATION: 1}`; `field_ops.router` 28/28 (exit 0); `field_ops.staff_router` 6/6 (exit 0).

## Final status
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` — see `approval-gate.md`.
