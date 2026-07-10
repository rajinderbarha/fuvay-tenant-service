# Tenant Home Services Setup — Scope Guard Report

## Guard Implementation

File: `frontend/tenant-portal/lib/verticalGuard.ts`
Function: `isHomeServicesTenant(context)`

Called in: `frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx`

```tsx
const tenant = useTenant();

if (tenant.loading) {
  return <TenantLayout><LoadingSkeleton /></TenantLayout>;
}

if (!isHomeServicesTenant(tenant)) {
  return (
    <TenantLayout>
      <div>
        "This setup wizard is available only for Home Services.
         This vertical uses a different setup model."
      </div>
    </TenantLayout>
  );
}
```

## Why useTenant() waits for loading

The `useTenant` hook has a self-healing refresh: it always re-fetches from the live backend
via `categoryDashboardApi.getRuntime()` even if a cached vertical exists. The `loading` state
is `false` only once this refresh resolves. We wait for `loading === false` before running the
guard to avoid falsely blocking tenants whose cached vertical was blank/stale.

## verticalGuard.ts Logic

`isHomeServicesTenant` checks all known vertical field names and normalizes case, spaces, and
hyphens before matching. This handles all known payload shapes:

- `context.vertical === "home_services"`
- `context.category_slug === "home-services"`  
- `context.tenant.category_type === "Home Service"`
- Any variation with underscores/hyphens/mixed case

## Services That See the Guard

**Blocked (non-Home Services):**
- IELTS / CA Services
- Restaurants / Food Ordering
- Real Estate
- Product Marketplace / Subscription / Listing / Menu+Cart categories

**Allowed:**
- AC Repair, AC Installation, AC Uninstallation
- Plumbing, Electrical
- Geyser Service, Appliance Repair
- Pest Control, Home Deep Cleaning

## Non-Home Services Message

> "This setup wizard is available only for Home Services. This vertical uses a different setup model."

This message is shown inside TenantLayout with the full navigation sidebar, so the tenant can
navigate to their correct setup pages.
