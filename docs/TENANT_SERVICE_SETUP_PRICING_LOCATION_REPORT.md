# Tenant Service Setup — Pricing Location Report

## Pricing Now Lives In: Service Setup

Route: `/provider/service-setup`
File: `frontend/tenant-portal/app/(tenant)/provider/service-setup/page.tsx`

## Wizard Steps (Updated)

| Step | Key | Description |
|------|-----|-------------|
| 1 | `service` | Select service (platform catalog) |
| 2 | `type` | Select service types |
| 3 | `brand` | Brand overrides |
| 4 | `issues` | Common customer issues (informational) |
| 5 | `options` | Add-on options |
| 6 | `areas` | Service areas coverage |
| 7 | `technician` | Assign technician |
| **8** | **`pricing`** | **Provider price range + Low/Mid/High preview** |
| 9 | `availability` | Availability rules |
| 10 | `review` | Review & publish |

## Pricing Step (Step 8) Implementation

**Provider Price Range:**
- Min Price (₹) input → `providerMinPrice` state → saved as `provider_price_override`
- Max Price (₹) input → `providerMaxPrice` state

**Customer Low/Mid/High Preview:**
- Button: "Preview Customer Options"
- Calls `homeServicesSetupApi.pricePreview({ tenant_min_price, tenant_max_price })`
- Returns `HsPricePreview` with `low_price`, `mid_price`, `high_price`, `platform_fee_percent`, `payment_mode`
- Displayed as 3-column card grid

**Business Rule Enforced:**
> "Customer pays the provider directly on-site — platform does not collect the service payment."

## APIs Used

| Action | API | Endpoint |
|--------|-----|----------|
| Price preview | `homeServicesSetupApi.pricePreview` | `POST /v1/tenant/catalog/price-options/preview` |
| Save with price | `providerOfferingsApi.enable/update` | `POST/PUT /v1/provider/offerings/enabled` with `provider_price_override` |

## Hard Gate Satisfied

Tenant has a working place to set provider price range: Service Setup step 8.
