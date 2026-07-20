# Known Limitations — Slice 2F-8

1. **Tenant-catalog-enablement vs. serviceability matching remains
   unresolved.** Serviceability does not check `TenantService.is_enabled`
   before allowing coverage mapping. Not fixed — not all required
   conditions were proven (see `tenant-catalog-enablement-contract.md`).

2. **The matching engine's join target (`ServiceCatalogItem`) is a
   third, apparently-legacy, tenant-scoped model** whose relationship to
   `admin_catalog.MasterService`/`TenantService` was not conclusively
   established. Investigating it fully would require auditing a fourth
   module (`service_catalog`), out of this slice's scope.

3. **No advisory/row lock on `enable_service`.** A concurrent race could
   surface as a raw database `IntegrityError` rather than a clean 409 —
   the schema-level unique constraint prevents an actual duplicate row,
   but the error path is not as clean as `serviceability`'s own pattern.
   Not fixed (no evidenced production incident).

4. **No audit event for any of the 9 catalog-enablement mutations.**
   Pre-existing, not introduced this slice, not fixed (design-choice).

5. **Type/brand mapping validation (`set_tenant_service_types`/
   `set_tenant_service_brands`'s internal `type_ids`/`brand_ids`
   cross-checks) not re-traced to the byte level.** No defect was
   evidenced, but a full independent audit was not performed.

6. **Frontend fix scoped narrowly** — only the `catalog/page.tsx`
   Enable/Disable button was corrected. `dashboard/page.tsx` and
   `provider/pricing/page.tsx` (both calling `masterCatalogApi` for
   reads only, confirmed via grep) were not audited field-by-field
   beyond confirming no mutation call exists there.

7. **Frontend lint not verified** — pre-existing environment/tooling gap,
   documented, not silently skipped.

8. **Product-policy questions left open by design**: whether staff should
   ever get delegated catalog-mapping capability, and whether/how to
   resolve the enablement/matching ambiguity — both deliberate,
   policy-driven non-closures, not oversights.
