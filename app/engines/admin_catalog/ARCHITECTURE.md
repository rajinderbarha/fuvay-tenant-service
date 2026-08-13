# Catalog engine architecture

The Catalog control plane has two intentionally separate aggregate roots.

## Platform vertical registry (`vertical_catalog`)

`verticals` owns platform availability and lifecycle: release stage, registration
gating, capabilities/modules, tenant enrollment, activation, and the audit trail.
Disabling a vertical stops new entry; it does not rewrite service configuration or
silently terminate operational work.

## Service runtime catalog (`admin_catalog`)

`service_categories` owns customer/provider runtime classification: customer flow,
finance model, visibility, tenant selection, and the hierarchy from groups through
services, job types, dimensions, brands, questions, and pricing rules.

Despite historical UI wording, a service category is not the vertical lifecycle
record. New functionality must not duplicate release or enrollment state here.
Likewise, job-type requirements must remain on job-type blueprints rather than being
promoted to a category-wide flag.

## Extension contract

1. Add a stable registry key, never use a display label as an identifier.
2. Put platform enablement/capability state in `vertical_catalog`.
3. Put discoverable service behavior in `admin_catalog` and link by stable key.
4. Keep tenant customization in tenant-scoped catalog tables; never mutate the
   platform blueprint when a tenant edits an offering.
5. Every administrative lifecycle mutation requires a permission and audit context.
6. Large directories filter/count/page in PostgreSQL; page-scoped enrichment may be
   batched after pagination. Exports use the asynchronous enterprise export adapter.
7. Runtime publication changes should be versioned when they can affect existing
   bookings. Existing bookings retain their captured service/pricing snapshot.

This separation lets a new vertical reuse existing catalog engines or introduce new
service behavior without coupling tenant enrollment, operations, and pricing storage.
