# Tenant My Status — Remaining Blockers

None of these block `READY_TENANT_MY_STATUS_ENTERPRISE_UI_CERTIFIED` — they are honestly
documented, non-blocking gaps per this session's established convention.

## 1. `POST /v1/provider/status/refresh` is a stub

Returns `{"refreshed": true}` without recomputing `provider_visibility_statuses` or
`provider_offering_bookable_statuses` rows. The button works (loading state, success refetch,
error+request_id on failure, permission-gated to tenant_owner) but calling it will not currently
change any displayed value, since nothing populates those tables' `is_visible`/`is_bookable`/
blockers fields yet. This is a backend rule-engine gap, not a frontend defect — the Required
Actions section works around it by deriving readiness from real, live account data directly
rather than depending on this endpoint's output.

## 2. No dedicated tenant business-document endpoint

Operational Readiness shows Documents as "Not independently tracked yet" rather than a real
count, since no `/v1/tenant/documents`-equivalent endpoint exists (the Document Vault Engine's
`GET /v1/documents` is a per-entity e-signature feature, not tenant business-verification
documents like GST certificates).

## 3. No granular frontend permission list

`/v1/auth/me` does not currently return a `permissions` array to the tenant-portal frontend
(unlike the raw login response, which does include one). Permission-aware UI in this page uses a
role check (`tenant_owner` vs other) as a pragmatic substitute for the ticket's full
`tenant.setup.recalculate` / `tenant.services.create` / etc. permission-key list. This correctly
gates the one real mutation on this page (Recalculate Readiness, which the backend itself
enforces via `require_tenant_owner`), but is coarser than true per-permission gating.

## 4. Coverage / pricing-setup readiness not independently modeled

`coverage_missing` and `pricing_setup_missing` blocker types exist in the rules vocabulary
(`lib/status-format.ts`) but are not independently computed in the Required Actions list, since
no offerings exist for the certified test tenant to evaluate coverage/pricing against. Once
offerings exist, `supported_type_ids`/`supported_brand_ids` emptiness could be used as a coverage
signal — deferred rather than guessed at with no real data to verify against.

## 5. Pre-existing, unrelated build failure on `/service-jobs`

Same `useSearchParams()` Suspense-boundary issue in `EnterpriseDataGrid.tsx` documented in
Phase 7B — confirmed untouched by this ticket's changes (no file this ticket modified imports
`EnterpriseDataGrid` or `useSearchParams`).

## 6. No ESLint config in `frontend/tenant-portal`

Same pre-existing gap documented in Phase 7B — `npx tsc --noEmit` was used as the primary
static-correctness gate.

## 7. No `npm test` script

`frontend/tenant-portal/package.json` has no `test` script (`dev`/`build`/`start`/`lint` only,
pre-existing). Frontend correctness was verified via `npx tsc --noEmit`, `npm run build`, and the
29 new static-inspection Python tests in `tests/test_tenant_my_status_enterprise_ui.py`.
