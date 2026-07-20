# Deferred Items — Slice 2F-21

- Implementation of `app.engines.package_commerce.tenant_router`'s
  authorization/ownership fix — deferred to Slice 2F-22 (the designated
  next slice; NOT implemented here per this slice's own discovery/selection
  scope boundary).
- Implementation of the 8 non-selected modules
  (`customer_reviews.provider_router`, `marketing_automation.provider_router`,
  `media.new_router` profile routes, `profile.router`,
  `admin_catalog.brand_provider_router`,
  `admin_catalog.recommendation_router`,
  `admin_catalog.service_option_provider_router`,
  `analytics.provider_router`) — deferred to future slices per
  `non-selected-module-queue.csv`.
- Frontend/mobile caller audits for all 9 modules — deferred per
  `known-limitations.md` item 1.
- `mark_paid` self-attestation policy resolution — deferred to Slice
  2F-22 per `product-decisions-required.md`.
- Compliance export-generation worker (`EXPORT_WORKER_NOT_IMPLEMENTED`,
  from 2F-20) — remains open, explicitly NOT reopened this slice per the
  mission's own instruction.
