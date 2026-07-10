# Tenant My Status — API Mapping Report

The ticket's suggested API list is mostly aspirational (`/v1/tenant/context`, `/v1/tenant/status`,
`/v1/tenant/bookability`, etc.) — none of those exact paths exist. Real, working endpoints were
found and used instead, documented below.

| Ticket suggestion | Real endpoint used | Notes |
|---|---|---|
| `GET /v1/tenant/context` | `useTenant()` (localStorage, already populated at login) | No dedicated context endpoint; tenant name/vertical/city already cached client-side. |
| `GET /v1/tenant/status` | `GET /v1/provider/status` | Real Sprint-12 endpoint. **Was returning live 500** — see Bug Fix section. |
| `GET /v1/tenant/bookability` | (same as above) | `is_bookable` is a field on the same status object, not a separate endpoint. |
| `GET /v1/tenant/dashboard/setup-status` | Computed client-side from 6 real endpoints (see below) | No dedicated setup-status endpoint exists; `/v1/provider/onboarding/status` was tried and found to reference a nonexistent table (live 500) — not used. |
| `GET /v1/tenant/status/offerings` | `GET /v1/provider/status/offerings` | Real endpoint. **Was returning live 500** — see Bug Fix section. |
| `GET /v1/tenant/status/blockers` | Merged from `visibility_blockers`/`bookability_blockers` on `/v1/provider/status`, plus a client-side rules engine (`lib/status-format.ts`) | Backend blocker arrays are empty by default (no rule engine currently populates them) — required actions are derived from real, live account data instead. |
| `GET /v1/tenant/status/rules` | Static, ticket-specified rule list rendered in the "How bookability is calculated" panel | No backend rules-listing endpoint exists; the rule list itself is not tenant-specific data. |
| `POST /v1/tenant/status/recalculate` | `POST /v1/provider/status/refresh` | Real endpoint, `require_tenant_owner`-gated. **Currently a stub** — returns `{"refreshed": true}` without recomputing the status row. Documented as a non-blocking backend gap; the button still triggers it and refetches all sections. |
| `GET /v1/tenant/finance/summary` | `GET /v1/provider/onboarding/package-summary` + `GET /v1/tenant/security-deposit` + `GET /v1/tenant/credit-wallet` | Three real, dedicated endpoints combined for the Finance Readiness panel — richer and more accurate than one generic summary. |
| `GET /v1/tenant/package` | `GET /v1/provider/onboarding/package-summary` | Real endpoint (package_commerce/tenant_router.py). |
| `GET /v1/tenant/usage-credits/balance` | `GET /v1/tenant/credit-wallet` | Real, dedicated tenant self-service endpoint. |
| `GET /v1/tenant/security-deposit` | `GET /v1/tenant/security-deposit` | Matches exactly — real endpoint. |
| `GET /v1/tenant/service-areas` | `GET /v1/tenant/service-areas` | Matches exactly — real endpoint (already used by Phase 7B). |
| `GET /v1/tenant/services` | `GET /v1/provider/offerings/enabled` | Real endpoint. **Was returning live 500** — see Bug Fix section. |
| `GET /v1/tenant/staff` | `GET /v1/provider/team-members` | Real endpoint — more accurate than `staffApi.list()` (which only queries `role=staff` and misses real `technician`-role accounts, per Phase 5/7B findings). |
| `GET /v1/tenant/availability` | `GET /v1/provider/availability` | Real endpoint (fixed in Phase 7B — table now exists). |
| `GET /v1/tenant/documents` | None found | No tenant business-document endpoint exists (the Document Vault Engine's `GET /v1/documents` is per-entity e-signature docs, a different concept). Documents readiness is shown as "Not independently tracked yet" rather than fabricated. |
| `GET /v1/tenant/activity` | `GET /v1/tenants/{tenant_id}/audit-log` | Real endpoint (`tenant_engine/router.py`), used for Recent Status Activity. |

## New API client additions

`myStatusApi` added to `frontend/tenant-portal/lib/api.ts`, wrapping the real endpoints above
(reusing existing `providerStatusApi`/`providerOfferingsApi`/`providerServiceAreasApi`/
`providerTeamMembersApi`/`providerAvailabilityApi` where they already existed, adding 4 new thin
wrappers: `getPackageSummary`, `getSecurityDeposit`, `getCreditWallet`, `getAuditLog`).
