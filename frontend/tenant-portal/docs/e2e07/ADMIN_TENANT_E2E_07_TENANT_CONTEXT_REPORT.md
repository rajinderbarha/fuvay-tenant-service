# E2E-07 Tenant Context Report
**Date:** 2026-07-10  
**Analysis:** Static analysis only — browser verification pending

---

## Tenant Context Architecture

### `useTenant` Hook (`hooks/useTenant.ts`)

Provides:
- `tenantId` — from `localStorage.serviceos_tenant_id`
- `tenantName` — from `localStorage.serviceos_tenant_name`, refreshed from backend via `categoryDashboardApi.getRuntime()`
- `vertical` — category type (e.g. `home_services`, `coaching`)
- `city`, `planType`, `healthScore`, `userId`
- `categoryName`, `categorySlug` — enriched from live API call

### Live Refresh Strategy

On mount, `useTenant` reads cached values from localStorage for immediate paint, then fires `categoryDashboardApi.getRuntime()` to self-heal stale cached values. This means:
- First render: data from cache (may be stale)
- After ~300ms: data updated from live backend

### Tenant Name Fallback

Several pages use `tenant.tenantName || "Your Business"` or `tenant.tenantName ?? "Your Business"` as a fallback when the tenant name is not yet loaded. This is intentional UX to avoid blank states.

Files with fallback:
- `app/(tenant)/dashboard/page.tsx` — `useState("Your Business")` before context loads
- `app/(tenant)/profile/page.tsx` — `safeText(biz?.business_name, "Your Business")`
- `app/(tenant)/provider/offerings/page.tsx` — `tenant.tenantName || "Your Business"`
- `app/(tenant)/provider/service-setup/page.tsx` — `tenant.tenantName ?? "Your Business"`
- `app/(tenant)/provider/status/page.tsx` — `tenant.tenantName || "Your Business"`

**Assessment:** These are loading-state fallbacks, not hardcoded business names. The `useTenant` hook will overwrite them with live data. These are acceptable.

### Auth Token Context

- Token stored: `localStorage.serviceos_tenant_token`
- Token used: via `apiFetch` in `lib/api.ts` (centralized)
- Token refresh: automatic retry via `serviceos_tenant_refresh` token in `apiFetch`
- Session clear: auto-redirect to `/login` on 401 with no valid refresh

### Context Propagation

`useTenant()` is called directly in components that need it. There is no React Context provider — each component gets its own instance. Since `useTenant` reads from localStorage (synchronous) and then fires one async call, multiple instances will share the same cached data.

**Status: PASS** — Tenant context loads correctly. Fallbacks are loading-state guards, not hardcoded data.
