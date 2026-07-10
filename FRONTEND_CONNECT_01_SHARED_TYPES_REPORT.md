# FRONTEND-CONNECT-01 — Shared Home Services Types Report

`lib/api-foundation/home-services-types.ts` (both frontends, pre-existing this sprint, verified correct):

## Strategy
Re-exports existing types from `../api.ts` under the spec's requested names rather than forking new interfaces (that file is the source of truth with hundreds of call sites):
`ProviderStatusResult`, `OfferingBookableStatus as BookabilityStatus`, `EnabledOffering as TenantService`, `PackageAssignmentSummary`, `TenantSecurityDepositStatus`, `TenantCreditWalletDetail as UsageCreditBalance`, `ProviderServiceArea as ServiceArea`, `ProviderTeamMember as Technician`, `ProviderAvailabilityRule as AvailabilityRule`.

## New types (no existing equivalent)
`PaymentMode = "customer_pays_provider_directly"`, `CustomerPriceOptions {low, mid, high, currency, platform_fee_percent?}`, `ServiceGroup`, `Service`, `ServiceType`, `Brand`, `Issue`, `ServiceOption`, `PricingRule`, `TenantServiceCoverage`, `MatchingDiagnostic`, `ProviderMatch`, `JobStatus` (aliased to `string`, full enum lives in `components/shared/ui.tsx` job status map), `Job`, `CompletionProof`, `UsageCreditLedgerEntry`, `AuditEvent`.

super-admin's version of the same file mirrors this exactly, sourcing admin-side equivalents from `lib/api.ts` where they exist.

## Explicit architecture note baked into the file's header comment
"Payment architecture is confirmed direct customer-to-provider payment + platform usage-credit billing — NOT wallet/payout. Do not add wallet/payout types here even though a legacy `/provider/wallet` page exists elsewhere in the repo (out of scope for this sprint to rename)." — this correctly documents the known pre-existing legacy naming without expanding scope to fix it.

## `any`/`unknown` usage
None of the new type declarations use `any`. `unknown` appears once, in `ApiError.raw?: unknown` (error-model.ts) — intentional, since the raw caught value is genuinely unknown-shaped before normalization.

## Files
- `g:\serviceos\frontend\super-admin\lib\api-foundation\home-services-types.ts`
- `g:\serviceos\frontend\tenant-portal\lib\api-foundation\home-services-types.ts`
