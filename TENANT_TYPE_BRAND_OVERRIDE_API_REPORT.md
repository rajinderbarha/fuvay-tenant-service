# Tenant Type-Brand Override API Report

## Real endpoints (already existed, now correctly used by the frontend)
| Ticket-suggested | Real |
|---|---|
| `GET .../pricing-rules/allowed` | `GET .../brand-pricing?service_type_id=` returns `admin_floor_price`/`admin_ceiling_price` per type — same purpose |
| `PUT .../services/{id}/brand-pricing` | `PUT .../brands/{brand_id}/pricing?service_type_id=` — real, now correctly called with `service_type_id` from the frontend (this sprint's fix) |
| `POST .../price-options/preview` | `POST /v1/tenant/catalog/price-options/preview` — real, unchanged, now called per-type-scoped row |
| `POST .../services/publish` | `POST .../publish` — real, unchanged; live-verified this sprint to preserve type-scoped overrides |

## Payload shape — matches the ticket exactly
```json
{"tenant_min_price": 650, "tenant_max_price": 750}
```
with `service_type_id` as a query parameter (not body field) — real,
functioning, live-verified this sprint with both Window AC and Split AC
producing genuinely separate records.

## No mock data
Every value in the fixed UI traces to a real API response — confirmed
via both source inspection and live curl verification this sprint.

## Verdict
API integration: **real**, no new endpoints needed — the fix was
entirely about the frontend finally using parameters the API already
supported.
