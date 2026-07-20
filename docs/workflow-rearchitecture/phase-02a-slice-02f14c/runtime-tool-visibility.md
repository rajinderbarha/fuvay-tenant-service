# Runtime Tool Visibility

## No tool changes were required

`scripts/workflow_rearchitecture/inventory_mutation_routes.py`'s `guard_status()` already
recognized `require_staff_or_above_mutation` (added in an earlier slice, 2F-6A/2F-14B era) and
maps it to `STAFF_EXECUTION_ROLE_SCOPE_AWARE` — a status already in `ACCEPTED_GUARD_STATUSES`.
Adding this dependency to `add_note`/`add_media` was sufficient for the tool to report both as
protected with zero tool modification.

## Verified via the tool itself, not source-string assertion

```
PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py \
  --verify-module app.engines.field_ops.router
```

Returns `"unverified_count": 0`, `"unverified_routes": []`, exit code `0` — confirmed directly
against the live, mounted FastAPI application (not a hand-maintained CSV), for all 28 routes.

## Distinctions the tool already makes

- Router-level composed protection: `STAFF_EXECUTION_ROLE_SCOPE_AWARE` /
  `TENANT_MUTATION_PERMISSION_SCOPE_AWARE` / `CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED` (all
  dependency-name-based).
- Service-level-only protection (tool-invisible by design, since the tool only introspects
  FastAPI dependency names, not service method bodies): this was exactly `add_note`/`add_media`'s
  prior state, now eliminated by adding the router-level dependency.

No new guard-status category or tool logic was added this slice — the existing categories were
sufficient once the correct dependency was wired at the router.
