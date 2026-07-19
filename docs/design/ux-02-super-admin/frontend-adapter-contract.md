# Frontend Adapter Contract

## `Ux02DataAdapter` (lib/ux02/types.ts)
```ts
export interface Ux02DataAdapter {
  listTenants(): Promise<TenantFixture[]>;
  getTenant(id: string): Promise<TenantFixture | undefined>;
  listVerificationSubmissions(): Promise<VerificationSubmissionFixture[]>;
  listComplianceCases(): Promise<ComplianceCaseFixture[]>;
  listSecurityObservations(): Promise<SecurityObservationFixture[]>;
  listAuditEntries(): Promise<AuditEntryFixture[]>;
}
```
No implementation of this interface exists yet — all current showcase pages import fixture arrays
directly (`FIXTURE_TENANTS`, etc.), not through an adapter instance. Wiring a real adapter
(backed by `admin_catalog/tenant_service`, onboarding, compliance, security, and audit endpoints)
is future work once each backend contract is confirmed — see `backend-contract-dependencies.md`.

## `CommandPaletteAdapter`
```ts
export interface CommandPaletteAdapter {
  search(query: string): Promise<{ id: string; label: string; group: string; href: string }[]>;
}
```
No unified search endpoint exists on the backend; this interface exists so the eventual palette UI
can be built against a stable contract regardless of what powers it later.

## Migration path
1. Implement `Ux02DataAdapter` against real endpoints (one method at a time, per confirmed
   contract).
2. Swap each showcase/production page's fixture import for a call through the adapter.
3. Promote the page's `readiness` from `MOCK_DESIGN_ONLY`/`API_CONTRACT_REQUIRED` to
   `READ_ONLY_READY` or `PRODUCTION_READY` only once verified end-to-end.
