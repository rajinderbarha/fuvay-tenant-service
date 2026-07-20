# Slice 2F-10 Implementation Summary

## Scope
Complete authorization, ownership, state-integrity and IDOR closure for
`app.engines.complaints.customer_router` (15 mounted routes: 8 mutation +
7 read). Runtime introspection performed fresh — no prior finding or
count was assumed.

## What was found
1. **Router-level role gap (same class as Slice 2F-9's provider finding,
   independently re-verified, not assumed)**: all 15 routes used
   `Depends(get_current_user)` only — authentication, no role check.
   Any authenticated user of any role (tenant_owner, staff, technician,
   another customer, even guest) could call every customer complaint
   endpoint.
2. **`create_complaint` had zero record-ownership check**: any
   authenticated caller could file a complaint against any
   booking/job/invoice/appointment/lead/review by ID, for any customer's
   record. `ComplaintEligibilityService` already had the correct
   ownership logic (`_fetch_record`/`_customer_owns_record`), used
   correctly by the separate advisory `check-eligible` endpoint, but it
   was never wired into actual creation.
3. **`create_refund_request_from_complaint` had zero complaint-ownership
   check**: unlike every other customer_router route, it called a bare
   `get_complaint` (fetch-by-id, no owner check) instead of
   `get_customer_complaint`. Any authenticated user could create a refund
   request against any complaint_id.
4. **`_get_resolution` had no complaint cross-check**: the identical bug
   class Slice 2F-9 fixed for `_get_settlement_proposal` — a customer who
   proved ownership of complaint A could still accept/reject a
   `resolution_id` belonging to a foreign complaint B.
5. **Ordering defect**: `customer_accept_resolution`/
   `customer_reject_resolution` mutated `resolution.status` — and, for a
   rework resolution, created AND COMMITTED a real
   `ServiceReworkRequest` — *before* validating the complaint's
   state-transition legality.

## What was already correct (verified, not re-fixed)
- `customer_respond_to_settlement` already uses the Slice 2F-9
  cross-checked `_get_settlement_proposal(db, proposal_id,
  complaint_id=complaint_id)` — a shared service method, so customer and
  provider paths both benefited from that fix already.
- Message/media visibility filtering (`ComplaintMessage.is_visible_to`)
  already correctly restricts customer reads to `public_to_case`/
  `customer_only` content.
- `_check_dual_acceptance`/`_execute_settlement_payout` (canonical
  `DisputeSettlementService` path) already blocks monetary remedies,
  requires dual acceptance, and takes no customer-supplied amount —
  `SettlementRespondIn` has no amount/remedy field at all.

## What changed
1. **`app/engines/complaints/customer_router.py`** — all 15 routes now
   use `Depends(require_customer)` (the pre-existing, already-used-elsewhere
   canonical customer-role dependency) instead of `get_current_user`.
2. **`app/engines/complaints/complaint_service.py`**:
   - `create_complaint` — added record-ownership verification via
     `self._eligibility._fetch_record`/`_customer_owns_record`.
   - `_get_resolution` — added an optional `complaint_id` cross-check
     parameter, mirroring `_get_settlement_proposal`'s Slice 2F-9 fix.
   - `customer_accept_resolution`/`customer_reject_resolution` —
     reordered to validate the complaint's state-transition legality
     (via `ALLOWED_TRANSITIONS_EXT`) *before* mutating `resolution.status`
     or creating a rework request.
3. **`app/engines/complaints/refund_service.py`** —
   `create_refund_request_from_complaint` now uses
   `get_customer_complaint` (ownership-checked) when
   `actor_type == ACTOR_CUSTOMER`.
4. **`scripts/workflow_rearchitecture/inventory_mutation_routes.py`** —
   added a new `CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED` guard-status
   classification for `require_customer`-gated routes, recognizing that
   customer self-service routes are a genuinely different authorization
   model than tenant mutations (no tenant `access_scope` concept applies
   to an ordinary customer account) — mirrors the reasoning already
   established for the existing customer-own-address exemptions.
5. **New test file**: `tests/test_phase2f10_customer_complaints_authorization.py`
   (25 tests) — router-level role-gate HTTP tests (unauthenticated,
   every denied role, correct-customer-clears-gate) + direct service-layer
   IDOR/ownership/ordering-defect tests.
6. Two pre-existing tests (`test_sprint25_complaints.py::test_create_complaint_success`,
   `test_sprint75_dispute_settlement.py::test_create_complaint_sets_sla_deadlines`)
   updated to stub the new, correct ownership check their mocked fixtures
   didn't previously need to satisfy.

## What did NOT change
`complaints.provider_router` and `complaints.admin_router` were not
modified. `execution.real_estate_router`, `execution.coaching_router`
were not begun. No permission was created. No role was created — the
canonical `customer` role and `require_customer` dependency both already
existed and are reused verbatim. The dual-acceptance settlement model,
`ALLOWED_TRANSITIONS_EXT`, `FINAL_STATUSES`, and the booking-pipeline
architecture were not changed. No visual redesign occurred — no frontend
file was touched at all (see `frontend-customer-exposure-audit.md`).
`readonly@demo-ac-services.local` and migration 144 were untouched.

## Outcome
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` —
see `approval-gate.md`. Global tenant-mutation coverage unchanged:
**106/182** — customer self-service routes were never part of that
denominator and remain tracked separately (see `global-coverage-update.md`).
