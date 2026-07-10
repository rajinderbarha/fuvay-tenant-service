# Tenant Home Services Service Setup Wizard — UI Report

## Route

`/tenant/setup/services`
File: `frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx`

## Page Structure

### 1. Scope Guard
- Uses `isHomeServicesTenant(tenant)` from `verticalGuard.ts`
- Shows loading skeleton while `useTenant()` resolves
- Non-Home-Services tenants see: "This setup wizard is available only for Home Services. This vertical uses a different setup model."

### 2. Service Catalog Page
**Header:** "Service Setup"
**Subtitle:** "Choose the services you provide, select supported types and brands, and set your provider price ranges."

**Stats row (3 cards):**
- Available Services
- Published
- Draft / Setup

**Service cards (admin-catalog-driven, no free-text):**
- Service icon + name + pricing model + job type
- Admin price range shown
- Badges: "Brand pricing", "Types required"
- CTA: "Set Up" / "Continue Setup" / "Manage"
- Status badge: "Published" / "Draft"

### 3. Wizard Modal (ServiceSetupWizard)
Opens on card click. Contains:

**Left panel (200px):**
- ← All services (back button)
- Service name + pricing model
- Step progress list with checkmarks

**Right content:**
5 wizard steps (brands step hidden if service has no brands)

### 4. Step 1 — Overview
- Title: "Set up {ServiceName}"
- Subtitle: "Review what you're configuring and how pricing works for this service."
- Info banner: price resolution explanation
- Info cards: Pricing Model, Types count, Brands count, Service Areas
- Service areas shows warning if none configured
- CTA: "Next: Select Types" or "Next: Set Pricing"

### 5. Step 2 — Types
- Title: "Which types do you service?"
- Multi-select card list with checkboxes
- Required types are auto-checked, not removable
- "Brand pricing available" label per type
- At-least-one validation before advancing

### 6. Step 3 — Pricing (per-type)
- Title: "Set your price range per type"
- One `TypePricingCard` per selected type:
  - Admin working range display
  - Visual range bar (CSS)
  - Min Price (₹) input — validated against `adminFloor`
  - Max Price (₹) input — validated against `adminCeiling`
  - "Preview" button → calls `homeServicesSetupApi.pricePreview`
  - `PricePreviewBand` showing Low / Mid / High + platform fee

### 7. Step 4 — Brands (conditional)
- Title: "Brand pricing"
- Toggle: "Same for all" / "Override some"
- "Same for all": info banner, all brands use type range
- "Override some": `BrandOverrideRow` per brand with `canOverride`
  - Checkbox to enable override
  - Min/Max inputs
  - Live preview

### 8. Step 5 — Review & Publish
- Title: "Review & publish"
- Full pricing matrix table: Type / Item · Brand / Variant · Your Min · Your Max · Customer Sees · Note
- Brand override rows indented (↳)
- Price resolution banner
- Warning if no service area (Publish disabled)
- Actions: Back · Save Draft · Publish Service

## Enabled Services List
- Shows only "published" + "active" services
- Columns: Service · Status · Setup Status · Actions (Manage / Disable)
- "Manage" re-opens the wizard

## Design
- `var(--brand)`, `var(--surface)`, `var(--border)`, `var(--text-primary/secondary/tertiary)` CSS vars throughout
- CSS vars for danger/warning/success/info feedback states
- `safeCur()`, `safeText()`, `safeNum()` — no raw null/undefined displayed
- `fontVariantNumeric: "tabular-nums"` on price columns
