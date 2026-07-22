# Deferred Items — Slice 2F-6

Explicitly deferred to a future slice/phase — none of these were
investigated, designed, or acted on this slice:

1. All 18 other remaining unclosed tenant-facing modules (see
   `remaining-module-priority-matrix.csv`) — `serviceability.router`,
   `admin_catalog.tenant_router`'s last unprotected route,
   `complaints.provider_router`, `execution.real_estate_router`,
   `execution.coaching_router`, `field_ops.checklist_router`,
   `field_ops.staff_router`, `compliance.provider_router`,
   `platform_notifications.provider_router`, `media.new_router`,
   `marketing_automation.provider_router`,
   `customer_reviews.provider_router`, `profile.router`,
   `admin_catalog.brand_provider_router`,
   `admin_catalog.recommendation_router`,
   `admin_catalog.service_option_provider_router`,
   `analytics.provider_router`, `package_commerce.tenant_router`.
2. Remediation of `readonly@demo-ac-services.local`.
3. Migration 144.
4. Reopening `package_commerce`/`finance_hub` permission policy or
   granting `PACKAGES_*`/`FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*` permissions.
5. Fixing the package-wallet idempotency contract (owned by
   `package_commerce`, not this module).
6. Resolving the platform-wide commission-ownership question (owned by
   `platform_commerce`, not this module).
7. Merging `Booking`/`Job`/`ServiceBooking`/`ServiceJob`.
8. Booking Exception Resolution, Admin/Tenant My Work, Next-Action
   aggregation.
9. Onboarding or provider-setup redesign.
10. Chat ownership changes.
11. Frontend visual redesign, theme changes, new role aliases.
12. Granting `staff`/`technician` the `FIELD_OPS_INVOICE_GEN` permission
    (flagged, not decided — see `product-decisions-required.md`).
13. Adding positive-amount validation to `record_onsite_payment`/`add_item`
    (flagged, not added).
14. Hiding the "Issue" button from non-owner roles in the tenant-portal
    UI (flagged, not made — frontend redesign out of scope).
15. Beginning a second new router module this slice.
