# Automatic Price Options — API Mapping Report

| Ticket suggestion | Real endpoint |
|---|---|
| `POST /v1/customer/home-services/match-and-price` | Already exists (Provider Matching sprint): `POST /v1/customer/home-services/booking-drafts/{draft_id}/match-and-price` — unchanged, reused as-is |
| `POST /v1/customer/home-services/confirm-price-choice` | Already exists: `.../booking-drafts/{draft_id}/confirm-price-choice` — unchanged, reused as-is |
| `POST /v1/admin/home-services/price-experience/preview` | **New**, matches exactly — `app/engines/admin_catalog/auto_price_options_router.py::admin_price_experience_preview` |
| `POST /v1/admin/home-services/matching/diagnostics` | **New**, matches exactly — `::admin_matching_diagnostics` |
| `GET /v1/tenant/home-services/customer-price-preview` | **New**, matches exactly — `::tenant_customer_price_preview` |
| `GET /v1/tenant/home-services/matching-readiness` | **New**, matches exactly — `::tenant_matching_readiness` |
| (not in ticket list) `GET /v1/admin/home-services/config` | **New** — exposes the 3 feature flags + scope, used to drive the admin hero card's live status display |

## Implementation notes

All 4 ticket-named endpoints were built exactly as specified (route paths
match verbatim) rather than needing a mapping workaround — the only addition
beyond the ticket's list is the `/config` endpoint, needed to make the admin
hero card's "Automatic Price Options: Enabled / Manual Bargain Rules:
Disabled" status live rather than hardcoded text.

All 4 new endpoints are thin wrappers around already-certified pure engines
from prior sprints (`bargain_engine.evaluate_customer_bargain`,
`matching_engine.compute_price_tiers`/`select_best_provider`/
`get_area_market_comparison`) — no new pricing or matching logic was
invented; this sprint only added the automatic-flow entry points and
UI on top of that certified engine.
