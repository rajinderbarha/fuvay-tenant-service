# Tenant My Offerings — Remaining Blockers

None of these block `READY_TENANT_MY_OFFERINGS_ENTERPRISE_UI_CERTIFIED` — honestly documented,
non-blocking gaps.

## 1. `refresh-readiness` is a stub

`POST /v1/provider/offerings/enabled/{id}/refresh-readiness` resets `readiness_status` to
`"pending"` without evaluating real blockers (service area, coverage, pricing, technician,
availability). No readiness rule engine currently populates `readiness_blockers` for offerings.
The "Readiness Issues" tab and Readiness KPI card correctly reflect whatever `readiness_blockers`
the backend does supply (currently always empty for freshly-enabled offerings), and the
"Validate Offerings" header action routes to this tab rather than fabricating a synthetic
readiness computation client-side. A future sprint should build the actual offering-readiness
rule engine (service area presence, coverage completeness, pricing configured, active technician
assigned, availability configured) mirroring the client-side derivation already built for the
My Status page's Required Actions.

## 2. No DELETE endpoint for enabled offerings

Only activate/deactivate exist; there is no way to permanently remove an enabled offering via the
API. The ticket's "Delete" action was not added to the UI since no working backend call exists —
adding an unwired button would violate the "no mock runtime data" rule.

## 3. Coverage counts shown only inside the wizard, not on every catalog card

Fetching per-service type/brand/issue/option counts for all 15 available offerings on page load
would require ~45 additional API calls (3-4 per offering). Given the real, live endpoints
involved are per-service (not batchable), coverage detail (types/brands/issues/options) is
fetched lazily inside the Enable/Edit wizard when a specific offering is opened, rather than
pre-fetched for every card. Cards instead show the `requires_service_type`/`requires_brand`
boolean flags from the base catalog row. A future sprint could add a batch coverage-summary
endpoint to show full counts on every card without an N+1 fetch pattern.

## 4. Package-approval gate does not currently block offering *enabling*

The certified tenant's package is `paid_pending_approval` (not yet admin-approved), yet offerings
can still be enabled. This matches the ticket's business rule "Package starts after admin
approval" being about *usage credits and bookability*, not catalog browsing/enabling — but it's
worth flagging that `package_inactive` as a readiness blocker type is defined in the vocabulary
but not yet actually checked by any backend rule (ties into blocker #1 above).

## 5. Pre-existing, unrelated build failure on `/service-jobs`

Same `useSearchParams()` Suspense-boundary issue in `EnterpriseDataGrid.tsx` documented in prior
sprints — confirmed untouched by this sprint's changes.

## 6. No ESLint config / no `npm test` script

Same pre-existing gaps documented in prior sprints. `npx tsc --noEmit` + `npm run build` +
Python static-inspection tests used as the correctness gates.
