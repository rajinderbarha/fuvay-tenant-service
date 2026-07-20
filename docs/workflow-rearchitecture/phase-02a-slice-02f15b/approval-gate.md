# Slice 2F-15B Approval Gate

> **QUALIFIED BY SLICE 2F-15C.** Two items in this slice's final status require correction:
> (1) the provenance predicate used `changed_by_role == "customer"` without binding the acting
> user's identity to `Booking.customer_id` specifically — closed in 2F-15C at all 4 query sites;
> (2) the `179/220` coverage figure counted 3 customer-reachable routes (`create_booking`,
> `cancel_booking`, `request_reschedule`) as `TENANT_PROVIDER_MUTATION` while ALSO reporting them
> as a "customer self-service subset" — a contradiction. 2F-15C corrects the canonical figure to
> **175/216** by giving each route exactly one persona and physically removing the 4 non-tenant
> rows from the canonical CSV. See
> `docs/workflow-rearchitecture/phase-02a-slice-02f15c/documentation-corrections.md`. No
> authorization decision from this slice is reversed — both corrections are query-hardening and
> bookkeeping fixes, not changes to who can perform any action.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

- **SECURITY_CLOSED**: every Booking route remains classified (`final-booking-persona-matrix.csv`, single persona per route, no combined labels) and protected. Customer and tenant dependency branches are explicit and independently tested (`customer-dependency-semantics.md`, `TestCustomerDependencyIndependentOfTenantScope`). Wrong personas and cross-tenant actors remain denied (unchanged, re-verified via full regression). Runtime verification for `app.engines.booking.router` exits 0 (10/10 protected + 1 false-positive excluded), `field_ops.router` 28/28 exits 0, `field_ops.staff_router` 6/6 exits 0.
- **CUSTOMER_AUTHORITY_PROVENANCE_CLOSED**: customer origin is now PROVEN (not merely asserted) from the exact creation event — `from_status IS NULL AND changed_by_role == "customer"`, the one row written atomically at `create_booking` time and never rewritten (append-only table, no writer ever supersedes it). Later customer activity (cancellation, reschedule, notes) is proven, by executed test, unable to establish creation provenance — each writes to a different table entirely or to `BookingStatusHistory` with a non-null `from_status`. Provider-assisted Bookings require independent evidence, proven to exclude the current Booking at every one of the three authority-dependent decision points (relationship establishment, direct `create_job(booking_id=...)`, `convert_to_job`). Missing or ambiguous legacy provenance is proven, by executed test, to fail closed in every category examined (no history, NULL role, provider-only history) with zero partial persistence.
- **DOMAIN_INTEGRITY_CLOSED**: provenance checks occur before relationship use and conversion in every code path examined (source-position proof in `no-partial-persistence-proof.md`); invalid provenance produces no partial records (`db.add.assert_not_called()` on every rejection test); existing Booking state and conversion rules are unchanged (`Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` remain separate, confirmed untouched).
- **PRIVACY_CLOSED**: unrelated tenants cannot use later customer actions to manufacture authority (proven — later customer actions never satisfy the creation-event filter regardless of tenant). Missing-history records cannot affect unrelated customer history (each query is scoped to `tenant_id`+`customer_id`; a missing/ambiguous row for one customer has no bearing on any other customer's evaluation). Customer identity and relationship errors remain privacy-safe (single uniform `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` error across every denial category, unchanged from 2F-14F/G). Audit actor identities remain accurate (`BookingStatusHistory.changed_by`/`changed_by_role` always server-derived, append-only, never rewritten).
- **GLOBAL_COVERAGE_CLOSED**: one canonical tenant-facing numerator (179) and denominator (220), both CSVs recount identically (enforced by `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount`, updated this slice), runtime inventory agrees (`persona_breakdown` matches `final-booking-persona-matrix.csv` exactly). Customer routes (3, all subset of the 9 tenant-facing) and platform/internal routes (1) are counted SEPARATELY, never merged into the X/Y headline (`canonical-tenant-coverage-recount.md`).
- **PRODUCT_POLICY BLOCKED** for: recovery of missing-history legacy Bookings; tenant-local customer directory; verified invitation/consent workflow; new provenance columns; legacy-data remediation migration; Booking/ServiceBooking consolidation; database-level concurrency hardening (TOCTOU window in the recheck-based provenance pattern); frontend implementation. None of these are security gaps in the code as it exists today — all require a product decision this slice has no authority to make.

## Scope discipline confirmed

No provenance column, migration, customer directory, or invitation/OTP/consent workflow was created. No merge of `Booking`/`ServiceBooking` or `field_ops.Job`/`ServiceJob`. `PartsRequest` and `quote_checklist` untouched. No role, alias, or permission added. No frontend/UI work performed. `readonly@demo-ac-services.local` confirmed untouched. Migration 144 confirmed unapplied. No visual redesign. No second module was begun — this slice's ONLY code changes were the runtime tool's persona-map extension and the physical removal of the `booking_preflight` row from the canonical coverage CSV; every authorization/provenance mechanism this slice examined was already correctly implemented in Slices 2F-15/2F-15A and required no application-code changes, only proof.

## Coverage

**179 protected of 220** tenant-facing mutation routes (unchanged in value from 2F-15A; now backed by a single-persona-per-route classification and physical removal of the false-positive row — see `canonical-tenant-coverage-recount.md`). Separately: 3 protected customer-self-service Booking mutations (subset, not additional), 1 protected platform/internal Booking mutation, 1 false-positive Booking route excluded entirely.

## Regression

13/13 new tests passing. 2 pre-existing tests corrected to the canonical 220/179 figures (not weakened). Full broad partition sweep: **1726 passed, 9 skipped, 0 failed** (`regression-report.md`, `test-report.md`).

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-15B approval gate. No further router module is started. `field_ops.router` (28/28) and `field_ops.staff_router` (6/6) are preserved. All previously-approved Slice 2F-15/2F-15A authorization fixes are preserved and re-verified. Every item Slice 2F-15A left unapproved is now adjudicated: `BookingStatusHistory.changed_by_role` proves the creation actor specifically (in conjunction with `from_status IS NULL`, not alone); no later customer-authored history row can retroactively legitimize a provider-created Booking; `require_tenant_mutation_permission` correctly separates customer self-service from tenant mutation scope; and canonical coverage (179/220) excludes customer self-service and platform/internal routes from the tenant-facing denominator, with both figures now proven by executed test rather than asserted from source reading.
