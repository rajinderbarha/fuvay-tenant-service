# Customer Price Experience — API Schema Report

## Request (unchanged shape, renamed fields)

```json
{
  "service_name": "AC Repair",
  "admin_min_price": 300,
  "admin_max_price": 500,
  "admin_base_price": 400,
  "selected_min_price": 350,
  "selected_max_price": 420,
  "platform_fee_percent": 10
}
```

`selected_min_price`/`selected_max_price` replace the old, confusing
`customer_min_price`/`customer_max_price` field names (admin sets the
*allowed* range; the tenant/provider *selects* a range inside it — "customer"
was never the right actor name for these two fields). The backend still
accepts the old field names as a fallback (`body.get("selected_min_price",
body.get("customer_min_price"))`) for any external caller not yet updated.

## Response — matches the ticket's required shape exactly

```json
{
  "admin_min_price": 300,
  "admin_max_price": 500,
  "admin_base_price": 400,
  "selected_min_price": 350,
  "selected_max_price": 420,
  "platform_fee_percent": 10.0,
  "platform_fee_on_min": 35.0,
  "platform_fee_on_max": 42.0,
  "customer_low_price": 385.0,
  "customer_mid_price": 425.0,
  "customer_high_price": 462.0,
  "allowed_offer_min": 385.0,
  "allowed_offer_max": 462.0,
  "payment_mode": "customer_pays_provider_directly",

  "customer_min_price": 350,
  "customer_max_price": 420,
  "low_price": 385.0,
  "mid_price": 425.0,
  "high_price": 462.0
}
```

The last 5 fields (`customer_min_price`, `customer_max_price`,
`low_price`, `mid_price`, `high_price`) are **backward-compatible
aliases** — kept so any external tooling/script still reading the old
field names doesn't break, per the ticket's explicit allowance ("Backward
compatibility aliases are allowed, but UI must use the corrected
fields"). The frontend page reads only the corrected fields
(`customer_low_price`, `customer_mid_price`, `customer_high_price`,
`platform_fee_on_min`, `platform_fee_on_max`, `selected_min_price`,
`selected_max_price`).

## Validation errors (RFC 7807 problem+json, all include request_id)

| Condition | error_code | HTTP |
|---|---|---|
| Admin Min > Admin Max | `INVALID_ADMIN_RANGE` | 422 |
| Selected Min < Admin Min | `SELECTED_RANGE_BELOW_ADMIN_MIN` | 422 |
| Selected Max > Admin Max | `SELECTED_RANGE_ABOVE_ADMIN_MAX` | 422 |
| Selected Min > Selected Max | `INVALID_PRICE_RANGE` | 422 |
| Platform Fee < 0 | `INVALID_PLATFORM_FEE` | 422 |

## TypeScript types updated

`frontend/super-admin/lib/api.ts`:
- `PriceExperiencePreviewResult` — added `selected_min_price`,
  `selected_max_price`, `platform_fee_on_min`, `platform_fee_on_max`,
  `customer_low_price`, `customer_mid_price`, `customer_high_price`;
  kept `customer_min_price`/`customer_max_price` as optional
  backward-compat aliases.
- `autoPriceOptionsApi.previewPriceExperience` request type — renamed
  `customer_min_price`/`customer_max_price` params to
  `selected_min_price`/`selected_max_price` (required fields, matching
  what the endpoint now expects as primary input).
