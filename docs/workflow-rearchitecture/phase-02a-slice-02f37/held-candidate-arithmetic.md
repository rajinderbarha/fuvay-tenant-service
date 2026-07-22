# Held-Candidate Arithmetic

## Formula

`final_pending_held = starting_pending - r`

- `r` = Set B routes receiving ANY final disposition this slice = **17**
  (all 17 held routes were adjudicated; none deferred as still-pending).

`17 - 17 = 0`

## Breakdown by disposition

| Disposition | Count | Routes |
|---|---|---|
| `TENANT_PROVIDER_MUTATION_ADD` (canonically added + protected) | 16 | pricing(9), payments(1), subscriptions(1), commerce(3: wallet/purchase/initiate, warranty/claims, badges/recalculate), compliance(2) |
| `PLATFORM_ADMIN_EXCLUDE` (already protected, excluded from tenant-only canonical CSV) | 1 | commerce(1): POST /v1/commerce/tenants/{tenant_id}/deposit/admin-adjust |
| **Total adjudicated** | **17** | |

Every included canonical addition (16 routes) was protected in this same
slice — none deferred with a silent gap. One route
(`POST /v1/payments/tenants/{tenant_id}/payout`) was canonically added
and closed for its authorization/tenant-trust dimension, but carries an
explicit, honestly-documented financial-integrity gap on its
client-supplied `amount` field (no authoritative balance ledger exists
to validate against — see `known-limitations.md` and
`financial-domain-integrity-audit.csv`).
