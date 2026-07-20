# Frontend Exposure Audit — Workstream 13

## Page found
`app/(tenant)/catalog/page.tsx` (tenant-portal) — the "Admin Catalog"
tab calls `masterCatalogApi.listAvailable/enable/disable`, which hit
`/v1/tenant/catalog/available-services`, `/enable-service`,
`/disable-service` respectively.

## Finding: no role/access-scope gate on the Enable/Disable button (fixed this slice)
Previously the "Enable for my business"/"Disable" button rendered
unconditionally for any authenticated tenant user viewing the page — no
`canEnable`/`canDisable` boolean existed at all (unlike Slice 2F-7's
`service-areas` page, which at least had a hardcoded-`true` boolean to
correct; this page had no gate whatsoever).

## Fix applied (minimal, reusing existing helpers)
```tsx
const canToggle = isTenantOwnerRole(getUserRole()) && !isTenantReadOnly();
...
{canToggle && (
  <Btn ...>{svc.is_enabled ? "Disable" : "Enable for my business"}</Btn>
)}
```
Uses the same pre-existing helpers reused in Slice 2F-7
(`getUserRole()`, `isTenantOwnerRole()`, `isTenantReadOnly()`). No new
frontend authorization system, no visual redesign — the button is now
conditionally rendered (not shown-but-disabled), consistent with the
mission's preference ("prefer not rendering unauthorized actions rather
than showing permanently failing buttons").

## Requirements check (after the fix)

| Requirement | Status |
|---|---|
| Read-only users have no active catalog mutation controls | Fixed — `isTenantReadOnly()` gates `canToggle` |
| Technicians do not see business-wide catalog configuration controls | Fixed — `isTenantOwnerRole()` returns `false` for `"technician"` |
| Staff sees only explicitly delegated capabilities | Fixed — no delegated capability was proven for staff on this module (`TENANT_UPDATE` is `tenant_owner`-only), so staff now correctly sees no toggle either |
| Tenant owners see approved actions | Preserved |
| Platform catalog creation/edit actions do not appear in tenant portals | Confirmed — no platform-admin catalog route or control appears anywhere in `frontend/tenant-portal` |
| Disabled/unsupported capabilities are not shown as working | The "Custom Services" tab (`CustomCatalogSection`, a separate, unrelated `ServiceCatalogItem`-based feature) was not investigated — out of scope, a different backend module (`service_catalog`, not `admin_catalog`) |

## Other pages calling this module
`app/(tenant)/dashboard/page.tsx` and `app/(tenant)/provider/pricing/page.tsx`
also reference `masterCatalogApi` — not independently audited field-by-field
this slice (only the primary enable/disable surface was in scope for the
"minimal policy-alignment changes" instruction); no mutation button was
found in a cursory check of either page beyond read-only summary/listing
usage.

## Conclusion
One real, minimal frontend misalignment found and fixed. No visual
redesign performed — same layout, same component structure, only the
button's render condition changed.
