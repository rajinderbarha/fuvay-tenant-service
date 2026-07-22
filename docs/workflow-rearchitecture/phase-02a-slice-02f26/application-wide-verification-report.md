# Application-Wide Verification Report — Slice 2F-26

## Result: EXIT 0 — all checks green

```
Inventory completeness:
  PASS  every mounted route is exported            (2299)
  PASS  every route has a behaviour classification
  PASS  no route remains UNKNOWN_BEHAVIOR
  PASS  every genuine mutation has a persona
  PASS  mutating GET audit exists
  PASS  read-only POST audit exists

Canonical integrity:
  PASS  no canonical row has a forbidden protection status
  PASS  no duplicate canonical route keys
  PASS  protected + unprotected == denominator
  PASS  every canonical row resolves to a mounted route
  PASS  every confirmed tenant mutation has a canonical row

Generic-prefix blind spot:
  PASS  generic-prefix tenant mutations are represented
        (65 canonical rows sit on non-tenant-prefixed paths)

Verifier non-vacuity:
  PASS  docstring text cannot satisfy a source check
  PASS  WHERE-clause inspection ignores SELECT column lists

Documentation honesty:
  PASS  no document claims completeness while checks fail

CURRENT_CANONICAL_COVERAGE: 214/257, 43 unprotected
VERIFIER PASSED
```

## Note on "every canonical row resolves to a mounted route"

This check uses a **GET-inclusive** walk. The pre-existing
`inventory_mutation_routes.walk()` filters to POST/PUT/PATCH/DELETE, so it
cannot see the two mutating-GET rows now in the canonical CSV
(`GET /v1/commerce/tenants/{tenant_id}/deposit` and `.../deposit/transactions`,
both of which lazily create a row through `_get_or_create_deposit`).

`test_phase2f17a`'s equivalent assertion was widened the same way rather than
exempting those rows — the point is to prove they *are* mounted, not to skip
them.

## Coverage statement

`CURRENT_CANONICAL_COVERAGE: 214 protected of 257`, 43 unprotected across 11
modules. See `known-limitations.md` for why this is still not asserted as a
final application-wide figure.
