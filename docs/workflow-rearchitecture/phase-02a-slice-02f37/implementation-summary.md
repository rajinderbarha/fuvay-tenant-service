# Slice 2F-37 Implementation Summary

Remaining Financial/Product-Policy Authorization and Held-Candidate
Adjudication, executed strictly against the frozen Slice 2F-34 artifacts
in `docs/workflow-rearchitecture/phase-02a-slice-02f34/`. Final
implementation slice before Slice 2F-38's application-wide
reconciliation and certification.

## Set A (3 routes, 1 module — closed)

`platform_commerce_deposit`: `GET /v1/commerce/tenants/{tenant_id}/deposit`,
`POST .../deposit/initiate`, `GET .../deposit/transactions`. Cross-tenant
path was already closed at the service layer
(`CommerceService._assert_owns_tenant_deposit`) — the only gap was the
missing access-scope guard, closed via `require_tenant_mutation_permission`.

## Set B — held candidates (17 routes, 5 modules, all adjudicated)

16 canonically added and protected (`TENANT_PROVIDER_MUTATION_ADD`); 1
already-protected exclude (`commerce` deposit/admin-adjust —
`PLATFORM_ADMIN_EXCLUDE`).

## Real defects found and fixed

- **Pricing zone/rule update/delete had ZERO tenant scoping** — not
  even the client-supplied path `tenant_id` was compared; any tenant
  could modify another tenant's zone surcharge or dynamic pricing rule
  by guessing/enumerating an ID. Fixed via `PricingService._require_trusted_tenant`
  plus a new tenant-ownership check on `ZoneSurcharge`/`DynamicPricingRule`.
- **`commerce.initiate_purchase`/`recalculate_badges` never called the
  existing `_assert_owns_tenant_deposit` helper** despite it already
  existing in the same service — a genuine cross-tenant gap, closed by
  simply calling the pre-existing helper.
- **`recalculate_badges` was guarded by a READ permission
  (`TENANT_HEALTH_READ`) protecting a WRITE** — fixed to
  `require_tenant_mutation_permission(P.TENANT_UPDATE)`.
- **`commerce.warranty/claims` had zero parent-job verification** — a
  client-supplied `tenant_id`/`job_id` pair with a client-supplied
  `amount_requested` was accepted with no proof the job existed,
  belonged to that tenant, or belonged to the claiming customer. Fixed
  via an added `ServiceJob` ownership check.
- **`payments.request_payout`'s `tenant_id` was fully client-controlled**
  — fixed via a new `PaymentService._require_trusted_tenant`. Its
  `amount` field remains an open, honestly-documented financial-
  integrity gap (no balance ledger exists to validate against).
- **`subscriptions.update_plan`'s `tenant_id` was fully client-
  controlled** — fixed via a new `SubscriptionService._require_trusted_tenant`.
- **`compliance` deletion/portability requests let any user request
  erasure/export of ANY OTHER user's data** (`user_id` was fully
  client-supplied) — an existing, fully-implemented DPDP workflow
  already existed; fixed via a self-only ownership check (super_admin
  exempt), with no new retention/deletion policy invented.

## N01 domain-integrity backlog — frozen, not remediated

This slice's own mission prompt (Workstreams 7-12) demanded active N01
remediation, directly conflicting with the frozen 2F-34 contract's
explicit "N01 media files OUT of scope, do not remediate." The frozen
contract was followed: N01's 4-item backlog is re-confirmed unchanged,
not touched. See `n01-final-status.md`.

## Coverage arithmetic

`c=3, a=16, h=16, r=17` → protected 294+3+16=313, denominator 297+16=313,
unprotected 313-313=0, pending held 17-17=0 — exactly matching the
mission's stated expected position for full closure.

## Final status

**CRITICAL_AUTHORIZATION_BATCH_COMPLETE** (per the same 6-status list as
2F-35/36, with `payments` independently carrying
`SECURITY_CLOSED_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`
on its financial-integrity dimension) — see `approval-gate.md`.
