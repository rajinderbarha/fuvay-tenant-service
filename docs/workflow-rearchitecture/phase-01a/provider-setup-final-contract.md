# Decision 10.2 — Provider Service and Pricing Setup: Final Contract

## Canonical records
`Service`, `ServiceOption`, `Brand`, `PricingRule`/`PricingOverride`, `TenantServiceArea` (admin_catalog, pricing, HS5/HS5B models). Brand assignment must use `admin_catalog/brand_provider_router.py`, NOT the disconnected `brands/provider_router.py` (never mounted — dead code).

## Canonical endpoints
Category/service: `admin_catalog` tenant enablement API. Options: `service_option_provider_router.py` (`/v1/provider/setup/services`). Brands: `admin_catalog/brand_provider_router.py`. Pricing: `pricing` engine. Areas: HS5 tenant API. Availability: HS5B tenant API. Publish-readiness: existing gate, hardened per HS4B reports (reuse, do not rebuild).

## Role ownership
tenant_owner (primary), staff (if permission-delegated).

## Entry route
`/tenant/setup/services` (Setup Wizard entry point), reachable from Home's onboarding checklist and Services nav item.

## Step sequence
1. Category, 2. Service, 3. Pricing model choice, 4. Service types, 5. Options, 6. Brands, 7. Base/range price (branches on step-3 choice — type/brand-dependent pricing is a confirmed separately-built feature, surfaced here as a conditional sub-step, not a separate page), 8. Geographic overrides, 9. Service areas/coverage, 10. Availability, 11. Review (new — does not exist today, needs building), 12. Publish (reuse existing gate).

## Required / conditional fields
Pricing model choice at step 3 determines whether steps 7-8 show fixed-price, range, or type/brand-dependent inputs. Auto price options (Low/Mid/High) are computed automatically downstream at booking time — not configured in this wizard.

## Validation
Reuse existing publish-readiness validation (HS4B, already hardened) at step 12 — do not duplicate validation logic in the new wizard shell.

## Status transitions
draft (per-step, page-level today) → published. No single wizard-level draft state exists yet — this is net-new UI/UX state, not a backend change (each step already persists independently).

## Available actions
Save & continue (each step), Save as draft (exit wizard, resume later — new capability, needs a lightweight "setup progress" record; see aggregation-endpoint-recommendations.md item 3), Publish (step 12).

## Error recovery
Each step's existing page-level validation surfaces inline; wizard shell adds a persistent "steps incomplete" indicator rather than allowing silent progression to publish.

## Notifications / audit
Publish action should notify relevant staff/admin per existing patterns (SOURCE_INFERRED, not independently re-verified this pass).

## My Work integration
Item type: setup_incomplete (tenant_owner) if wizard started but not published within some threshold.

## Next-action behavior
Per next-action-contract.md "Provider setup" section — progress is aggregated across the 12 steps via the new setup-progress endpoint.

## Backend blockers
1. Two competing setup-template/bulk-wizard systems (admin_catalog vs service_setup engines) — must be reconciled before step 1/2's "duplicate from template" feature is wired; if unresolved by Phase 2 start, ship without templating and add later.
2. Two competing customer-flow engines — affects category routing consistency between this wizard and the customer-facing booking flow; recommend confirming which one the current booking flow actually calls (not investigated in this pass) before Phase 2 finalizes step 1.

## Frontend limitations for Phase 2
No template/duplicate-from-existing-service feature until blocker 1 is resolved. No "review" step exists yet — must be built new (aggregation only, no new business logic).

## Acceptance criteria
- Wizard covers all 12 steps against real, already-working per-step pages/APIs.
- Publish step reuses the existing hardened readiness gate unchanged.
- Setup-progress aggregation endpoint correctly reflects real completeness per step.
- Advanced pricing/brand overrides remain available post-publish as a DETAIL_TAB, not forced back into the wizard.
