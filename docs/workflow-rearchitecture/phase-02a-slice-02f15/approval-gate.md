# Slice 2F-15 Approval Gate

> **SUPERSEDED BY SLICE 2F-15A.** This slice's `SECURITY_CLOSED`, `CUSTOMER_AUTHORITY_PROVENANCE_CLOSED`,
> and `GLOBAL_COVERAGE_CLOSED` claims below were overstated: 6 `booking.router` routes remained
> unverified (runtime tool reported exit 1), and a provider-created confirmed Booking could still
> establish relationship authority by itself (self-bootstrap risk), with no independent-evidence
> requirement on `convert_to_job` or direct `field_ops.create_job(booking_id=...)`. Both gaps are
> closed in Slice 2F-15A (`docs/workflow-rearchitecture/phase-02a-slice-02f15a/`) — see
> `phase-02a-slice-02f15a/documentation-corrections.md` for the full, itemized correction of every
> claim below. Coverage moved from 174/221 (provisional, this file) to 179/220 (canonical, 2F-15A).

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

- **SECURITY_CLOSED**: every Booking mutation in the create/confirm/convert chain now has
  explicit persona enforcement. `create_booking`/`confirm_booking`/`reject_booking`/
  `convert_to_job` are all mutation-scope-aware (`require_tenant_mutation_permission`). Customer
  self-booking server-derives customer identity (structurally, unchanged, re-confirmed).
  Tenant, customer, Booking, and service ownership are enforced. **Unrelated global customers
  cannot be nominated without established authority** — this is the core fix. Wrong personas and
  cross-tenant actors are denied (unchanged, re-verified). No weaker same-Booking route remains
  reaching this specific capability (`add_note` and the cancellation/reschedule routes cannot
  create or confirm a Booking, so they cannot bypass this fix — see alternate-booking-route-audit.md).
- **CUSTOMER_AUTHORITY_PROVENANCE_CLOSED**: Booking creation provenance is explicit (two modes,
  cleanly disambiguated). Confirmation semantics are explicit (`PROVIDER_ACCEPTS_BOOKING`, not
  customer consent — documented, not misrepresented). **Provider-only creation plus
  provider-only confirmation can no longer establish new customer authority** — the exact Slice
  2F-14G exploit chain is directly tested and proven closed
  (`test_bootstrap_attack_no_relationship_rejected`). Qualifying `field_ops` relationship
  evidence now has trustworthy provenance by induction (every qualifying Booking either
  originated from the customer or was backed by a prior qualifying record). Audit/history
  records identify the real actor (unchanged, `confirmed_by_user_id`/`BookingStatusHistory`
  always server-derived).
- **DOMAIN_INTEGRITY_CLOSED**: Booking transitions are unchanged and explicit (this slice's fix
  operates entirely upstream of the state machine). Invalid confirmation creates no side effects
  (pre-existing, re-verified). Conversion eligibility remains intact. Duplicate and final-state
  behavior are explicit (unchanged). Booking and ServiceBooking remain separate (confirmed,
  unmodified).
- **PRIVACY_CLOSED**: unrelated tenants cannot create Booking or Job history for a customer
  (fixed — the creation-time check blocks it before any row exists). Another tenant's customer
  relationship is not disclosed (the relationship query is tenant-scoped; identical error
  regardless of which non-qualifying case applies). Customer identity cannot be impersonated
  (self-booking remains structurally server-derived). Denied attempts create no customer-visible
  records (verified via `db.add.assert_not_called()`).
- **GLOBAL_COVERAGE_CLOSED**: one canonical numerator (174) and denominator (221). Both CSVs
  recount identically. Runtime verification for `field_ops.router`/`field_ops.staff_router`
  remains exit 0; `booking.router` reports exit 1 for its 6 explicitly out-of-scope routes
  (documented, not a regression).
- **PRODUCT_POLICY BLOCKED** for: `booking/router.py`'s `add_note`/cancellation/reschedule
  access-scope hardening; legacy pre-fix Booking data audit; tenant-local customer directory;
  verified invitation workflow; `BookingStatusHistory`-based cancelled/voided disambiguation;
  concurrency hardening. None of these are the security gap this slice was opened to close.

## Scope discipline confirmed

No second router/module was begun. `Booking.convert_to_job`'s own logic, `ServiceJob`,
`ServiceBooking`, `PartsRequest`, `quote_checklist` were not modified.
`FieldOpsService._assert_tenant_customer_relationship` was not modified (confirmed unnecessary).
No role or alias was added. No new permission was added — only the existing
`require_tenant_mutation_permission` dependency (already used across the field_ops series) was
applied to 4 more routes. No cross-pipeline adapter was introduced (the relationship check reuses
existing `Booking`/`Job` models read-only). `readonly@demo-ac-services.local` untouched. Migration
144 unapplied. No visual redesign occurred.

## Coverage

**174 protected of 221** tenant-facing mutation routes (up from the approved 169/210 baseline —
+4 numerator from booking fixes, +1 from `void_booking` newly tracked, +11 denominator from
`booking.router`'s first-time inventory).

## Regression

217 passed across direct slice/dependency suites (0 failures attributable to this slice); 1707
passed in the broad partition sweep, 0 failed.

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-15 approval gate. No
further router module is started. The customer-identity and confirmation-provenance path
disclosed in Slice 2F-14G is now closed at its source.
