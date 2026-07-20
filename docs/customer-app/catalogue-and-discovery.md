# Customer App — Catalogue and Discovery

## Module Model

Not implemented this sprint (no backend contract — see backend-contract-
audit). CUSTOMER-L5-01's `remote-config` `modules[]` type exists but has no
live categories/services mapped to it yet.

## Category Model

`features/home/api/home-api-types.ts#CategorySummaryDto` (raw) →
`features/home/domain/category-schema.ts#ValidatedCategorySummary`
(runtime-validated) → `features/home/domain/discovery-composer.ts#HomeCategoryItem`
(app-facing shape, only the fields the UI actually needs).

## Service Summary Model

`OfferingSummaryDto`/`offeringSummarySchema` are defined and validated
(`home-api.ts#listOfferings`, `category-schema.ts#offeringSummarySchema`)
but **not yet called from any screen** — no service-detail destination
exists to link to (CUSTOMER-L5-04). Kept as a ready-to-use, tested layer
rather than dead code with no test coverage.

## Campaign Model

Not implemented — no backend contract.

## Endpoint Contracts

See `CUSTOMER-L5-03-backend-contract-audit.md`.

## Validation Rules

`category-schema.ts`: name/description length caps (200/2000 chars),
`available_offering_count` must be non-negative, icon/banner URLs must be
`https://` or a relative path (rejects `javascript:`/`data:`/arbitrary
schemes). Invalid items are dropped individually, never fail the whole
list (`parseCategoryList`).

## Availability Rules

Enforced server-side (`is_active && is_customer_visible` filter in
`service.py#list_customer_categories`) — the client does not re-implement
an availability check, since the backend contract gives no additional
fields (e.g. `availability_window`) to evaluate client-side.

## Route Mapping

No category-detail route exists yet — `CategoryCard`'s press handler does
not navigate (see `home-architecture.md`). Once CUSTOMER-L5-04 adds a
`serviceDetails`/category-detail screen, the mapping will go through the
existing compiled `route-registry.ts` (CUSTOMER-L5-01), never a raw
backend-provided route string.

## Image Policy

`CategoryCard.tsx#isTrustedImageUrl` only renders `icon_url` when it starts
with `https://`; anything else (including a relative path, which the
schema accepts for future flexibility but the card doesn't yet know how to
resolve into an absolute URL) falls back to a generic `AppIcon`. Image
load failure (`onError`) also falls back to the icon — no broken-image
placeholder is ever shown.

## Icon Policy

No semantic icon-identifier mapping exists yet (the backend does not
return one — `icon_url` is an image URL, not a semantic key like `"ac"`).
`CategoryCard` always uses a single generic `AppIcon name="home"` fallback
rather than attempting to map category names/slugs to specific icons —
guessing an icon from a category name would be exactly the kind of
"dynamically import arbitrary icons from a backend string" pattern the
sprint brief prohibits, and the current backend contract doesn't provide a
compiled-icon-safe field to do this properly. Tracked in `known-gaps.md`.
