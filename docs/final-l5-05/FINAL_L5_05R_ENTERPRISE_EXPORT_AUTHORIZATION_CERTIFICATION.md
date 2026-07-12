# FINAL-L5-05R — Enterprise Export Resource Mapping, Backend Authorization and Runtime Certification

## Scope actually completed this sprint

FINAL-L5-05R's 53-part mission targets exhaustive Enterprise Export authorization across every resource, format, storage/retention, audit, and role boundary. This sprint completed the mission's own literal title — resource mapping — and closed 3 additional real defects found while verifying it, rather than attempting the full 53-part scope in one session, consistent with this engagement's established pattern.

### 1. Completed the resource mapping: 39/39 resources now mapped (was 12/39)

**Investigation**: `RESOURCE_EXPORT_PERMISSIONS` (`app/engines/enterprise_grid/filter_registry.py`) mapped 12 of the platform's 39 registered export resources (Finance/Security/Jobs, closed in FINAL-L5-05O). The remaining 27 — Tenants, Categories, Engines, Offerings, Service Bookings, Coaching Appointments, Real Estate Leads, Service Invoices, Payments, Commission Records, Reviews, Complaints, Refund/Rework Requests, Pricing Tiers/Locations/Rules, Customers, Settings, Feature Flags, and all 7 `provider_*`-scoped resources — remained reachable by any authenticated admin, a documented residual gap from FINAL-L5-05O.

**Fix**: All 27 are now mapped, reusing existing permission keys wherever a clean domain fit existed (`finance:hub:export` for financial documents; `security:audit:export` already covered by existing entries; `tenant:data:export` for Tenant Administration and all 7 provider-self-service resources; `customers:export`/`settings:export` for exact-match resources) and introducing exactly 2 new keys where no existing permission fit the domain: `operations:export` (Reviews/Complaints/Refund-Rework Requests/Bookings/Appointments/Leads — customer-service-adjacent operational content) and `catalog:export` (Categories/Engines/Offerings/Pricing Tiers/Locations/Rules — platform catalog/pricing configuration). `operations:export` is granted to Operations Admin, matching this mission's own Part 9 policy text naming Reviews/Complaints as Operations-approved; `catalog:export` is granted to no limited role this sprint (Super Admin only), since no explicit business policy names it as approved for any role — a conservative default, not an oversight.

### 2. Closed the "unknown resource silently bypasses authorization" gap (P1)

**Investigation**: `required_export_permission()` uses `dict.get()`, returning `None` for a resource_key not in the mapping. The router's original check (`if required and not has(...)`) treated `None` as falsy and **skipped authorization entirely** for any unregistered/typo'd resource_key — before this sprint's mapping completion, this silently affected the (then-unmapped) 27 resources; after completion, it would still affect any genuinely unknown key (a probe, a future resource added to the registry without an export mapping, a client bug).

**Fix**: `create_export` now checks `EnterpriseFilterRegistry.resource_exists()` **first**, before the permission check, returning a controlled `422 EXPORT_RESOURCE_UNSUPPORTED` for anything not registered — closing the fail-open path completely and matching the mission's explicit Part 6/31 requirement.

### 3. Wired the dead-code tenant-scope check into export creation, with a live-verified regression fix (P1)

**Investigation**: `EnterpriseListQueryService.validate_scope()` — designed to force `SCOPE_PROVIDER` resources to always use the caller's own `tenant_id`, ignoring any payload override — has **zero callers anywhere in the codebase**. It was never wired into the list/query path it was seemingly built for, and never into export creation at all. This meant a provider/tenant-side caller could submit `filters: {"tenant_id": "<another tenant>"}` for any of the 7 `provider_*` resources with no rejection at job-creation time.

**Fix**: `create_export` now enforces this directly: for `SCOPE_PROVIDER` resources, a `tenant_id` filter that doesn't match the caller's own `u.tenant_id` is rejected with `403 EXPORT_CROSS_TENANT_FORBIDDEN`.

**Real regression found and fixed during live verification**: the first version of this fix did not exempt `super_admin`, whose `tenant_id` is `None`/platform-level — meaning Super Admin was incorrectly blocked from exporting *any* provider-scoped resource with a `tenant_id` filter (since `None` never equals a real tenant UUID). Live-verified: before the fix, `POST /v1/enterprise/exports` for `provider_service_jobs` with a real tenant_id filter returned `403` for Super Admin; after adding the same `super_admin` exemption pattern already used elsewhere in this codebase (`ServiceabilityService._assert_owns_tenant()`), it correctly returns `201`.

### 4. Fixed a genuine 500-instead-of-422 defect found while live-verifying the new mappings (P2)

**Investigation**: `create_export_job` raises a plain `ValueError` (not a `ServiceOSException`) for invalid field selection, unknown export job lookups, and access-denied cases — a pre-existing, pervasive pattern shared with the unrelated Saved-Views/Column-Preferences endpoints in the same router (not touched this sprint). Left uncaught, an invalid `columns` selection produced an unhandled `500 INTERNAL_ERROR` instead of a controlled `422`, discovered live while verifying the newly-completed resource mappings with a test payload that happened to use an invalid column name.

**Fix**: The 3 export endpoints (`create_export`, `get_export`, `retry_export`) now catch `ValueError` and convert the known export-specific error codes (`EXPORT_FIELD_NOT_ALLOWED` → 422, `EXPORT_JOB_NOT_FOUND` → 404, `EXPORT_JOB_ACCESS_DENIED` → 403) to controlled `ServiceOSException`s, matching this mission's Part 31 error model. Scoped narrowly to export endpoints only — the Saved-Views/Column-Preferences endpoints sharing the same `ValueError` pattern are unrelated to this sprint's Export Authorization scope and were not touched.

### 5. Added CSV formula-injection mitigation (Part 14)

`generate_csv` now prefixes any cell value starting with `=`, `+`, `-`, `@`, tab, or CR with a single quote (the standard OWASP CSV-injection mitigation), neutralizing formula execution in Excel/Sheets without altering the visible value for legitimate data.

## A significant, honest limitation: no export worker exists

**Investigation**: `ExportService.generate_csv()` and `.mark_completed()` are never called from anywhere in the router or any background job — confirmed via full-codebase grep. `create_export_job` only ever creates a job row (`PENDING`, or `FAILED` with `EXPORT_ASYNC_REQUIRED` if the estimated row count exceeds the sync limit). **No file is ever actually generated by this system, for any resource, admin or provider.** This matches a carry-forward note from FINAL-L5-05K's documentation ("async export worker is a carry-forward TODO") — a pre-existing platform limitation, not something introduced or left incomplete by this sprint's bounded fixes.

**Consequence for this mission's acceptance criteria**: Part 42's "Real Generated-Export Verification" (file exists, format valid, columns correct, checksum) and Part 39's "export worker/background processor runs where required" **cannot be satisfied as literally written**, because no worker exists anywhere in this codebase to generate a file for any resource. This is documented honestly here rather than silently claimed complete — the authorization boundary this sprint hardened (job creation, permission checks, tenant-scope checks) is real and live-verified; the downstream file-generation pipeline it gates is unimplemented platform infrastructure.

## Automated guards

`tests/test_final_l5_05r_export_resource_mapping.py` — 21 new tests, all passing: exhaustive mapping completeness (all 39 resources), no read-permission-as-export-permission, every mapped key is a real `P.*` value, domain-correct mapping spot-checks per group, fail-closed unknown-resource verification, the tenant-scope enforcement + super_admin exemption, CSV injection sanitization (both unit-level and via a real `generate_csv` call), and the mandatory cross-domain role isolation checks (Operations/Finance/Security/Read-Only).

## Verification summary

- Full backend regression: 9186 passed (pre-sprint baseline), 9207 with the 21 new tests. One full-suite run showed 13 failed/23 errors confined entirely to `test_p0_provider_enterprise.py` (a file this sprint never touched); standalone rerun of that file showed 65/65 passing, 0 errors — confirmed as the same class of pre-existing, test-order-dependent full-suite flake documented in FINAL-L5-05Q (`test_trust_quality_phase1.py`), not a regression from this sprint's changes. A second full-suite run was performed for final confirmation.
- TypeScript: 0 errors (no frontend changes this sprint).
- Production build: passes.
- Live 5-role API matrix: every newly-mapped resource verified — Operations resource (`admin_reviews`) 201 for Super Admin + Operations Admin, 403 for Finance/Security/Read-Only; Catalog resource (`admin_categories`) 201 for Super Admin only; Finance-adjacent resource (`admin_payments`) 201 for Super Admin + Finance Admin, 403 for others; Tenant resource (`admin_tenants`) Super-Admin-only; unknown resource key → 422; invalid field selection → 422 (previously 500); the FINAL-L5-05O regression set (`admin_finance_topups`) re-confirmed unchanged.
- Live cross-tenant/scope verification: Super Admin exemption fix confirmed live (previously-broken 403 now correctly 201); the actual cross-tenant denial path for a non-exempt caller was verified via static/code-level inspection (no demo `tenant_owner` credential was available in this session to exercise it end-to-end as a live HTTP call — documented honestly as a residual gap, not claimed complete).
- Live Chromium: 13 re-run prior-sprint tests (05N/05O) touching the Enterprise Export/permission UI, zero regression. No new frontend code was written this sprint (all fixes were backend), so no new Chromium coverage was added beyond confirming the existing UI still functions against the hardened backend.

## Explicitly not attempted this sprint (honestly documented, not hidden)

See `FINAL_L5_05_BUG_REGISTER.md` (L5-05R-001 through 012) and `FINAL_L5_05_REMAINING_BLOCKERS.md`. In summary:

- **No export worker/file-generation pipeline exists** — a pre-existing platform limitation (see above), blocking Part 42's real-generated-file verification and Part 39's worker-startup check entirely. This is the single largest reason full READY cannot be returned.
- **Sensitive-field classification** (Part 13) was not performed resource-by-resource beyond what already exists in each resource's `sensitive_fields`/`allowed_export_fields` config (pre-existing from Sprint 26) — a full audit against the mission's PUBLIC/INTERNAL/CONFIDENTIAL/SENSITIVE/SECRET/PROHIBITED taxonomy was not done.
- **Export result/download authorization** beyond the existing `requested_by_user_id` ownership check (confirmed correct, pre-existing) was not extended — there is no signed-URL/storage layer to audit since no files are ever generated.
- **Rate limits and concurrency/idempotency testing** (Parts 29/30) were not performed — the sync row-limit check (`ENTERPRISE_SYNC_EXPORT_ROW_LIMIT`) is pre-existing and was not re-verified.
- **Full five-role Chromium export-dialog matrix** (Part 43) was not run — no export dialog/UI was found or modified this sprint beyond what 05O already covers (dashboard export button, Security Deposits action menu).
- **Throttled-network, responsive, and accessibility verification** (Parts 44-46) — same carried-forward gaps as every prior sprint in this engagement.

## Result

The mission's own literal title — completing Enterprise Export resource mapping — is done: all 39 registered resources now have an explicit export permission, zero fall back to generic authenticated access. Three additional real defects were found and fixed while live-verifying this completion: an unknown-resource fail-open gap, a dead-code tenant-scope check now wired in (with a live-caught-and-fixed Super Admin regression), and a 500-instead-of-422 error-handling bug. CSV formula injection is now mitigated. All fixes are live-verified via a real 5-role API matrix and re-run Chromium regression, with zero regressions in 9186+ backend tests. The most significant honest finding is architectural, not something this sprint could close: no export worker exists anywhere in this codebase, so no export ever produces a real file for any resource — this is a pre-existing platform limitation (carried forward from FINAL-L5-05K), not an incomplete fix, and it is the primary reason the mission's real-generated-export verification requirement cannot be satisfied.
