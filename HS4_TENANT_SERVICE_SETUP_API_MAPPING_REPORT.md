# HS4 — Tenant Service Setup API Mapping Report

## Real endpoints (confirmed via source + live curl this sprint)
| Ticket-suggested | Real |
|---|---|
| `GET /v1/tenant/home-services/catalog/available` | `GET /v1/tenant/catalog/home-services/available-services` (Home-Services-scoped, confirmed real from an earlier sprint's fix — the original `list_available_services` had no category filter at all) |
| `GET .../services/setup-draft` | `GET /v1/tenant/catalog/enabled-services` (lists all tenant services incl. `setup_status`) |
| `PUT .../services/{id}/pricing` | `PUT /v1/tenant/catalog/enabled-services/{id}/types/{type_id}/pricing` — real, live-verified this sprint (boundary rejection + success cases) |
| `PUT .../services/{id}/brand-pricing` | `PUT /v1/tenant/catalog/enabled-services/{id}/brands/{brand_id}/pricing` — real, type-scoped (fixed in prior sprint) |
| `POST .../services/publish` | `POST /v1/tenant/catalog/enabled-services/{id}/publish` — real, live-verified this sprint (200, `setup_status: "published"`) |
| `GET /v1/tenant/setup/checklist` | `GET /v1/provider/status` — real, but **found not to reflect a real publish** (see Publish Readiness report and Remaining Blockers — `/refresh` doesn't actually recompute `is_bookable`/blockers) |
| `GET /v1/tenant/home-services/readiness` | Same `/v1/provider/status` endpoint |
| `POST .../price-options/preview` | `POST /v1/tenant/catalog/price-options/preview` — real, pre-existing, certified in an earlier sprint |

## No mock data
All values in the wizard trace to real API responses — confirmed via
both source read and live curl calls against the real backend this
sprint.

## Verdict
API integration: **real**. One real bug found in the status/readiness
engine (see Remaining Blockers) — not a mock-data issue, a genuine
stale-computation bug.
