# Slice 2F-9 Implementation Summary

## Scope
Fully investigate, classify, protect, and verify every mounted mutation
endpoint owned by `app.engines.complaints.provider_router` — 9 mounted
mutations, confirmed via runtime introspection.

## What was found
**All 9 mutations were completely unprotected** before this slice —
`get_current_user` only, with no role, permission, or access-scope check
of any kind. Any authenticated user of any role (including customer,
guest, or a cross-tenant staff member) could respond to complaints,
offer resolutions, schedule/start/complete rework, review refunds,
submit AI settlement answers, and create/respond to settlement
proposals for **any tenant's complaint**.

No `COMPLAINT_*`/`REWORK_*`/`REFUND_*` permission exists anywhere in the
permission registry. Per "do not grant a permission merely because no
role currently has it," all 9 routes are now gated with
`require_tenant_owner_mutation` — the narrowest existing composed
dependency (tenant_owner role, access-scope-aware), granting nothing new.

**Four additional, directly-connected cross-tenant bypasses** were found
at the service layer, independent of the router-level guard:
1. `create_settlement_proposal` used `_get_complaint` (no tenant check)
   instead of `provider_get_complaint`.
2. `ServiceReworkService._get_rework` (used by schedule/start/complete)
   had zero tenant check.
3. `RefundRequestService._get_refund` had zero tenant check.
4. `_get_settlement_proposal` did not cross-check a supplied
   `proposal_id` against the already-verified `complaint_id` — the
   deepest finding, since `respond_to_settlement` can trigger a real
   internal credit-wallet/security-deposit payout on dual acceptance
   (`_execute_settlement_payout`, via the canonical
   `DisputeSettlementService`, never real money).

## What changed
1. **`app/engines/complaints/provider_router.py`** — all 9 endpoints
   now use `require_tenant_owner_mutation`; `tenant_id` threaded through
   to the 5 service calls that needed it.
2. **`app/engines/complaints/rework_service.py`** — `_get_rework` and 3
   mutation methods + `get_rework` now accept and enforce an optional
   `tenant_id`.
3. **`app/engines/complaints/refund_service.py`** — `_get_refund`,
   `provider_review_refund`, `get_refund` — same fix.
4. **`app/engines/complaints/complaint_service.py`** —
   `create_settlement_proposal` uses `provider_get_complaint` when
   `tenant_id` is supplied; `_get_settlement_proposal` cross-checks
   `proposal.complaint_id`.
5. **`frontend/tenant-portal/app/(tenant)/provider/complaints/[complaint_id]/page.tsx`** —
   4 mutation controls ("Send reply," "Offer resolution," "Propose
   settlement," "Accept"/"Reject" a proposal) previously had **no role
   gate at all**; now conditionally rendered via
   `isTenantOwnerRole(getUserRole()) && !isTenantReadOnly()`, reusing the
   same helpers from Slices 2F-7/2F-8.
6. **Test suite**: new `tests/test_phase2f9_complaints_provider_authorization.py`
   (84 tests — persona enforcement for all 9 routes, direct proof of all
   4 service-layer bypass fixes via genuinely mismatched fixtures,
   existing-guard regression checks, module-verification parity).
7. **Global coverage docs**: `mutation-enforcement-matrix.csv` and
   `tenant-mutation-endpoint-inventory.csv` updated in place.

## What did NOT change
No previously-closed module was modified. Admin Catalog (2F-8),
Serviceability (2F-7), and Invoice/Payment (2F-6/6A/6B) closures remain
valid and untouched. `complaints.customer_router` and
`complaints.admin_router` were read for context (the admin router
confirmed `require_super_admin`-gated throughout, correctly stronger)
but not modified. `execution.real_estate_router`/`coaching_router` were
not begun. No permission was granted. No new role was introduced.
`readonly@` and migration 144 were untouched.

## Outcome
`SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED` — see
`approval-gate.md`. Global tenant-mutation coverage: **97/182 → 106/182**
(+9, all genuinely newly protected — this module had zero protection
before this slice).
