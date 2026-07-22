# Residual Error Privacy Equivalence — Slice 2F-25A

Comparison of MISSING versus UNAUTHORIZED (foreign) for each capability.

| Capability | Missing | Foreign / unauthorized | Equivalent? |
|---|---|---|---|
| Aggregate entity | zero-count body, HTTP 200 | zero-count body, HTTP 200 (excluded by the tenant predicate) | **YES** |
| Job review request | `NotFoundException("ReviewRequest", job_id)` | identical | **YES** |
| Customer review list | empty list, HTTP 200 | empty list for another tenant's rows; `NotFound` for another customer (customer persona) | **YES** within each persona |
| create_request parent Job | `NotFoundException("Job", job_id)` | identical | **YES** |
| create_request customer relationship | `CUSTOMER_MISMATCH` | `CUSTOMER_MISMATCH` | **YES** |

## Detail

**Aggregate** — the pre-existing contract returns a zero-count body for "no
reviews yet". A foreign entity now falls into the same branch because the
tenant predicate excludes it, so the caller cannot distinguish "does not
exist" from "belongs to someone else". No status-code or shape difference.

**Job request / parent Job** — both raise the same `NotFoundException` with
the same entity label and the same supplied id echoed. No header or body
difference.

**`CUSTOMER_MISMATCH`** — deliberately does *not* reveal the job's real
customer id. It states only that the supplied customer does not match.

## One asymmetry, disclosed
For the **customer** persona, `list_by_customer` raises `NotFound` when asking
for another customer, whereas a tenant principal asking for an unrelated
customer receives an **empty list**. These are different personas on different
code paths, so they are not comparable to each other — within each persona the
missing/unauthorized pair is equivalent, which is the property that matters.
Recorded rather than smoothed over.
