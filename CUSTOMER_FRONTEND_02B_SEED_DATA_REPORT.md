# CUSTOMER-FRONTEND-02B — Part 2: Deterministic Seed Data Report

## Baseline verified via direct SQL + real APIs

| Item | Status | Evidence |
|---|---|---|
| Customer One (customer@serviceos.in) | Exists, active | Login succeeded, JWT issued |
| Customer Two (customer2@serviceos.in) | Already existed in DB (`SELECT email,role FROM users WHERE role='customer'`) | Login succeeded, JWT issued |
| Tenant "Demo AC Services" | Exists, status=active | `SELECT id,business_name,status FROM tenants` |
| Zipcode 141001 service area | Active + primary | `tenant_service_areas` row `d1e94fb5-...` coverage_type=zipcode, is_active=t, is_primary=t |
| Availability rules | 7 rows, all `is_active=t`, days 1-6 covered 09:00-18/19:00 | `provider_availability_rules` |
| Usage credit balance | 3958.00 | `tenant_billing.credit_balance` |
| Security deposit | Paid, 5000.00 | `tenant_billing.security_deposit_paid=t` |
| Provider bookability | is_visible=t, is_bookable=t, blockers=[] | `provider_visibility_statuses` |

## Gap found and fixed
The HARD RULE (real bookable match for AC Repair + Split AC + LG + 141001) initially failed at the catalog level, not the bookability level:

- `brands` table: LG brand (`64a3b25f-23aa-4639-8baf-f67def0f60db`) had `category_id = NULL`.
- `master_issue_types` table: "AC Not Cooling" (`5df141b1-a879-4008-98af-f9643285fe05`) had `category_id = NULL` and `master_service_id = NULL`.
- Both `/v1/catalog/master/brands?category_id=...` and `/v1/catalog/master/issue-types?category_id=...` filter by exact column equality (verified in `app/engines/admin_catalog/service.py::list_brands` / `list_issue_types`), so both endpoints returned empty lists for the Home Services category (`0888d283-9a52-4d7b-8612-9f47fa8357a1`) even though the rows existed globally.

### Attempted real-endpoint fix first
Tried `PUT /v1/admin/brands/{id}` and `PUT /v1/admin/issue-types/{id}` with `category_id` in the body (super_admin JWT). Both returned `success:true` but the response showed `category_id` still `null` — inspection of `app/engines/brands/service.py::update_brand` confirmed the whitelist of updatable fields (`display_name, description, website_url, country_of_origin, display_order, logo_url, code, is_global, alias_names, metadata`) does NOT include `category_id`. No real endpoint exists to set `category_id` on a brand or issue type post-creation.

### Fallback: direct SQL (documented, as permitted by spec)
```sql
UPDATE brands SET category_id='0888d283-9a52-4d7b-8612-9f47fa8357a1'
  WHERE id='64a3b25f-23aa-4639-8baf-f67def0f60db';
UPDATE master_issue_types
  SET category_id='0888d283-9a52-4d7b-8612-9f47fa8357a1',
      master_service_id='a96e625a-60e1-46c0-bde4-ccbb88da50a2'
  WHERE id='5df141b1-a879-4008-98af-f9643285fe05';
```
Re-verified via the real customer-facing endpoints: `brands?category_id=...` now returns `["LG"]`, `issue-types?category_id=...` now returns `["AC Not Cooling"]`.

## Pricing rule confirmed present
`service_pricing_rules` already had an ACTIVE row for `master_service_id=ac_repair, service_type_id=Split AC (c86dfcf3...), brand_id=LG (64a3b25f...)`: min_price=600, max_price=950. No SQL change needed there — this is what produced the real 770/850/935 (Low/Mid/High incl. platform fee) numbers seen in Part 3.

## Result
Baseline is now fully bookable end-to-end for AC Repair + Split AC + LG + Not Cooling + 141001, using only the pre-existing pricing rule and two targeted SQL backfills for orphaned category_id/master_service_id FKs (a data-integrity gap, not a code bug — no endpoint regressed).

STATUS: SEED DATA READY.
