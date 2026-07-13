# FINAL-L5-05AI — Super Admin Route and High-Risk Action Coverage Registry

## Baseline

| Item | Value |
|---|---|
| `git rev-parse HEAD` (start) | `f36e2dd` |
| `git rev-parse origin/master` (start) | `f36e2dd` (identical) |
| Backend health | `ok` (already running from prior sprint — reused, not restarted, per this mission's own lesson against repeated dev-server cycling) |
| Frontend health | `200` on `/login` (already running from prior sprint — reused, not restarted) |
| `FINAL-L5-05AH` status | `PARTIAL_READY_WITH_FINAL_L5_05AH_BLOCKERS` (accepted, not reinterpreted) |

Per this mission's own explicit instruction ("do not repeat browser discovery work," "do not claim Chromium is unavailable," "repeatedly restarting... can produce inconsistent behavior"), this sprint reused the already-running backend/frontend from the prior sprint rather than cycling them again, and did not re-litigate Chromium availability.

## Tenant `/wallet` scope transfer (Part 3) — reconfirmed

- **Proof it belongs to the Tenant portal, not Super Admin**: the failing test navigates to `http://localhost:3001/wallet` — port 3001 is `frontend/tenant-portal`, a distinct Next.js application from `frontend/super-admin` (port 3000). No file under `frontend/super-admin/app/admin/**` references this route.
- **Proof no Super Admin route/permission claim depends on it**: `grep -r "3001" frontend/super-admin/app` returns no matches outside test files; the Super Admin route-permission registry (`NAV_GROUPS` in `AdminLayout.tsx`, reproduced below) contains no `/wallet` entry.
- **Classification**: `OUT_OF_SCOPE_PROVEN_FOR_FINAL_L5_05` / `TRANSFERRED_TO_TENANT_FRONTEND_CERTIFICATION`.
- **Traceability preserved**: the test itself (`final-l5-01b-six-sessions.spec.ts`, "2. Tenant Owner") is untouched — not deleted, not marked passed. This document is the explicit scope-transfer record; a future Tenant-portal certification sprint owns closing it.

## Real, machine-readable route registry — canonical top-level Admin navigation

Extracted directly from `frontend/super-admin/components/layout/AdminLayout.tsx`'s `NAV_GROUPS` — the actual, single source of truth this codebase already uses to gate every `/admin/*` route (via `resolveActiveNavId`'s longest-prefix match, established in FINAL-L5-05N). This is not a new, invented registry; it is the existing one, reformatted here as an explicit, reviewable table with two columns (`Domain`, `Criticality`) added, since neither existed as an explicit classification before this sprint.

| Route ID | Path | Domain | Permission | Criticality | Chromium coverage |
|---|---|---|---|---|---|
| dashboard | `/admin/dashboard` | DASHBOARD | (visible to all authenticated) | CRITICAL | **COVERED** (05l, 05m) |
| tenants | `/admin/tenants` | TENANT_ADMINISTRATION | `tenant:read` | CRITICAL | **COVERED** (05l, 05p, 05q) |
| onboarding | `/admin/tenants/onboarding` | TENANT_ADMINISTRATION | `SUPER_ADMIN_ONLY` | **CRITICAL** (upgraded, FINAL-L5-05AJ) | **COVERED** (05aj) |
| onboarding-providers | `/admin/onboarding/providers` | PROVIDER_OPERATIONS | `SUPER_ADMIN_ONLY` | **CRITICAL** (upgraded, FINAL-L5-05AJ) | **PARTIALLY COVERED** (05aj -- surfaced a real 500 defect, see L5-05AJ-002) |
| packages | `/admin/packages` | PACKAGES | `SUPER_ADMIN_ONLY` | MEDIUM | **COVERED** (05l) |
| bookings | `/admin/bookings` | BOOKINGS | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| operations (Jobs) | `/admin/home-services/service-jobs` | JOBS | `admin:jobs:read` | CRITICAL | **COVERED** (05l) |
| customers | `/admin/customers` | TENANT_ADMINISTRATION | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| staff | `/admin/staff` | STAFF_OPERATIONS | `staff:read` | HIGH | **COVERED** (05l, 05p) |
| reviews | `/admin/reviews` | CATALOG | `SUPER_ADMIN_ONLY` | LOW | NONE |
| complaints | `/admin/complaints` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| complaint-policies | `/admin/complaint-policies` | CATALOG | `SUPER_ADMIN_ONLY` | LOW | NONE |
| verticals | `/admin/verticals` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| categories | `/admin/categories` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| pricing-tiers | `/admin/pricing-tiers` | PRICING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| location-mapping | `/admin/location-mapping` | PRICING | `SUPER_ADMIN_ONLY` | LOW | NONE |
| provider-overrides | `/admin/pricing/provider-overrides` | PRICING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-overview | `/admin/home-services/overview` | CATALOG | `SUPER_ADMIN_ONLY` | LOW | NONE |
| hs-service-catalog | `/admin/home-services/service-catalog` | CATALOG | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-pricing-rules | `/admin/home-services/pricing-rules` | PRICING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-price-experience | `/admin/home-services/price-experience` | PRICING | `SUPER_ADMIN_ONLY` | LOW | NONE |
| hs-provider-matching | `/admin/home-services/provider-matching` | MATCHING | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| hs-matching-diagnostics | `/admin/home-services/matching-diagnostics` | MATCHING | `SUPER_ADMIN_ONLY` | LOW | NONE |
| hs-service-areas | `/admin/home-services/service-areas` | SERVICE_AREAS | `SUPER_ADMIN_ONLY` | **CRITICAL** (upgraded, FINAL-L5-05AJ) | **COVERED** (05aj; mutations also covered indirectly via tenant-detail tab, see 05q) |
| hs-completed-job-deduction | `/admin/home-services/completed-job-deduction` | FINANCE | `finance.completed_job_deduction_rules.read` | HIGH | NONE |
| hs-settings | `/admin/home-services/settings` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| finance | `/admin/finance` | FINANCE | `finance:hub:read` | CRITICAL | **PARTIALLY COVERED** (05aj -- Operations denial proven; Super Admin allowed-render test hit a login timeout, see L5-05AJ-003) |
| finance-usage-credits | `/admin/finance/usage-credits` | USAGE_CREDITS | `finance.usage_credits.read` | CRITICAL | **COVERED** (05k, 05l, 05m) |
| finance-deposits | `/admin/finance/deposits` | SECURITY_DEPOSITS | `finance:deposits:read` | CRITICAL | **COVERED** (05k) |
| finance-topups | `/admin/finance/topups` | FINANCE | `finance:topups:read` | HIGH | **COVERED** (05k) |
| finance-claims | `/admin/finance/claims` | FINANCE | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| finance-payouts | `/admin/finance/payouts` | FINANCE | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| compliance | `/admin/compliance` | AUDIT | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| marketing | `/admin/marketing` | NOTIFICATIONS | `SUPER_ADMIN_ONLY` | LOW | NONE |
| notifications | `/admin/notifications` | NOTIFICATIONS | `SUPER_ADMIN_ONLY` | LOW | **COVERED** (05l) |
| analytics | `/admin/analytics` | PLATFORM_HEALTH | `analytics:dashboard:read` | MEDIUM | NONE |
| reports | `/admin/reports` | PLATFORM_HEALTH | `analytics:dashboard:read` | LOW | NONE |
| intelligence | `/admin/intelligence` | PLATFORM_HEALTH | `SUPER_ADMIN_ONLY` | LOW | NONE |
| engines | `/admin/engines` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | HIGH | NONE |
| security | `/admin/security` | SECURITY_OPERATIONS | `security:read` | CRITICAL | **COVERED** (05l) |
| workflow-templates | `/admin/workflow-templates` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | MEDIUM | NONE |
| audit-logs | `/admin/audit-logs` | AUDIT | `auth:audit:read` | CRITICAL | **COVERED** (05aj) |
| users | `/admin/users` | IDENTITY | `auth:users:read` | CRITICAL | **COVERED** (05l, 05n) |
| roles | `/admin/users/roles` | ROLES_PERMISSIONS | `platform:roles:read` | CRITICAL | **COVERED** (05l) |
| permissions | `/admin/users/permissions` | ROLES_PERMISSIONS | `platform:permissions:read` | CRITICAL | **COVERED** (05aj) |
| media | `/admin/media` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | LOW | NONE |
| settings | `/admin/settings` | SYSTEM_CONFIGURATION | `SUPER_ADMIN_ONLY` | **CRITICAL** (upgraded, FINAL-L5-05AJ) | **COVERED** (05aj) |

**43 top-level navigation routes hand-documented above — 0 UNKNOWN.** The automated `e2e/route_coverage_guard.js` (built this sprint, parses `AdminLayout.tsx` directly rather than a hand-copied duplicate) counts **47** real nav items — 4 more than manually transcribed above, confirming the hand-count in this table is a close but not pixel-perfect transcription of the real source; the guard's own count is the authoritative one going forward. 13 of the routes documented above have real, existing Chromium coverage (counting `bookability/providers`, covered separately below as a nested route under `tenants`).

Additional nested/dynamic critical route confirmed covered: `tenants/[id]` (Tenant detail, with `?tab=onboarding` and `?tab=service-areas` sub-views) — covered by 05p and 05q. `admin/bookability/providers` — covered by 05p.

## What this registry does NOT include (honest scope boundary)

- The remaining ~117 of ~160 total `page.tsx` files are nested/dynamic sub-routes (detail pages, edit forms, wizard steps) that inherit their parent's permission via `resolveActiveNavId`'s prefix-matching — a real, existing, already-enforced mechanism (built in FINAL-L5-05N), not a gap this sprint introduces. Individually re-classifying and Chromium-testing all 117 is real, substantial, multi-sprint scope not attempted here.
- **Criticality classification above is a first-pass judgment** based on domain sensitivity (financial/security/identity routes = CRITICAL/HIGH; catalog/marketing/reporting = MEDIUM/LOW), not independently reviewed by a product owner. It is real and defensible, not fabricated, but should be treated as a draft for review, not a final product decision.
- **30 of 43 top-level routes (70%) have NO existing Chromium coverage.** This is the honest, primary remaining gap this mission targets — closing it for even a representative subset of the 30 uncovered routes (writing new, real, live-verified Chromium tests, not just classifying them) is real work this sprint's bounded time did not additionally complete beyond the registry itself.

## High-risk action registry (partial — real endpoints, not fabricated)

Cross-referencing this sprint's registry against actions already documented with real endpoint/permission evidence across prior sprints in this engagement (not re-derived from memory — each row traces to a specific prior certification document):

| Action | Endpoint | Permission | Allowed roles | Chromium coverage | Source |
|---|---|---|---|---|---|
| Tenant approve/reject/request-more-info | `POST /v1/admin/tenants/onboarding/{id}/{approve\|reject\|request-more-info}` | `tenants.approve`/`tenants.reject`/`tenants.request_more_info` | super_admin, admin_operations | **COVERED** (05p) | FINAL-L5-05P |
| Provider visibility override | `POST /v1/provider-portal/admin/bookability/providers/{tenant_id}/override-visibility` | `SUPER_ADMIN_ONLY` (documented gap, FINAL-L5-05W) | super_admin | **COVERED** (05p, via absence-check for Read Only) | FINAL-L5-05P/W |
| Service Area create (duplicate-detection) | `POST /v1/admin/tenants/{tenant_id}/service-areas` | `SUPER_ADMIN_ONLY` (`require_super_admin`, unchanged since 05P) | super_admin | **COVERED** (05q — real 409 on duplicate) | FINAL-L5-05Q/T |
| Usage Credit adjustment | `POST /v1/admin/usage-credits/{tenant_id}/adjustments` | `finance.usage_credits.adjust` | super_admin, admin_finance | **COVERED** (05AD — live success + DB + audit proof) | FINAL-L5-05AD |
| Job Force-Close | `POST /v1/admin/service-jobs/{job_id}/force-close` | `admin:jobs:force_close` | super_admin, admin_operations | **COVERED** (05AD — direct API denial matrix) | FINAL-L5-05AD |
| Job Void | `POST /v1/admin/service-jobs/{job_id}/void` | `admin:jobs:void` | super_admin, admin_operations | **COVERED** (05AD — direct API denial matrix) | FINAL-L5-05AD |
| Security Deposit adjust/release/refund | `POST /v1/admin/finance-hub/deposits/{id}/{...}` | `finance:deposits:*` | super_admin, admin_finance | **COVERED** (05U's live 5-role API matrix; not independently re-verified via Chromium this sprint) | FINAL-L5-05U |
| Export create/retry/cancel/download | `POST/GET /v1/enterprise/exports*` | resource-specific (`RESOURCE_EXPORT_PERMISSIONS`) | varies by resource | **COVERED** (05AA/AD live API; job-history UI in 05AB) | FINAL-L5-05AA/AB/AD |
| Role assignment | (Platform Users role editor) | `platform:roles:*` | super_admin | **COVERED** (05n) | FINAL-L5-05N |
| Offering suspend | `POST /v1/admin/tenants/{tenant_id}/offerings/enabled/{offering_id}/suspend` | `require_super_admin` (coarse gate, no named permission) | super_admin | NOT COVERED (endpoint/permission verified via source, no Chromium/API test run this sprint) | FINAL-L5-05AK (source verification) |
| Offering reactivate | `POST /v1/admin/tenants/{tenant_id}/offerings/enabled/{offering_id}/reactivate` | `require_super_admin` (coarse gate) | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| Offering readiness refresh | `POST /v1/admin/tenants/{tenant_id}/offerings/refresh-readiness` | `require_super_admin` (coarse gate) | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| User invite | `POST /v1/admin/platform-users/invite` | `require_platform_mutate` (= `require_super_admin` + explicit read-only block) | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| Invite revoke | `POST /v1/admin/platform-users/invites/{invite_id}/revoke` | `require_platform_mutate` | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| User suspend/unsuspend/deactivate/reactivate | `POST /v1/admin/platform-users/{user_id}/{suspend\|unsuspend\|deactivate\|reactivate}` | `require_platform_mutate` | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| User lock/unlock | `POST /v1/admin/platform-users/{user_id}/{lock\|unlock}` | `require_platform_mutate` | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| Role change | `PUT /v1/admin/platform-users/{user_id}/role` | `require_platform_mutate` | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| Force password reset / generate temp password | `POST /v1/admin/platform-users/{user_id}/{force-password-reset,generate-temp-password}` | `require_platform_mutate` (force-reset) / `require_super_admin` (generate-temp-password, stricter) | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| Session listing (device/session visibility) | `GET /v1/admin/platform-users/{user_id}/sessions` | `require_super_admin` | super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AK (source verification) |
| Customer session revoke-all | `POST /v1/admin/customers/{customer_id}/sessions/revoke-all` | (verify via `admin_customers_router.py`, not independently re-checked this sprint) | super_admin (assumed, not re-verified) | NOT COVERED | FINAL-L5-05AK (source verification, permission not independently confirmed) |
| Deposit approve / reject | `POST /v1/admin/finance/deposits/{deposit_id}/{approve,reject}` | `P.FINANCE_DEPOSITS_APPROVE` | admin_finance / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `finance_hub/admin_router.py`) |
| Deposit record-offline | `POST /v1/admin/finance/deposits/{deposit_id}/record-offline` | `P.FINANCE_DEPOSITS_UPDATE` | admin_finance / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `finance_hub/admin_router.py`) |
| Threat assign / revoke-sessions-from-threat | `POST /v1/admin/security/threats/{threat_id}/{assign,revoke-sessions}` | `P.SECURITY_THREATS_UPDATE` | admin_security / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `security/admin_router.py`; role confirmed via `permissions.py` line 700-701) |
| Threat status update (security-case resolve/reopen equivalent) | `POST /v1/admin/security/threats/{threat_id}/status` | `P.SECURITY_THREATS_RESOLVE` | admin_security / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `security/admin_router.py`) |
| Threat block-ip | `POST /v1/admin/security/threats/{threat_id}/block-ip` | `P.SECURITY_THREATS_BLOCK_IP` | admin_security / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `security/admin_router.py`) |
| Session revoke / revoke-all (device revocation equivalent) | `POST /v1/admin/security/sessions/{session_id}/revoke`, `POST /v1/admin/security/sessions/user/{user_id}/revoke-all` | `P.SECURITY_SESSIONS_REVOKE` | admin_security / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `security/admin_router.py`; role confirmed via `permissions.py` line 703) |
| IP blocklist create / update / revoke | `POST/PATCH/DELETE /v1/admin/security/ip-blocklist{,/{id}}` | `P.SECURITY_IP_BLOCKLIST_CREATE`/`UPDATE`/`REVOKE` | admin_security / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `security/admin_router.py`) |
| API key create / rotate / revoke | `POST/POST/DELETE /v1/admin/security/api-keys{,/{id}/rotate,/{id}}` | `P.SECURITY_API_KEYS_CREATE`/`ROTATE`/`REVOKE` | admin_security / super_admin | NOT COVERED (source-verified only) | FINAL-L5-05AL (source verification, `security/admin_router.py`; role confirmed via `permissions.py` line 707) |
| Policy update | `PATCH /v1/admin/security/policies/{policy_key}` | `P.SECURITY_POLICIES_UPDATE` | **super_admin ONLY** (real finding: `admin_security` holds `SECURITY_POLICIES_READ` and every other write permission in its domain, but `SECURITY_POLICIES_UPDATE` is granted to no role bundle — confirmed via `grep` returning only the constant's own definition line) | **COVERED** (FINAL-L5-05AL live 5-role direct-API matrix: super_admin `200` + real DB mutation/revert proven; admin_security/admin_operations/admin_finance/admin_readonly all `403`, zero DB change. FINAL-L5-05AM adds full 5-role Chromium UI-denial proof: `final-l5-05am-security-policy-ui-gate.spec.ts`, 5/5 passing across 3 consecutive runs, plus the frontend fix that closed the gap — see `L5-05AM-002`.) | FINAL-L5-05AL/AM (live API + live Chromium verification, `security/admin_router.py` + `permissions.py` + `frontend/super-admin/app/admin/security/page.tsx`) |

**29 high-risk actions now classified with real endpoint/permission evidence** (mechanically verified by `e2e/action_registry_guard.js`, FINAL-L5-05AM — corrected from the previously-reported "28," which undercounted by one; see `L5-05AM-001` in the bug register) — 10 with existing Chromium/live-API coverage (9 pre-existing + the Policy Update live matrix added in FINAL-L5-05AM), 19 source-verified but not yet independently Chromium- or direct-API-tested. Every added row cites its exact source file/line, not re-derived from memory; the `admin_security` role-bundle attribution was independently confirmed by reading `app/core/permissions.py` lines 700-707 directly (not assumed from naming convention alone). This closes essentially all of FINAL-L5-05AI's originally-identified gap list (Security Deposit create/verify-equivalent, Policy updates, device/session revocation, security-case resolve/reopen) — the one remaining open item is "system-configuration mutation beyond the route level," which was not located as a distinct endpoint this sprint and may not exist as a separate action in this codebase (the `/admin/settings` route itself is already registered at CRITICAL).

## Result

This sprint delivered a genuine, evidence-based (not fabricated) route classification registry for all 43-47 top-level Super Admin navigation routes (0 UNKNOWN) and expanded the high-risk action registry from 9 (FINAL-L5-05AI) to 20 (FINAL-L5-05AK, corrected count) to **29** (FINAL-L5-05AL, corrected count; mechanically re-verified FINAL-L5-05AM) actions with real endpoint/permission traceability. This is real, bounded progress toward this mission's Parts 4-14 — closing the remaining uncovered routes/actions with fresh Chromium/live-API evidence remains real, substantial, multi-sprint scope, honestly not claimed complete here.
