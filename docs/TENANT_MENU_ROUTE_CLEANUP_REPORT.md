# Tenant Menu Route Cleanup Report

## Old Routes — Status

| Old Route | Behavior After Cleanup |
|-----------|----------------------|
| `/provider/pricing` | Shows deprecated message + auto-redirect to `/provider/service-setup` after 4s |
| `/provider/customer-price-preview` | Shows deprecated message + auto-redirect to `/provider/service-setup` after 4s |
| `/tenant/setup/services` | Shows deprecated message + auto-redirect to `/provider/service-setup` after 4s |
| `/provider/service-coverage` | Page still exists but removed from sidebar nav |
| `/provider/services` | Redirected via nav-config path map to `provider-service-setup` |

## Deprecated Page Content

All three deprecated pages show:

> **This setup page has moved.**
> Provider pricing is now configured inside Service Setup.
> [Open Service Setup →]

Auto-redirect fires after 4 seconds via `useEffect` + `router.replace`.

## nav-config.ts Path Mapping

`pricing` path segment now maps to `provider-service-setup` nav ID (was `provider-pricing`).
`service-setup` path segment also maps to `provider-service-setup`.

## Routes Not Handled (No Existing Pages)

| Route | Status |
|-------|--------|
| `/tenant/bargain-settings` | No page existed; no action needed |
| `/tenant/bargain-rules` | No page existed; no action needed |
| `/tenant/pricing` | No page existed; no action needed |
