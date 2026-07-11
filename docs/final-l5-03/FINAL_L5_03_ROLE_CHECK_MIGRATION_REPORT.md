# FINAL-L5-03 — Role Check Migration Report

## Change
`tenant-portal/lib/api.ts`: added
```ts
export function isTenantOwnerRole(role: string | null | undefined): boolean {
  return role === "tenant_owner" || role === undefined;
}
```
right next to the existing `isTenantReadOnly()`.

## Migrated call sites
- `app/(tenant)/provider/status/page.tsx:85` — `const isTenantOwner = isTenantOwnerRole(meApi.data?.role);`
- `app/(tenant)/provider/offerings/page.tsx:478` — same

## Behavior preservation proof
The extracted function is a byte-for-byte copy of the original inline expression (`role === "tenant_owner" || role === undefined`) — no semantic change, purely a duplication removal. Verified via:
- `npx tsc --noEmit`: 0 errors.
- Real Chromium regression: `provider/offerings` page loads and renders correctly (`final-l5-03-cross-app-regression.spec.ts`, Tenant Portal test).

## Result
Duplication eliminated, zero behavior change, verified.
