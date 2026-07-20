# Held-Candidate Arithmetic

## Formula

`final_pending_held = starting_pending - r`

- `r` = Set B routes receiving ANY final disposition this slice = **28** (all 28 held routes were adjudicated; none deferred as still-pending).

`45 - 28 = 17`

## Breakdown by disposition

| Disposition | Count | Routes |
|---|---|---|
| `TENANT_PROVIDER_MUTATION_ADD` (canonically added + protected) | 24 | chat(1), inventory(5), appointments(7), catalog(2), dispatch(2), ds(4: demand/recompute, pricing/apply, customer/ltv, ltv/recompute), settings(2), notifications(1) |
| `CUSTOMER_SELF_SERVICE_EXCLUDE` (already protected, excluded from tenant-only canonical CSV by Design A convention) | 1 | bookings(1): POST /v1/bookings |
| `READ_ONLY_EXCLUDE` | 3 | serviceability/check(1), ds churn/score(1), ds demand/forecast(1) |
| **Total adjudicated** | **28** | |

Every included canonical addition (24 routes) was protected in this same
slice — none deferred with a silent gap, per mission rule "do not add an
included mutation canonically and silently defer its security
remediation."
