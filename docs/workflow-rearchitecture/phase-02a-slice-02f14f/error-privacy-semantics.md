# Error and Privacy Semantics

| Case | Error code | HTTP status | Discloses another tenant? | Discloses Booking/Job details? |
|---|---|---|---|---|
| Unrelated customer (no relationship, any tenant) | `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` | 422 | No | No |
| Customer known only to another tenant | `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` (identical) | 422 | No | No |
| Missing customer (no such User row) | `FOREIGN_CUSTOMER` | 422 | No | No |
| Wrong-role account (not `customer`) | `FOREIGN_CUSTOMER` (identical to missing) | 422 | No | No |
| Disabled/deleted customer | `FOREIGN_CUSTOMER` (identical to missing/wrong-role) | 422 | No | No |
| Foreign Booking | `FOREIGN_BOOKING` | 422 | No | No |
| Foreign parent Job | `FOREIGN_PARENT_JOB` | 422 | No | No |

## Requirements verified

- **Does not reveal another tenant's relationship**: `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` is
  raised identically whether the customer is unknown to every tenant or known only to a
  different one — the relationship query never inspects or returns any other tenant's rows.
- **Does not reveal Booking or Job details**: every relationship/ownership query in `create_job`
  selects only existence (`.id`, `.limit(1)`) or a single already-validated record's own fields —
  none return a *different* tenant's or customer's data to the caller.
- **Safe 404/422/403 semantics consistent with existing APIs**: all new checks use 422
  (`Unprocessable Entity`), consistent with the existing sibling checks
  (`FOREIGN_SERVICE_TYPE`/`FOREIGN_PARENT_JOB`/`FOREIGN_BOOKING`/`FOREIGN_CUSTOMER`, all 422) —
  no inconsistent status code was introduced.
- **One stable domain error for missing tenant/customer authority**:
  `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` is the single, uniform code for this condition — not
  split into "known to another tenant" vs. "never used" variants.
- **Does not expose whether a customer exists in another tenant**: confirmed above.
- **Disabled/deleted/wrong-role reuse the existing `FOREIGN_CUSTOMER` code** rather than
  introducing 3 new distinguishable codes — this is a deliberate privacy choice: distinguishing
  "wrong role" from "disabled" from "deleted" from "doesn't exist" would let a caller enumerate
  account states by trying different `customer_id` values and reading the error code back. A
  single uniform "not a valid customer account" response for all four cases prevents this.
