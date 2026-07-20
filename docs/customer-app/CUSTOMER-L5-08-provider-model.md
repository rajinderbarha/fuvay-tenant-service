# CUSTOMER-L5-08 — Provider Model

## Provider = Tenant (confirmed)

There is no separate `Provider`/`ProviderCompany`/`ProviderZone` model
anywhere in the backend. The customer-facing "provider" in this flow is
always a row from `tenants` (`app/engines/tenant_engine/models.py:11`,
canonical `Tenant` SQLAlchemy model). `matching_engine.py`'s candidate pool
query (lines 304-326) selects directly from `Tenant` joined to
`TenantServiceArea`; `CandidateSignals.tenant_id` (line ~92) is
`str(Tenant.id)`.

This matches every other sprint's finding that this backend has no
dedicated "provider" bounded context distinct from tenant/organization
identity — a tenant IS a provider in the `home_services` vertical, full
stop.

## Real `Tenant` fields relevant to matching (confirmed columns)

```python
health_score: Numeric(5,2), default=100.0      # internal only, never returned to customer
health_band: String(20), default="gold"        # internal only, never returned to customer
rating_average: Numeric(3,2), default=0.0       # returned to customer as `rating`
verification_status: String                     # exists on the table, NOT read by the badge computation
status: str                                      # must be "active" to be a matching candidate
vertical: str                                    # must be "home_services"
suspended_at: datetime | null                    # must be null to be a matching candidate
```

## Supporting tables consulted during matching (never exposed directly)

| Table | Role |
|---|---|
| `provider_visibility_statuses` | Precomputed `is_bookable` + `bookability_blockers` — the single canonical bookability gate (folds in technician/availability/package/wallet/deposit signals per an explicit in-code consolidation comment). |
| `tenant_service_areas` | Zipcode/city coverage. |
| `tenant_service_area_services` | Per-area service/type/brand coverage. |
| `service_pricing_rules` | Whether a valid price rule exists for the requested `master_service_id`. |
| `provider_team_members` | Queried only as an aggregate active-headcount count for the internal capacity score — never to select or expose an individual technician. |
| `BargainRule` (customer_min_price/customer_max_price) | Drives `PRICE_OPTIONS_UNAVAILABLE` if missing — pricing scope, not rendered by this sprint. |

## Customer-Safe Provider Object (the only provider shape this sprint ever sees)

```json
{
  "tenant_id": "…",
  "provider_name": "…",
  "public_badges": ["Verified"],
  "rating": 4.7,
  "customer_visible_reason": "Best matched provider based on service coverage, availability, quality, and completion history."
}
```

Five fields. Every field this sprint's UI shows is one of these five —
nothing else is invented to make the preview screen feel more complete than
the real backend response actually is.

## What must never be exposed to the customer (confirmed internal-only)

- `internal_score` / `internal_score_breakdown` (8 weighted sub-scores) — never returned to the customer router at all (`reveal_internal_score=False` hardcoded).
- `health_score` / `health_band` — plain `Tenant` columns, never serialized into any customer-facing response in this flow.
- `excluded_providers` / candidate pool / `candidate_count` — only appears inside the no-match failure path's *internal* return dict (`select_best_provider`'s return value), never forwarded past `match_provider_and_price`'s exception into the actual HTTP error body the customer receives.
- Distance, ETA, technician identity — do not exist in this data model at this stage at all (see contract-matrix.md).

## Badge Semantics (server-computed, closed set)

| Badge string | Real trigger |
|---|---|
| `"Verified"` | Always present for any eligible match — **hardcoded unconditionally**, does not check `Tenant.verification_status`. Documented as a backend data-integrity concern in known-gaps.md. |
| `"Highly Rated"` | `rating_average >= 4.5` |
| `"High Completion"` | `health_score >= 90` (an internal score the customer never otherwise sees, but this one derived threshold-badge does surface indirectly). |

This client's `badge-label-mapping.ts` maps exactly these three known
literal strings to localized labels; anything else fails safe (renders the
raw string, logs `provider_badge_unmapped` at `warn`) rather than throwing
or hiding the badge silently.
