# Tenant Home Services Service Setup Wizard — UI Report

## Structure delivered

1. Service catalog page (`/tenant/setup/services`) — title, subtitle, info
   banner (Customer Price Options / Auto Low-Mid-High disclosure), grid of
   real service cards (icon, name, pricing model, requirement badges,
   Set Up/Manage CTA with Enabled badge)
2. "Your Services" list below the catalog — real enabled services with
   Draft/Published status and bookable indicator
3. Wizard left panel — "← All services" back link, selected service name +
   group + pricing-model badge, 4-step indicator (Service/Types/Pricing/
   Review) with green-check completed steps and blue current-step
   highlight (Types step is hidden entirely when the service has no
   admin-mapped types, per the ticket's "skip this step" rule)
4. Step 1 (Service Overview) — title, subtitle, info banner exactly
   matching the ticket text, 3 summary cards (Pricing Model, Brands,
   Types), Next button
5. Step 2 (Select Types) — title, subtitle, checkbox type cards with
   selected-state styling, "select at least one" validation
6. Step 3 (Pricing) — per-type tabs (only selected types), Working Range
   display, Your Minimum/Maximum Price inputs, Save button, live Customer
   Price Options Preview (Low/Mid/High chips) sourced from the real
   backend response after each save
7. Step 3B (Brand Pricing) — Same for all / Override some toggle, brand
   rows (checkbox reflecting override state, initials avatar, name,
   routing-only disclosure, Your Min/Max, live preview), inline edit form
8. Step 4 (Review & Publish) — full pricing matrix table (Type/Item,
   Brand/Variant, Your Min, Your Max, Customer Sees, Note) with indented
   `↳` brand-override rows, price-resolution banner, missing-service-area
   warning with "Add Service Area →" link, Back/Save Draft/Publish actions
9. Enabled services list — integrated into the catalog page (see #2)

## Design notes

Consistent with every other tenant-portal page built this session: light/
neutral enterprise theme (`--surface`, `--text-primary`), clean cards, no
technical overload — the wizard shows only "Your Minimum Price"/"Your
Maximum Price" plain-language labels, never raw enum values or internal
field names. The gradient primary button and clear step-completion
checkmarks match the "clear selected states" requirement.

## Real data, no fabrication

Every price shown (admin floor/ceiling, tenant range, Low/Mid/High) is
live-fetched from the real backend after the Admin Home Services Catalog
Console sprint's floor/ceiling data. Types/brands with no admin range
configured yet show "Not configured" honestly rather than a fake default.
