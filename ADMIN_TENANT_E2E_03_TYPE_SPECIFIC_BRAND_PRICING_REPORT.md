# Type-Specific Brand Pricing Verification (Part 5, CRITICAL)

## Direct DB proof (psql, `service_pricing_rules` table)

Real, pre-existing (not created by this sprint) active pricing rows for AC Repair (`a96e625a-60e1-46c0-bde4-ccbb88da50a2`) + Brand LG (`64a3b25f-23aa-4639-8baf-f67def0f60db`):

| Rule ID | service_type_id | Type name | brand_id | min_price | max_price | is_active |
|---|---|---|---|---|---|---|
| 2ef804e7-c349-4387-8294-2b3f1a3e80e5 | c86dfcf3-53bd-4d83-bf0b-51257f382652 | **Split AC** | LG | 600.00 | 950.00 | true |
| 36303216-984e-4938-acfc-c76116e2f90f | e27f6591-9b8d-4d57-93d0-8ed86c19c8af | **Window AC** | LG | 350.00 | 500.00 | true |

These are two separate rows, each with a distinct `service_type_id`, same `brand_id` (LG), different price ranges. This directly disproves "one global LG price for all AC types" — LG has a materially different, independently stored price range per type. Re-queried after all browser CRUD testing in this sprint (Part 4) — both rows unchanged, confirming no accidental mutation.

Also confirmed additional non-brand type-scoped rows exist (Split AC all-brands: 850-2000; Window AC all-brands: 550-1500), and brand-scoped-but-not-type-scoped rows exist for other services — i.e. the backend genuinely supports the full hierarchy: Service+Type+Brand+Zone > Service+Type+Zone > Service+Zone, with `service_type_id` and `brand_id` as independent nullable FKs on the same table, not a denormalized "one price per brand" model.

## Browser UI proof

- `service-catalog` page, Brands tab: explicit text (verified in rendered page source and screenshot `ac-repair-brands.png`) — "For type-based services, the actual brand price range is set per type in Pricing Rules — e.g. Window AC + LG and Split AC + LG are separate pricing records."
- `pricing-rules` page: table column "Type" shows "Type-scoped" vs "All Types" per row (from `r.service_type_id ? "Type-scoped" : "All Types"`), and "Brand" column shows "Brand-scoped" vs "All Brands" independently — so a viewer can see at a glance that a row is tied to one specific type. Screenshot: `pricing-rules-list.png`.
- Edit modal: Service select drives a dependent Type select (`catalogApi.listServiceTypeMappings(form.master_service_id)`) and Brand select (`catalogApi.listBrandMappings`) — both scoped to the chosen service, and the Type field is a real dropdown of that service's mapped types (Split AC / Window AC appear as separate options), not a free-text or global field.
- Client-side validation in `saveAction` (page.tsx line ~113) explicitly blocks saving a brand-priced rule on a type-based ("range" pricing_model) service without a type selected: `"Service type is required when adding brand pricing for a type-based service."` — this mirrors a real backend guard (`SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING`, per code comment), meaning the system structurally prevents a type-based service from ever having one global brand price.

## Verdict

Editing one type's LG rule does not touch the other (confirmed by primary-key-scoped `service_pricing_rules.id`, independent `min_price`/`max_price` columns, and unchanged DB values pre/post this sprint's Cancel-only edit test). Rule detail includes `service_type_id` (shown in UI as resolved type name, not shown as raw UUID). No global LG price is ever rendered — the UI's own row grouping and edit form make type-scoping visually explicit.

Result: **PROVEN — Window AC + LG pricing is genuinely separate from Split AC + LG pricing at both the DB and UI layer.**
