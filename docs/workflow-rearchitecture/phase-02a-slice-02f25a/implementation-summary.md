# Implementation Summary — Slice 2F-25A

Every one of the six unapproved points was justified. This slice closes them.

## What was actually unproven in 2F-25

| # | Claim made | Reality |
|---|---|---|
| 1 | "PRIVACY — CLOSED" | three mounted reads were knowingly unscoped |
| 2 | "runtime verification exits zero" | there was no verifier script; the claim rested on a test suite that did not check the residual reads |
| 3 | `create_request` FULLY_PROTECTED | it took `job_id` AND `customer_id` from the request body with **no proof** the job existed, belonged to the tenant, or that the customer was that job's customer |
| 4 | "denominator reconciled" | true for this engine, but the generic-prefix blind spot means it is not application-wide complete |
| 5 | environment statements | contradictory: "no live DB/server" appeared alongside evidence the stack was up |
| 6 | final status | over-claimed on the strength of 1-3 |

## The four capabilities, now closed

**`GET /aggregates/{entity_type}/{entity_id}`** — was completely unscoped, so
any authenticated principal could read any tenant's or staff member's
aggregate ratings by guessing an id: a reputation oracle. `ReviewAggregate`
carries a real `tenant_id`, so it is now tenant-scoped. It is **not** claimed
public: no allow-list of public entity types exists and inventing one would be
new product policy.

**`GET /requests/jobs/{job_id}`** — was a bare `job_id` lookup. Now
relationship-scoped: customers see only requests addressed to them; every
other principal is confined to its own tenant.

**`GET /customers/{customer_id}`** — `_assert_owns` fires **only** for
`actor_role == "customer"`, so a tenant principal could enumerate any
customer's entire review history across all tenants. Non-customer principals
are now restricted to their own tenant's rows.

**`create_request`** — now resolves the parent `field_ops.Job` by
`job_number` **within the caller's tenant**, derives `customer_id` from that
Job, and rejects a mismatching client value (`CUSTOMER_MISMATCH`). Ownership
runs **before** the duplicate check, which previously leaked foreign job
numbers through the global `already_exists` response.

## A regression 2F-25 introduced, found and repaired

`field_ops.service` creates the review request on job close and constructed
`ReviewService(...)` with **no tenant context**. 2F-25's tenant pinning
therefore raised `TENANT_ACCESS_DENIED` on every job close — swallowed by an
`except Exception` that only logs a warning. **Review requests silently
stopped being created.**

Confirmed empirically before fixing, not inferred. The node-ID regression
comparison could not see it: the exception is caught, and no test covers that
path. That is a real limitation of the methodology, recorded in
`known-limitations.md`.

Repaired by passing the Job's own tenant (the authoritative source) and
marking the call `trusted_internal=True`.

## Verifier

A real verifier now exists at
`scripts/workflow_rearchitecture/verify_legacy_review.py`. It checks the
actual conditions, strips docstrings/comments before matching (both 2F-24 and
this slice had assertions satisfied by prose), and **exits non-zero** on any
gap. Its discriminating power is itself tested.

## Coverage

**CURRENT_CANONICAL_COVERAGE: 212 of 229**, unchanged by this slice — no route
was added or removed; `create_request` simply now *earns* the classification
it was previously given. Explicitly **not** application-wide complete.

## Final status
**`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`** for
the legacy review engine specifically — see `approval-gate.md` for the exact
scope of that claim.
