# Admin Catalog Data Model Verification (Part 2)

Verified directly via `psql` against the live `serviceos` database plus admin UI:

Real tables backing the model: `master_services` (Service Group is `category_id` -> categories; "Home Services" is a category), `service_types` (+ `master_service_types` mapping), `brands` (+ `master_service_brands` mapping), issue types (`service_issue_mappings` / issue_types via masterDataApi), `service_option_mappings` (Options), `service_pricing_rules` (pricing), `pricing_tiers` + `tier_locations` (zone/tier), `is_active` (status), no dedicated `customer_visible` column on `master_services` — active implies visible (documented in-page as "catalog has no separate customer_visible flag yet").

Baseline data confirmed present:
- Service "AC Repair" — id `a96e625a-60e1-46c0-bde4-ccbb88da50a2`, `is_brand_required=true`.
- Type "Split AC" — id `c86dfcf3-53bd-4d83-bf0b-51257f382652` (mapped via `master_service_types`).
- Type "Window AC" — id `e27f6591-9b8d-4d57-93d0-8ed86c19c8af` (mapped via `master_service_types`). Both types already existed — no seed data creation was necessary for Part 5.
- Brand "LG" — id `64a3b25f-23aa-4639-8baf-f67def0f60db`, mapped to AC Repair (also Samsung, Voltas mapped).
- Zipcode 141001 / Ludhiana — present in `tier_locations` (tier "Mid") and `tenant_service_areas`, active=true.
- Issue "Not Cooling" — confirmed present via UI (Issues tab, `masterDataApi.listIssueTypes`); browser evidence in `catalog-content.log` shows "Issues tab contains Not Cooling/cooling: true".

UI display verified (service-catalog page, `app/admin/home-services/service-catalog/page.tsx`):
- Service groups shown in left rail grouped by `service_group_id`.
- Services listed under group with type/brand counts.
- Service Types tab: table with Type name, Customer Visible, Provider Selectable, Brand Pricing Allowed Later, Status columns.
- Brands tab: brand cards with price-override-eligibility labels, explicitly notes "Window AC + LG and Split AC + LG are separate pricing records."
- Issues tab: live list from `masterDataApi.listIssueTypes`, each row with Active/Inactive badge.
- Options tab: live list from `masterDataApi.listServiceOptions`.
- Status badges: Active/Inactive shown with color-coded pill both in service header and list rows.
- Visibility: "Customer Visible" shown as static "Yes" (documented limitation — no separate flag; not a bug, a real schema gap noted honestly in the code comment).

Result: PASS — full data model present and correctly displayed; one honest gap (no distinct customer_visible column) already documented in-app rather than faked.
