# Alternate Finance Route Audit — Workstream 11

## Method
Grepped `app/engines/{package_commerce,platform_commerce,payment,customer_credits}`
for warranty/claim/payout/deposit mutation routes that might duplicate or
bypass `finance_hub.admin_router`'s 17 mutations.

## Findings

### `platform_commerce/router.py` — warranty claims
Contains its own `/warranty/claims/{claim_id}/approve` and `/reject`
routes (lines 433-444), each gated by `Depends(require_super_admin)` and
calling `CommerceService.approve_claim` / `.reject_claim` — **the same
service methods** `finance_hub.admin_router`'s `approve_claim`/`reject_claim`
delegate into via `self._commerce`. This is not a bypass: both entry
points converge on the same underlying service call, and the
`platform_commerce` route is gated even more strictly (direct
`require_super_admin` role check) than finance_hub's permission-based gate
(which is *also* effectively super-admin-only today, since
`FINANCE_CLAIMS_APPROVE`/`REJECT` are granted to no role). **Disposition:
CANONICAL_PLATFORM_WRITE (dual entry, consistent gating, no security gap).**
Also present: `submit_claim` (customer-initiated, `get_current_user` only
— correct, this is the customer's own claim submission, not an admin
mutation) and two list/detail GET routes (`require_super_admin` /
`get_current_user`, both reads).

### `payment/router.py` — payouts
Contains `/tenants/{tenant_id}/payout` (POST, **request** a payout,
gated by `require_permission(P.TENANT_BILLING_MANAGE)`) plus 2 GET
routes (`get_payout`, `list_payouts`). This is the upstream "request"
step of the payout lifecycle — a distinct action from finance_hub's
`approve_payout`/`reject_payout`/`mark_processing`/`mark_completed`/
`mark_failed`, which govern the payout's admin-side progression after
a request exists. No overlap or route collision: different HTTP paths,
different lifecycle stage, different permission. **Disposition:
CANONICAL_PLATFORM_WRITE (distinct lifecycle stage, not a duplicate).**

### `customer_credits` / `usage_credits`
No mutation routes overlapping with `finance_hub`'s topup/deposit
actions were found — `customer_credits` governs the customer-facing
credit ledger (already audited/fixed in an earlier slice, FINAL-L5-05J),
a distinct domain object from `CreditTopupOrder`/`SecurityDeposit`.

### `tenant_engine`, billing, subscriptions, invoices, reconciliation
No routes were found in these modules that write to
`security_deposits`, `credit_topup_orders`, `payout_records`, or
`warranty_claims` — no additional alternate routes found.

## `--verify-overlap` result
Ran `scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-overlap`
comparing `finance_hub.admin_router` against `platform_commerce.router`
and `payment.router`: **zero path collisions** (all paths are distinct
strings; the shared-service-method convergence noted above is at the
service layer only, not a route-level duplicate).

## Conclusion
2 alternate-route families found (`platform_commerce` claims,
`payment` payout-request), both classified `CANONICAL_PLATFORM_WRITE` —
neither is a bypass of finance_hub's authorization, and neither required
closing or modification.
