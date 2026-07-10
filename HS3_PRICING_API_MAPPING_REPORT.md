# HS3 — Pricing API Mapping Report

## Real endpoints (confirmed via source, mostly pre-existing)
| Ticket-suggested | Real |
|---|---|
| `GET /v1/admin/home-services/pricing-rules` | `catalogApi.listPricingRules()` → real `GET /v1/admin/pricing-rules` (generic, filtered client-side to Home Services service IDs) |
| `POST /v1/admin/home-services/pricing-rules` | `POST /v1/admin/pricing-rules` — real, **this sprint added 2 new validations** (brand-requires-type, duplicate check) |
| `PUT .../pricing-rules/{rule_id}` | `PUT /v1/admin/pricing-rules/{rule_id}` — real, unchanged |
| `DELETE .../pricing-rules/{rule_id}` | Not independently verified this sprint |
| `POST .../price-experience/preview` | Real symmetric-formula function exists (`compute_symmetric_customer_price_tiers`) and is reachable via the tenant-side preview endpoint (`POST /v1/tenant/home-services/price-options/preview`, certified in an earlier sprint) — no dedicated admin-side preview endpoint was added this sprint |
| `GET .../pricing-rules/summary` | Not found — the pricing-rules page doesn't currently show dedicated health/summary cards (see UI gap in Remaining Blockers) |
| `GET .../pricing-rules/audit` | Not independently verified this sprint |
| `GET /v1/tenant/home-services/pricing-rules/allowed` | Real — `_find_admin_pricing_rule` serves this purpose via `GET .../type-pricing` and `GET .../brand-pricing` |
| `POST /v1/tenant/home-services/price-options/preview` | Real, pre-existing, certified in an earlier sprint |
| `PUT /v1/tenant/home-services/services/{id}/pricing` | Real — `PUT .../types/{type_id}/pricing` and `PUT .../brands/{brand_id}/pricing` |

## No mock data
Confirmed: all pricing-rule data on the admin page comes from the real
`catalogApi.listPricingRules()`/`createPricingRule`/`updatePricingRule`
calls; all live-verification this sprint was against the real running
backend and real Postgres data.

## Verdict
API integration: **real**. Two backend methods hardened this sprint
(`create_pricing_rule` with 2 new validations). No dedicated admin-side
summary/audit endpoints exist — documented gap, not fabricated.
