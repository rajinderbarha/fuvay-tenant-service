# FINAL-L5-04B — Service Setup Enforcement Report

## Real enforcement added: `app/engines/admin_catalog/tenant_service.py::enable_service()`
Inserted immediately after the existing "category active" check (line ~163), before the "already enabled" check:

```python
if svc.service_group_id:
    has_entitlement = await entitlement_service.has_category_entitlement(
        self.db, tenant_id, svc.service_group_id
    )
    if not has_entitlement:
        raise ServiceOSException("CATEGORY_NOT_ENTITLED", ..., status_code=403)
```

## Required conditions (mission's list)
| Condition | Status |
|---|---|
| 1. Parent module is active and entitled | Category-level check implies module-level (a category entitlement cannot exist without an ACTIVE parent module entitlement — enforced at assignment time) |
| 2. Category is active and entitled | **Enforced and live-tested** |
| 3. Service belongs to that category | Structural — `svc.service_group_id` is read directly from the `MasterService` row being enabled |
| 4. Tenant role has mutation permission | Pre-existing, unaffected — `require_tenant_mutation_permission(P.TENANT_UPDATE)` still gates the endpoint |

## Protected surface — honest scope
Only **Services** (`enable_service`) is guarded this sprint. **Service Types, Brands, Issues, Pricing, Coverage, Availability, Publish Readiness** were not individually wired to entitlement checks — real gap, listed in Remaining Blockers. The rationale: `enable_service` is the single upstream gate through which a tenant first gains access to configure anything else about a service (types/brands/pricing are all sub-configuration of an already-enabled `TenantService` row) — so this one guard closes the primary door, even though downstream sub-configuration endpoints don't have their own independent redundant check yet.

## Required behavior
| # | Requirement | Result |
|---|---|---|
| 1 | Existing historical setup remains readable | **Confirmed** — the guard only fires inside `enable_service` (a create/re-enable path); `list_enabled_services`/`get_enabled_service` (read paths) were not touched and remain unguarded, so existing configured services stay fully visible regardless of current entitlement state |
| 2 | New setup is blocked after entitlement disable | **Live-verified**: disabled AC & HVAC entitlement, confirmed `enable_service` for an AC-group service now returns 403 |
| 3 | Re-enable restores editing | **Live-verified**: re-enabled the entitlement, confirmed the same `enable_service` call for an AC-group service then succeeds (201) |
| 4 | No orphan setup created | The guard runs before any `TenantService` row is created/mutated — a rejected call creates nothing |

## Regression check
Adding this guard broke 4 pre-existing unit tests in `tests/test_sprint3_catalog.py` (their `make_service()` fixture uses `MagicMock(spec=MasterService)`, which fabricates a truthy `service_group_id` for any unset attribute, incorrectly tripping the new guard). Root-caused and fixed by adding an explicit `service_group_id=None` default to the fixture (a real, legitimate case — a service with no group — not a workaround). Full suite re-run confirmed **0 regressions**: 90 failed/42 errors both before and after (pre-existing, unrelated), 8827 passed (8804 baseline + 23 new entitlement tests).

## Result
One real, live-tested backend enforcement point on the primary service-enablement gate. Downstream sub-configuration endpoints (types/brands/pricing/coverage/availability/publish-readiness) remain unguarded — honestly documented, not silently assumed covered.
