# Service Type Consistency

## Model / ownership

`ServiceCatalogItem` (via `ServiceCatalogService.get_by_service_type_id(tenant_id,
service_type_id)`), tenant-owned, `is_active` required (both enforced since Slice 2F-14C,
unchanged this slice).

## Relationships

- **Catalog relationship**: `service_type_id` is the catalog's own key field.
- **Booking relationship**: cross-checked this slice — a supplied `service_type_id` must match
  `booking.service_type_id` when `booking_id` is also supplied.
- **Parent Job relationship**: intentionally NOT cross-checked (see
  parent-job-relational-consistency.md — `REPAIR_SERVICE_MAY_DIFFER_BY_POLICY`).
- **Checklist-template relationship**: `Job.checklist` is populated from
  `catalog_item.checklist_template` only when the client didn't supply one — this uses the SAME
  already-tenant-validated `catalog_item` object fetched during the new validation step (Slice
  2F-14C's optimization, unchanged), so the checklist can never be materialized from an
  unvalidated or foreign-tenant catalog entry.

## Verified

- Foreign service rejected: `FOREIGN_SERVICE_TYPE` (2F-14C, unmodified).
- Inactive service rejected: `INACTIVE_SERVICE_TYPE` (2F-14C, unmodified).
- Booking-derived service cannot be silently replaced: fixed this slice
  (`SERVICE_BOOKING_MISMATCH` on disagreement — the request is rejected, not silently
  overridden).
- Parent-derived service: no replacement concept exists — service is never derived from a
  parent, so there's nothing to "replace" (see parent-job-relational-consistency.md).
- Checklist materialization uses the verified service: confirmed — `catalog_item` (the same
  object validated for tenant/active status) is the only source for auto-populated checklist
  data.
- A mismatched service does not generate an unrelated checklist: confirmed — if
  `service_type_id` disagrees with a supplied `booking_id`'s service, the request is rejected
  before `Job(...)` is ever constructed, so no checklist (correct or incorrect) is ever
  generated for a mismatched combination.
