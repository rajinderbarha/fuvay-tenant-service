# Known Limitations — Slice 2F-7

1. **No canonical geography reference table exists platform-wide.**
   Country/State/District/City/PostalCode are unvalidated free-text
   fields. Not introduced or fixed this slice — a significant,
   platform-wide product/architecture decision, not scoped here.

2. **District is stored but functionally inert** — not a selectable
   `coverage_type`, never used as a matching key. Pre-existing, not
   changed.

3. **No tenant-catalog-enablement check on service mappings** —
   `add_service_mapping` validates against the canonical, platform-wide
   catalog only. Whether a tenant-specific enablement concept should
   exist is owned by `admin_catalog`, out of scope.

4. **No audit event for service-mapping mutations** (`add`/`update`/
   `delete_service_mapping`), unlike area-level mutations. Pre-existing,
   not fixed (design-choice, not mechanical).

5. **Frontend fix scoped narrowly.** Only the hardcoded
   `canCreate/canUpdate/canDelete/canSetPrimary` booleans on
   `provider/service-areas/page.tsx` were corrected. The service-area
   creation/edit form's individual field options (e.g., whether a
   "district" or "tier" selector is ever offered) were not audited
   field-by-field this slice.

6. **`app/(tenant)/service-areas/page.tsx` (geo-zone UI) not evaluated.**
   A separate, pre-existing page for a different backend module
   (`app.engines.geo`) with its own zone CRUD — its authorization
   alignment with its own backend was not assessed, since that module
   was never named in this slice's mission.

7. **Frontend lint not verified** — this app has no ESLint v9 config and
   `next lint`'s CLI fails in this environment for reasons unrelated to
   this change (documented, not silently skipped).

8. **Product-policy questions left open by design**: whether staff should
   ever get delegated service-area capabilities, and whether a canonical
   geography reference table should be introduced — both deliberate,
   policy-driven non-closures, not oversights.
