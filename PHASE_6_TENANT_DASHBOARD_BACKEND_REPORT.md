# Phase 6 — Tenant Dashboard & Provider Setup Backend Report

## Architecture note (read first)

Like Phase 4/5, this is **not greenfield**. A full research pass confirmed
the tenant-facing portal is extensively built across 4 engines:
`tenant_engine/portal_router.py` (profile, staff, service areas, wallet
read, navigation, dashboard runtime), `package_commerce/tenant_router.py`
(packages, security deposit read, credit wallet/ledger read, commissions
read), `admin_catalog/tenant_router.py` (available/enabled services, self-
service catalog setup), and `provider_portal/router.py` (team members,
availability, offerings/pricing, onboarding status checklist, bookability
status). A separate, dedicated Next.js app (`frontend/tenant-portal/`) with
dozens of pre-built routes already consumes these APIs. All tenant-scoped
endpoints derive `tenant_id` exclusively from the JWT — never from request
body/query params — confirmed live (a `?tenant_id=` override attempt was
silently ignored).

## CRITICAL bug found and fixed: the primary test tenant owner could not reach their own tenant at all

`provider@serviceos.in` (the exact tenant-owner account this ticket's
baseline scenario names) had `users.tenant_id` pointing to a **phantom
tenant** (`f002bb6b-4e8b-4764-8d45-1f1ce4014999`) that does not exist in the
`tenants` table (`GET /v1/admin/tenants/{that_id}` → `404`) — while the real
"Demo AC Services" tenant's `owner_user_id` correctly points back to this
same user. Since every tenant-portal endpoint derives `tenant_id` solely
from the JWT claim (itself sourced from `users.tenant_id` at login), this
user could never actually reach Demo AC Services' real data — `dashboard/
runtime` returned `tenant: null` for everything, and `/v1/tenant/wallet`
silently returned a fresh zeroed default for a wallet that doesn't exist
under that phantom ID, masking the failure entirely. Fixed by correcting
`users.tenant_id` to the real Demo AC Services ID. Live-confirmed: a fresh
login now correctly resolves `tenant.business_name: "Demo AC Services"` on
the dashboard runtime endpoint, and `/v1/tenant/wallet` returns the real
ledger history (`lifetime_purchased: 1100, lifetime_consumed: 1100,
balance: 0` — matching Phase 4/5's test cycles exactly).

## Module 1 — Tenant Login / Context Guard

Confirmed live: fresh login for `provider@serviceos.in` issues a JWT with
`role: tenant_owner`, `tenant_id: 34b427a7-...` (now correct). Every tenant
endpoint tested derives tenant scope purely from this claim.

## Module 4/5/6 — Package & Credits, Ledger, Security Deposit (tenant view)

All read-only, all confirmed live:
- `GET /v1/tenant/wallet` → real balance (0, matching the Phase 5-restored baseline).
- `GET /v1/tenant/security-deposit` → `required_amount: 5000.0, status: "unpaid"` — separate table, separate endpoint, no mutation endpoints exist on the tenant router (`mark-paid`/`release`/`adjust`/`forfeit` all confirmed absent from `package_commerce/tenant_router.py`) — **tenant cannot self-mark deposit received, confirmed structurally impossible, not just policy-blocked.**

## Module 7 — Service Area Management

Confirmed live: `POST /v1/tenant/service-areas` with the exact baseline
(`Ludhiana, 141001, Punjab, India, coverage_type=zipcode`) succeeded,
creating a real, audited record with a real `request_id`. Query-param
`tenant_id` override attempts are silently ignored (isolation confirmed).

## Module 8 — Service Catalog

Confirmed live: `GET /v1/tenant/catalog/available-services` returns real
platform catalog data (AC Installation, etc. with real pricing);
`GET /v1/tenant/catalog/enabled-services` correctly returns empty
(`{"services": []}`) since this tenant hasn't enabled any yet — a genuine,
correct empty state, not an error.

## Module 11 — Staff / Team

`GET /v1/tenant/staff` → `{"staff": [], "total": 0}` — correct empty state
(Demo Technician was never actually created as a live user for this
tenant in prior sprints' fixture data, despite being referenced in the
ticket's baseline scenario — documented as a data gap, not a code bug).

## Result: **Backend certified after fixing 1 critical data-integrity bug (dangling tenant_id) and 3 files' worth of the systemic request_id-placeholder bug (48 occurrences total).** See `PHASE_6_TENANT_DASHBOARD_BUG_FIX_REPORT.md` for full detail.
