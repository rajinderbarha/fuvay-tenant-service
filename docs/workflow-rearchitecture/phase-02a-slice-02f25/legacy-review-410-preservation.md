# Legacy 410 Preservation — Slice 2F-25

## Status: PRESERVED

`POST /v1/reviews` still raises `HTTPException(status_code=410)` and is still
declared `status_code=status.HTTP_410_GONE`.

## Proof obligations

| Obligation | Evidence |
|---|---|
| Route still returns 410 | `test_create_route_still_returns_410` asserts both the decorator status and the raise |
| No alternate mount reactivates it | `test_no_alternate_mount_reactivates_creation` asserts the router never calls `s.create_review(`; the service method survives for seeding/tests only |
| No frontend depends on successful creation | caller audit found no application posting to `/v1/reviews` (tenant-portal uses reply/flag/resolve/requests/list only) |
| No route-ordering conflict shadows it | the 410 route is declared on the exact path `""` under the `/v1/reviews` prefix; the runtime walk reports `POST /v1/reviews` present, so no later declaration shadows it |
| No service correction re-enabled it | this slice changed `submit_reply`, `flag_review`, `get_review` and the tenant-pinning of five methods — `create_review` was not touched |

## Canonical creation pipeline untouched
Reviews are created through the `customer_reviews` engine. Slice 2F-24's
closure of that pipeline is asserted intact by
`TestPreviousClosuresIntact::test_canonical_customer_reviews_closure_intact`.

## Coverage treatment
`POST /v1/reviews` is classified `DEPRECATED` and was **not** added to the
canonical denominator — a 410 route performs no mutation.
