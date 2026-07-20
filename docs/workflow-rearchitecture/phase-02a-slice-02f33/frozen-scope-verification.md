# Frozen Scope Verification (WS1)

## Hashes reconfirmed before any edit

| File | Frozen hash (2F-32) | Confirmed live |
|---|---|---|
| `selected-canonical-route-scope.csv` (Set A) | `fc45fa777f47c2c9` | ✓ match |
| `selected-held-adjudication-scope.csv` (Set B) | `593837fac1076324` | ✓ match |
| `selected-out-of-scope-adjacent-routes.csv` (Set C) | `578a7e506b83dc09` | ✓ match |
| Canonical inventory | `1f7891798eb8382f` | ✓ match |
| Matrix | `abac4ae72e8ab1d4` | ✓ match |

All frozen hashes matched exactly before any code or canonical change was
made this slice.

## Route sets, loaded verbatim (not recreated from memory)

**Set A** (1 route): `DELETE /v1/geo/zones/{zone_id}` (`delete_zone`)

**Set B** (2 routes):
- `POST /v1/geo/tenants/{tenant_id}/zones` (`create_zone`)
- `POST /v1/geo/tenants/{tenant_id}/staff/{staff_id}/location` (`update_location`)

**Set C**: 24 rows (23 other canonical unprotected routes + the
`update_zone`/`PUT /v1/geo/zones/{zone_id}` observation) — loaded from
`selected-out-of-scope-adjacent-routes.csv`, none modified this slice.

## Mount confirmation

All 3 scoped routes confirmed mounted via
`authority_model_2f26e.py::route_index()` both before and after this
slice's edits — no route was ever unmounted, no route appears in more
than one scope set, no duplicate/shadowed operation exists for any of the
3.

Every Set A route had a canonical inventory row before this slice (the
existing `PERMISSION_ONLY_NOT_SCOPE_AWARE` row). Every Set B route was
confirmed outside canonical coverage before adjudication (neither
`(POST, /v1/geo/tenants/{tenant_id}/zones)` nor `(POST, /v1/geo/tenants/
{tenant_id}/staff/{staff_id}/location)` appeared in the canonical CSV
prior to this slice's writes).
