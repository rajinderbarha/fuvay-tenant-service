# Reference Workflow 2 — Provider Service & Pricing Setup

## Proposed guided flow (Standard Pattern 5) mapped to existing pages/APIs

1. Select category — `admin_catalog`/`vertical_catalog` read APIs (existing, `/tenant/setup/services` page)
2. Select or create service — `admin_catalog` tenant enablement API
3. Choose pricing model — `pricing` engine
4. Configure service types — `admin_catalog/catalog_enterprise_router.py` (service types master)
5. Configure options — `admin_catalog/service_option_provider_router.py` (`/v1/provider/setup/services`)
6. Assign supported brands — `admin_catalog/brand_provider_router.py` (canonical; NOT the disconnected `brands/provider_router.py`)
7. Configure base price/range — `pricing` engine, page `/provider/pricing`
8. Configure geographic overrides — `pricing` engine location-mapping equivalent (tenant-scoped)
9. Configure service areas — `/provider/service-areas`, `/provider/service-coverage` (currently two pages — collapse into steps 9a/9b of one wizard)
10. Configure availability — `/tenant/setup/availability` (HS5B)
11. Review — new summary step (does not exist today, needs to be built)
12. Publish — existing publish-readiness gate (`HS4B_PUBLISH_READINESS_FIX_REPORT.md` confirms a readiness check exists and was fixed to be accurate)

## Required data / conditional fields
- Pricing model choice (fixed vs range vs brand/type-dependent) determines which of steps 7-8 apply — type-dependent brand pricing is a confirmed, separately-built feature (`TYPE_DEPENDENT_BRAND_PRICING_*` reports) that should appear as a conditional branch at step 7, not a separate top-level page.
- Auto price options (Low/Mid/High) are computed automatically post-matching from these inputs — the manual bargain module is retired (RUNTIME_VERIFIED) and should not appear in this wizard at all.

## Validation / drafts / duplication
- Draft/save-progress capability: SOURCE_INFERRED exists per-page (each step is independently persisted today since these are separate pages) but there is no single wizard-level "draft" concept spanning all 12 steps — this is new UI/UX work, not new backend work.
- Templates: `service_setup_template_router.py` (admin_catalog) already supports templating — reuse as the "duplicate from template" option at step 2, once reconciled against the competing `service_setup/templates_router.py` (see canonical-pipeline-report.md #7 — resolve which is canonical before wiring this).
- Publish-readiness validation already exists and was hardened (HS4B reports) — reuse, don't rebuild.

## What stays as separate advanced-management pages after initial setup
- Bulk setup/wizard tooling (admin-side bulk operations across many tenants) stays a distinct admin page, not part of the per-tenant guided flow.
- Type/brand-specific override fine-tuning after initial publish stays an Advanced tab on the Services workspace (Level 3), not part of the initial wizard re-run.
- Auto price options admin configuration (`/admin/home-services/pricing-rules`) stays admin-only, not shown to tenant_owner.

## Error recovery
Each step's existing page already has its own validation/error handling (SOURCE_VERIFIED per individual HS reports); wizard shell needs to surface "step incomplete" state clearly rather than allow silent progression — this is the main net-new UX requirement, no backend gap identified.
