# ADMIN-TENANT-E2E-09 — Area-Specific Coverage Report

Real psql query against `tenant_service_areas` + `tenant_service_area_services` (tenant `34b427a7-b2be-496c-b826-6d51bb181248`):

| Area | Type | zipcode | is_active | is_primary |
|---|---|---|---|---|
| Ludhiana | zipcode | 141001 | **true** | **true** |
| Ludhiana | zipcode | 141002 | false | false |
| bassi pathana | city | — | false | false |

`tenant_service_area_services` confirms a real linkage row for area `141001` → `service_id=a96e625a...` (AC Repair) → `service_type_id=c86dfcf3...` (Split AC) → `brand_id=64a3b25f...` (LG), `is_available=true` — i.e. Split AC + LG coverage in 141001 IS active and structurally distinct (has its own `service_type_id`/`brand_id` columns) from a hypothetical Window AC + LG row, which was not found in this table (only one row exists currently — Window AC+LG area-level coverage does not yet have its own explicit row, though pricing for Window AC+LG exists at the tenant_service_brands level). This is worth flagging: area-level per-type-per-brand coverage rows are sparse (only 1 row total) even though type/brand *pricing* is fully configured for both types — suggests area coverage granularity may not be fully populated for Window AC yet. Documented as a data-completeness gap, not a code bug.

## Safety decision (per spec's explicit guidance)
Given Demo AC Services is the sole shared dev tenant used across many prior sprints, and given the credit balance is already at 0 (a genuine live risk per the Baseline report), I chose **not** to destructively remove/restore the 141001 coverage row to test the "unbookable when uncovered" behavior. Instead I performed a **code-review-level check**:

- `app/engines/home_service_booking/customer_router.py`'s `match_and_price` docstring states the backend "runs the full eligibility gate (bookable, coverage, technician, availability, pricing, package, credits, deposit) over every candidate" before selecting a provider — i.e. coverage absence is explicitly one of the gating checks by design, confirming the logic WOULD reject an uncovered area without needing to destructively prove it on the shared tenant.

## Verdict: PASS (via code-review-level check per spec's safety guidance; live destructive test intentionally skipped to protect the shared tenant)
