# Phase 3B — Backend Router Report

## Bargain Rules endpoints (`app/engines/admin_catalog/admin_router.py`)

| Method | Path | Status |
|---|---|---|
| GET | `/v1/admin/pricing/bargain-rules/summary` | **new** — 8 KPIs |
| GET | `/v1/admin/pricing/bargain-rules` | extended (search/category/bargain_enabled/provider_approval_required/below_floor_action filters) |
| GET | `/v1/admin/pricing/bargain-rules/{rule_id}` | unchanged path, enriched response |
| POST | `/v1/admin/pricing/bargain-rules` | unchanged path, duplicate + floor-bounds validation added |
| PUT | `/v1/admin/pricing/bargain-rules/{rule_id}` | unchanged |
| POST | `/v1/admin/pricing/bargain-rules/{rule_id}/enable` | pre-existing, kept for backward compatibility |
| POST | `/v1/admin/pricing/bargain-rules/{rule_id}/disable` | pre-existing, kept for backward compatibility |
| POST | `/v1/admin/pricing/bargain-rules/{rule_id}/activate` | **new** (alias of enable, ticket-required name) |
| POST | `/v1/admin/pricing/bargain-rules/{rule_id}/deactivate` | **new** (alias of disable, ticket-required name) |
| POST | `/v1/admin/pricing/bargain-rules/{rule_id}/validate` | **new** — 5-check validation panel |
| GET | `/v1/admin/pricing/bargain-rules/{rule_id}/audit` | **new** |
| POST | `/v1/admin/pricing/bargain/evaluate-preview` | unchanged path, response shape rewritten |

Note: `/v1/pricing/bargain/evaluate` (public/tenant-facing, non-admin) was
searched for and does **not** exist in this codebase — only the admin-preview
evaluation endpoint exists. This is a pre-existing gap, not introduced this
sprint; documented in remaining blockers since the ticket references it as
"if it exists."

## Provider Pricing Overrides endpoints

| Method | Path | Status |
|---|---|---|
| GET | `/v1/admin/pricing/provider-overrides/summary` | **new** — 8 KPIs |
| GET | `/v1/admin/pricing/provider-overrides` | extended (status + search filters) |
| GET | `/v1/admin/pricing/provider-overrides/{override_id}` | unchanged path, enriched response |
| POST | `/v1/admin/pricing/provider-overrides` | unchanged path, duplicate + renamed error codes |
| PUT | `/v1/admin/pricing/provider-overrides/{override_id}` | unchanged path, renamed error codes |
| POST | `/v1/admin/pricing/provider-overrides/{override_id}/approve` | unchanged |
| POST | `/v1/admin/pricing/provider-overrides/{override_id}/reject` | unchanged |
| POST | `/v1/admin/pricing/provider-overrides/{override_id}/enable` | pre-existing, kept for backward compatibility |
| POST | `/v1/admin/pricing/provider-overrides/{override_id}/disable` | pre-existing, kept for backward compatibility |
| POST | `/v1/admin/pricing/provider-overrides/{override_id}/activate` | **new** (alias, ticket-required name) |
| POST | `/v1/admin/pricing/provider-overrides/{override_id}/deactivate` | **new** (alias, ticket-required name) |
| POST | `/v1/admin/pricing/provider-overrides/validate-preview` | **new** — dry-run validation |
| GET | `/v1/admin/pricing/provider-overrides/{override_id}/audit` | **new** |

Route-ordering note: `summary` and `validate-preview` are literal path
segments registered ahead of their sibling `{id}`-parameterized routes in the
same router, and FastAPI/Starlette matches routes in registration order —
verified live: `GET /pricing/bargain-rules/summary` correctly hit the summary
handler, not `get_bargain_rule("summary")`.

## Live verification (real backend + real Postgres, `admin@serviceos.in` super_admin token)

All of the following were exercised over real HTTP after a full backend
restart to pick up the new code:

- `GET .../bargain-rules/summary` → 8-key KPI object, real counts (1 total, 1
  bargain-enabled service, 0 validation issues).
- `GET .../bargain-rules` → returns `master_service_name: "AC Repair"`,
  `base_price/min_price/max_price: 800/600/1200`, `readiness: "inactive"`,
  `warning: "Bargaining is configured but this rule is inactive."` for the
  seeded (still-inactive) AC Repair bargain rule from the prior sprint.
- `POST .../bargain-rules/{id}/activate` → `readiness` flips to `"ready"`,
  `warning` becomes `null`.
- `POST .../bargain/evaluate-preview` with `offer_price: 500` → `"decision":
  "rejected"`, `"reason": "Offer is below bargain floor."`, `bargain_floor:
  650`. With `offer_price: 650` → `"decision": "accepted"`, `rule_used: "AC
  Repair Bargain"`, `pricing_source: "pricing_rule"` — matches the ticket's
  exact expected JSON shape field-for-field.
- `POST .../bargain-rules/{id}/validate` → all 5 checks `true`, `"valid": true`.
- `GET .../bargain-rules/{id}/audit` → 2 real audit entries (`create`, then
  the `inactive` status change from the prior sprint), each with
  `request_id`.
- `POST .../bargain-rules/{id}/deactivate` → reverted rule to its original
  `inactive` state to leave DB unchanged for future test runs.
- `GET .../provider-overrides/summary` → real counts (1 total, 1 active, avg
  price 900).
- `GET .../provider-overrides` → returns `tenant_name: "Demo AC Services"`,
  `tenant_code: "demo-ac-services"` (never the raw tenant UUID as primary
  display), `platform_min/max/base_price: 600/1200/800`, `delta_from_base: 100`.
- `POST .../provider-overrides/validate-preview` with `override_price: 500` →
  `OVERRIDE_BELOW_PLATFORM_MIN` + `DUPLICATE_ACTIVE_OVERRIDE` (a real active
  override already exists for this tenant/service from the prior sprint —
  correct behavior, not a bug: the new duplicate-check is working as
  designed). With `override_price: 1300` → `OVERRIDE_ABOVE_PLATFORM_MAX` +
  the same duplicate flag.
- `GET .../provider-overrides/{id}/audit` → 2 real audit entries (`create`,
  `approve`).
- `GET /openapi.json` → all 12 bargain + 13 override paths present (see
  `PHASE_3B_SWAGGER_OPENAPI_REPORT.md`).

## Result: **Router endpoints wired and live-verified — PASS**
