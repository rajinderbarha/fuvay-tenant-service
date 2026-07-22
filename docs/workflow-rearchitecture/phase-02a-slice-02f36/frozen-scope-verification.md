# Frozen Scope Verification

## Set A/B/C hash reconfirmation (against Slice 2F-34 frozen files)

| Set | File | Frozen hash | Live hash | Match |
|---|---|---|---|---|
| A (18 routes) | `slice-2f36-module-scope.csv` | `0994c5373c08a2b6` | `0994c5373c08a2b6` | YES |
| B (28 routes) | `slice-2f36-held-scope.csv` | `9fe3fe305b53d174` | `9fe3fe305b53d174` | YES |
| C (5 routes) | `slice-2f36-exclusion-scope.csv` | `6adb8d71a4c7e2b6` | `6adb8d71a4c7e2b6` | YES |

No `FROZEN_SCOPE_MISMATCH`.

## Starting position (loaded live from Slice 2F-35's `approval-gate.md`)

- Protected: 252
- Denominator: 273
- Canonical unprotected: 21
- Pending held candidates: 45
- Full phase-2F regression: 2378 passing (confirmed twice, deterministic)

Matches the mission's stated authoritative starting position exactly — no
`AUTHORITATIVE_QUEUE_RECONCILIATION_BLOCKED`.

## Modules (7, 18 canonical routes)

| Module | Set A count | Router file(s) |
|---|---|---|
| `enterprise_grid_saved_views` | 4 | `app/engines/enterprise_grid/router.py` |
| `enterprise_grid_preferences_exports` | 2 | `app/engines/enterprise_grid/router.py` |
| `admin_catalog_provider_setup` | 4 | `app/engines/admin_catalog/{service_option_provider_router,brand_provider_router,recommendation_router}.py` |
| `profile_technician_self_service` | 3 | `app/engines/profile/router.py` |
| `profile_universal_self_service` | 1 | `app/engines/profile/router.py` |
| `marketing_automation_provider` | 3 | `app/engines/marketing_automation/provider_router.py` |
| `analytics_provider_reports` | 1 | `app/engines/analytics/provider_router.py` |

## Held registry modules (10, 28 candidate routes)

`appointments`(7), `ds`(6), `inventory`(5), `catalog`(2), `dispatch`(2),
`settings`(2), `serviceability`(1), `chat`(1), `bookings`(1),
`notifications`(1).

## Exclusion Set C (5 routes) — untouched, confirmed by hash match

`POST /v1/rag/query`, `GET/POST /v1/commerce/tenants/{tenant_id}/deposit*`
(3 routes), `DELETE /v1/webhooks/endpoints/{endpoint_id}`. Note: the
webhook and rag_query routes were CLOSED by Slice 2F-35 (a different,
already-approved slice) after this Set C file was frozen — this is
expected and does not constitute drift of Slice 2F-36's own frozen file
(byte-identical hash confirmed above); Slice 2F-36 does not touch them
either way (forbidden files list explicitly names `app/engines/webhook/*`
and `app/engines/rag/*`).

## Application-file allow-list confirmed touched this slice

- `app/engines/enterprise_grid/router.py`, `services.py`
- `app/engines/admin_catalog/service_option_provider_router.py`
- `app/engines/admin_catalog/brand_provider_router.py`
- `app/engines/admin_catalog/recommendation_router.py`
- `app/engines/profile/router.py`
- `app/engines/marketing_automation/provider_router.py`
- `app/engines/analytics/provider_router.py`
- Router/service files for included Set B routes (per-module, see
  `held-route-adjudication.csv`)
- `app/core/permissions.py`: NOT modified — all 18 Set A routes reused
  existing `require_mutation_access_scope` / `require_staff_or_above_mutation`
  guards (added in Slices 2F-31A/earlier), consistent with the cross-slice
  file-conflict audit's prediction ("no new guard function is
  anticipated").
